"""
AutoInsightDaily - FastAPI Backend Server
Provides REST API endpoints for the news automation pipeline.
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from pydantic import BaseModel
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.agent import AIAgent
from backend.content import get_headlines, summarize_news_for_image, get_description, write_post_description, stats
from backend.image_generator import generate_images, generate_background_image_prompt, generate_background_image, print_news_on_image, save_image
from backend.upload import upload_all_images, get_images, cleanup_server, upload_to_stage
from backend.post import post_to_instagram

load_dotenv()

# --- State Persistence ---
STATE_FILE = Path("pipeline_state.json")

def save_state():
    """Save current pipeline state to disk for persistence across restarts."""
    state_data = {
        "pipeline_state": pipeline_state,
        "activity_log": activity_log[-50:],  # Keep last 50 activities
        "news_cache": news_cache,
        "summaries_cache": summaries_cache,
        "saved_at": datetime.now().isoformat()
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Could not save state: {e}")

def load_state():
    """Load pipeline state from disk on startup."""
    global pipeline_state, activity_log, news_cache, summaries_cache
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            
            # Restore state (but reset status to idle on restart)
            pipeline_state.update(state_data.get("pipeline_state", {}))
            pipeline_state["status"] = "idle"  # Always start idle
            pipeline_state["current_step"] = ""
            pipeline_state["progress"] = 0
            
            activity_log.extend(state_data.get("activity_log", []))
            news_cache.extend(state_data.get("news_cache", []))
            summaries_cache.extend(state_data.get("summaries_cache", []))
            
            saved_at = state_data.get("saved_at", "unknown")
            print(f"✅ Restored state from {saved_at}")
            print(f"   - {len(news_cache)} headlines cached")
            print(f"   - {len(summaries_cache)} summaries cached")
            print(f"   - {len(activity_log)} activity entries")
        except Exception as e:
            print(f"Warning: Could not load state: {e}")

# --- App Configuration ---
app = FastAPI(
    title="AutoInsightDaily",
    description="AI-powered Instagram News Automation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# --- Global State ---
pipeline_state = {
    "status": "idle",  # idle, running, completed, error
    "current_step": "",
    "progress": 0,
    "message": "",
    "last_run": None,
    "error": None,
    "images_completed": 0,  # ponytail: track per-image progress
    "images_total": 0
}

# AI Provider Configuration State
# Default to OpenRouter with free models
ai_config = {
    "provider": AIAgent.OPENROUTER,  # Default to OpenRouter
    "models": {
        "summary": "openrouter/free:free",  # OpenRouter free model
        "translation": os.getenv("OLLAMA_TRANSLATION_MODEL", "translategemma"),
        "image": "sourceful/riverflow-v2-fast"  # OpenRouter image model
    }
}

activity_log: List[Dict] = []
news_cache: List[Dict] = []
summaries_cache: List[Dict] = []
connected_websockets: List[WebSocket] = []

# Load saved state on startup
load_state()

# --- Pydantic Models ---
class NewsSource(BaseModel):
    category: str
    url: str
    source_name: str

class HeadlineItem(BaseModel):
    title: str
    source: str
    link: str
    selected: bool = True

class SummarizeRequest(BaseModel):
    headline: str
    description: Optional[str] = None

class GenerateImageRequest(BaseModel):
    index: int
    headline: str
    summary: str
    hashtag: str = ""

class SettingsUpdate(BaseModel):
    run_locally: Optional[bool] = None
    openrouter_api_key: Optional[str] = None
    headline_limit: Optional[int] = None
    auto_cleanup: Optional[bool] = None

class AIProviderUpdate(BaseModel):
    provider: str  # "ollama" or "openrouter"
    models: Optional[Dict[str, str]] = None  # {"summary": "model_name", "image": "model_name"}

# --- Helper Functions ---
def log_activity(action: str, status: str = "success", details: Optional[Dict[str, Any]] = None, step: Optional[str] = None):
    """Add entry to activity log with rich details."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "status": status,
        "step": step,  # Pipeline step: fetch, summarize, generate, upload, post
        "details": details or {}
    }
    activity_log.insert(0, entry)
    if len(activity_log) > 100:
        activity_log.pop()
    
    # Auto-save state after each activity (for persistence)
    if status in ["success", "error"]:
        save_state()

async def broadcast_state():
    """Broadcast pipeline state to all connected WebSocket clients."""
    for ws in connected_websockets:
        try:
            await ws.send_json(pipeline_state)
        except:
            pass

def get_agent():
    """Initialize AI agent based on current configuration."""
    global ai_config
    
    # Provider is already set to OPENROUTER by default
    # Can be overridden by environment variable if needed
    run_locally = os.getenv("RUN_LOCALLY", "False").lower() == "true"
    if run_locally and ai_config["provider"] == AIAgent.OPENROUTER:
        # Switch to Ollama if RUN_LOCALLY is set and we haven't explicitly chosen OpenRouter
        ai_config["provider"] = AIAgent.OLLAMA
        # Update models to Ollama-compatible ones
        if ai_config["models"]["summary"].startswith("meta-llama") or "/" in ai_config["models"]["summary"]:
            ai_config["models"]["summary"] = os.getenv("OLLAMA_SUMMARY_MODEL", "llama3")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    ai_provider = ai_config["provider"]
    return AIAgent(ai_provider=ai_provider, api_key=api_key)

# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render main dashboard."""
    return templates.TemplateResponse(request=request, name="index.html")

# --- API Routes ---

# Pipeline Status
@app.get("/api/status")
async def get_status():
    """Get current pipeline status."""
    return {
        "pipeline": pipeline_state,
        "stats": stats,
        "activity": activity_log[:10]
    }

@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates."""
    await websocket.accept()
    connected_websockets.append(websocket)
    try:
        while True:
            await websocket.send_json(pipeline_state)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)

# News Sources
@app.get("/api/sources")
async def get_sources():
    """Get all configured RSS sources."""
    sources = {
        'Finance/Trade': {'url': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114', 'name': 'CNBC'},
        'Geo-Politics': {'url': 'https://feeds.bbci.co.uk/news/world/rss.xml', 'name': 'BBC'},
        'Tech': {'url': 'https://techcrunch.com/feed/', 'name': 'TechCrunch'},
        'Sports-Cricket': {'url': 'https://crickettimes.com/feed', 'name': 'CricketTimes'},
        'Sports-Football': {'url': 'https://worldsoccer.com/feed', 'name': 'WorldSoccer'},
        'India': {'url': 'https://indianexpress.com/feed', 'name': 'IndianExpress'},
        'Innovation': {'url': 'https://newatlas.com/index.rss', 'name': 'NewAtlas'},
        'Positive-News': {'url': 'https://www.goodnewsnetwork.org/feed', 'name': 'GoodNewsNetwork'}
    }
    return {"sources": sources}

# Headlines
@app.post("/api/headlines/fetch")
async def fetch_headlines(limit: int = 10):
    """Fetch headlines from all sources."""
    global news_cache, pipeline_state
    
    pipeline_state["status"] = "running"
    pipeline_state["current_step"] = "Fetching headlines"
    pipeline_state["progress"] = 10
    await broadcast_state()
    
    log_activity("Starting headline fetch", "running", {"limit": limit}, step="fetch")
    
    try:
        headlines = get_headlines(limit)
        news_cache = [{"title": h["title"], "source": h["source"], "link": h["link"], "selected": True} for h in headlines]
        
        # Group headlines by source
        sources = {}
        for h in headlines:
            src = h["source"]
            sources[src] = sources.get(src, 0) + 1
        
        pipeline_state["status"] = "idle"
        pipeline_state["current_step"] = ""
        pipeline_state["progress"] = 0
        log_activity(
            f"Fetched {len(headlines)} headlines", 
            "success", 
            {
                "count": len(headlines),
                "sources": sources,
                "headlines": [h["title"][:60] + "..." if len(h["title"]) > 60 else h["title"] for h in headlines[:5]]
            },
            step="fetch"
        )
        await broadcast_state()
        
        return {"headlines": news_cache, "count": len(news_cache)}
    except Exception as e:
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        log_activity(f"Failed to fetch headlines: {e}", "error", {"error": str(e)}, step="fetch")
        await broadcast_state()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/headlines")
async def get_cached_headlines():
    """Get cached headlines."""
    return {"headlines": news_cache}

@app.put("/api/headlines/{index}/toggle")
async def toggle_headline(index: int):
    """Toggle headline selection."""
    if 0 <= index < len(news_cache):
        news_cache[index]["selected"] = not news_cache[index]["selected"]
        return {"success": True, "headline": news_cache[index]}
    raise HTTPException(status_code=404, detail="Headline not found")

# Summarization
@app.post("/api/summarize")
async def summarize_single(request: SummarizeRequest):
    """Summarize a single headline."""
    try:
        agent = get_agent()
        description = request.description or request.headline
        # Use the configured model from ai_config
        summary, hashtag = summarize_news_for_image(agent, request.headline, description, model=ai_config["models"]["summary"])
        return {"summary": summary, "hashtag": hashtag}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/summarize/batch")
async def summarize_batch(background_tasks: BackgroundTasks):
    """Summarize all selected headlines."""
    global summaries_cache, pipeline_state
    
    selected = [h for h in news_cache if h.get("selected", True)]
    if not selected:
        raise HTTPException(status_code=400, detail="No headlines selected")
    
    pipeline_state["status"] = "running"
    pipeline_state["current_step"] = "Summarizing headlines"
    pipeline_state["progress"] = 20
    await broadcast_state()
    
    log_activity(f"Starting AI summarization of {len(selected)} headlines", "running", {"count": len(selected)}, step="summarize")
    
    try:
        agent = get_agent()
        summaries_cache = []
        
        for i, news in enumerate(selected):
            pipeline_state["progress"] = 20 + int((i / len(selected)) * 40)
            pipeline_state["message"] = f"Summarizing {i+1}/{len(selected)}"
            await broadcast_state()
            
            description = get_description(news["link"], news["title"])
            # Use the configured model from ai_config
            summary, hashtag = summarize_news_for_image(agent, news["title"], description, model=ai_config["models"]["summary"])
            
            summaries_cache.append({
                "index": i,
                "original_title": news["title"],
                "headline": news["title"],
                "summary": summary,
                "hashtag": hashtag,
                "source": news["link"],
            })
            
            # Log each summary completion
            log_activity(
                f"Summarized: {news['title'][:50]}...", 
                "success", 
                {"index": i+1, "total": len(selected), "hashtag": hashtag},
                step="summarize"
            )
        
        pipeline_state["status"] = "idle"
        pipeline_state["current_step"] = ""
        pipeline_state["progress"] = 0
        pipeline_state["message"] = ""
        log_activity(
            f"Completed summarization of {len(summaries_cache)} headlines", 
            "success", 
            {
                "count": len(summaries_cache),
                "ai_provider": agent.ai_provider,
                "summaries": [{"title": s["headline"][:40], "hashtag": s["hashtag"]} for s in summaries_cache[:3]]
            },
            step="summarize"
        )
        await broadcast_state()
        
        return {"summaries": summaries_cache, "count": len(summaries_cache)}
    except Exception as e:
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        log_activity(f"Summarization failed: {e}", "error", {"error": str(e)}, step="summarize")
        await broadcast_state()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summaries")
async def get_summaries():
    """Get cached summaries."""
    return {"summaries": summaries_cache}

@app.put("/api/summaries/{index}")
async def update_summary(index: int, summary: str, hashtag: str = ""):
    """Update a summary manually."""
    if 0 <= index < len(summaries_cache):
        summaries_cache[index]["summary"] = summary
        if hashtag:
            summaries_cache[index]["hashtag"] = hashtag
        return {"success": True, "summary": summaries_cache[index]}
    raise HTTPException(status_code=404, detail="Summary not found")

# Image Generation
async def _generate_images_background():
    """Background task for image generation."""
    global pipeline_state
    
    try:
        agent = get_agent()
        image_dir = os.getenv("IMAGE_DIR") or "insta_news_cards"
        os.makedirs(image_dir, exist_ok=True)
        generated_images = []
        total = len(summaries_cache)
        
        for i, news in enumerate(summaries_cache):
            pipeline_state["images_completed"] = i
            pipeline_state["images_total"] = total
            pipeline_state["progress"] = 60 + int((i / total) * 30)
            pipeline_state["message"] = f"Generating image {i+1}/{total}"
            await broadcast_state()
            
            # ponytail: retry per-image, not whole batch
            for attempt in range(3):
                try:
                    image_bg_prompt = generate_background_image_prompt(agent, news["headline"])
                    background_image = generate_background_image(agent, image_bg_prompt, model=ai_config["models"]["image"])
                    
                    if background_image:
                        news_post = print_news_on_image(background_image, news["headline"], news["summary"])
                        image_path = f"{image_dir}/post_{news['index']}.png"
                        save_image(news_post, image_path)
                        generated_images.append(image_path)
                        
                        log_activity(
                            f"Generated image {i+1}/{total}", 
                            "success", 
                            {"index": i+1, "attempt": attempt+1, "file": f"post_{news['index']}.png"},
                            step="generate"
                        )
                        break
                except Exception as e:
                    if attempt == 2:
                        log_activity(f"Failed image {i+1} after 3 attempts", "error", {"error": str(e)}, step="generate")
        
        write_post_description(summaries_cache)
        
        pipeline_state["status"] = "idle"
        pipeline_state["current_step"] = ""
        pipeline_state["progress"] = 0
        pipeline_state["message"] = ""
        pipeline_state["images_completed"] = total
        log_activity(
            f"Completed image generation", 
            "success", 
            {"count": len(generated_images), "image_dir": image_dir},
            step="generate"
        )
        await broadcast_state()
        
    except Exception as e:
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        log_activity(f"Image generation failed: {e}", "error", {"error": str(e)}, step="generate")
        await broadcast_state()

@app.post("/api/images/generate")
async def generate_all_images(background_tasks: BackgroundTasks):
    """Start image generation in background."""
    global pipeline_state
    
    if not summaries_cache:
        raise HTTPException(status_code=400, detail="No summaries to generate images for")
    
    pipeline_state["status"] = "running"
    pipeline_state["current_step"] = "Generating images"
    pipeline_state["progress"] = 60
    pipeline_state["images_completed"] = 0
    pipeline_state["images_total"] = len(summaries_cache)
    await broadcast_state()
    
    log_activity(f"Starting image generation for {len(summaries_cache)} summaries", "running", {"count": len(summaries_cache)}, step="generate")
    
    background_tasks.add_task(_generate_images_background)
    
    return {"success": True, "status": "started", "total": len(summaries_cache)}

@app.get("/api/images")
async def list_images():
    """List all generated images."""
    image_dir = os.getenv("IMAGE_DIR") or "insta_news_cards"
    images = []
    
    if os.path.exists(image_dir):
        for f in sorted(os.listdir(image_dir)):
            if f.endswith(('.png', '.jpg', '.jpeg')):
                images.append({
                    "name": f,
                    "path": f"/api/images/file/{f}",
                    "size": os.path.getsize(os.path.join(image_dir, f))
                })
    
    return {"images": images}

@app.get("/api/images/file/{filename}")
async def get_image_file(filename: str):
    """Serve an image file."""
    image_dir = os.getenv("IMAGE_DIR") or "insta_news_cards"
    file_path = os.path.join(image_dir, filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Image not found")

# Staging & Upload
@app.post("/api/staging/upload")
async def upload_to_staging():
    """Upload images to staging server."""
    global pipeline_state
    
    pipeline_state["status"] = "running"
    pipeline_state["current_step"] = "Uploading to staging"
    pipeline_state["progress"] = 90
    await broadcast_state()
    
    log_activity("Starting upload to staging server", "running", step="upload")
    
    try:
        urls = upload_all_images()
        
        pipeline_state["status"] = "idle"
        pipeline_state["current_step"] = ""
        pipeline_state["progress"] = 0
        log_activity(
            f"Uploaded {len(urls)} images to staging", 
            "success", 
            {"count": len(urls), "urls": urls[:3] if len(urls) > 3 else urls},
            step="upload"
        )
        await broadcast_state()
        
        return {"success": True, "urls": urls, "count": len(urls)}
    except Exception as e:
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        log_activity(f"Upload failed: {e}", "error", {"error": str(e)}, step="upload")
        await broadcast_state()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/staging/images")
async def get_staging_images():
    """Get images currently on staging server."""
    try:
        images = get_images()
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/staging/cleanup")
async def cleanup_staging():
    """Clean up staging server."""
    try:
        cleanup_server()
        log_activity("Cleaned up staging server", "success", step="cleanup")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Instagram Publishing
@app.post("/api/instagram/post")
async def publish_to_instagram():
    """Publish carousel to Instagram."""
    global pipeline_state
    
    pipeline_state["status"] = "running"
    pipeline_state["current_step"] = "Publishing to Instagram"
    pipeline_state["progress"] = 95
    await broadcast_state()
    
    log_activity("Starting Instagram publication", "running", step="post")
    
    try:
        success = post_to_instagram()
        
        if success:
            cleanup_server()
            pipeline_state["status"] = "completed"
            pipeline_state["last_run"] = datetime.now().isoformat()
            log_activity(
                "Posted to Instagram successfully", 
                "success", 
                {"platform": "Instagram", "post_type": "carousel", "timestamp": datetime.now().isoformat()},
                step="post"
            )
        else:
            pipeline_state["status"] = "error"
            pipeline_state["error"] = "Post failed"
            log_activity("Instagram post failed", "error", step="post")
        
        pipeline_state["current_step"] = ""
        pipeline_state["progress"] = 0
        await broadcast_state()
        
        return {"success": success}
    except Exception as e:
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        log_activity(f"Instagram post failed: {e}", "error", {"error": str(e)}, step="post")
        await broadcast_state()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/instagram/status")
async def get_instagram_status():
    """Check Instagram connection status."""
    access_token = os.getenv("ACCESS_TOKEN")
    ig_user_id = os.getenv("IG_USER_ID")
    
    return {
        "connected": bool(access_token and ig_user_id),
        "user_id": ig_user_id[:10] + "..." if ig_user_id else None
    }

# Settings
@app.get("/api/settings")
async def get_settings():
    """Get current settings."""
    global ai_config
    
    # Initialize provider if not set
    if ai_config["provider"] is None:
        run_locally = os.getenv("RUN_LOCALLY", "False").lower() == "true"
        ai_config["provider"] = AIAgent.OLLAMA if run_locally else AIAgent.OPENROUTER
    
    return {
        "run_locally": os.getenv("RUN_LOCALLY", "False").lower() == "true",
        "ai_provider": ai_config["provider"],
        "models": ai_config["models"],
        "has_openrouter_key": bool(os.getenv("OPENROUTER_API_KEY")),
        "image_dir": os.getenv("IMAGE_DIR") or "insta_news_cards",
        "staging_url": os.getenv("STAGING_URL") or "",
        "has_instagram": bool(os.getenv("ACCESS_TOKEN") and os.getenv("IG_USER_ID")),
        "summary_model": ai_config["models"]["summary"],
        "translation_model": ai_config["models"]["translation"]
    }

@app.post("/api/ai/provider")
async def set_ai_provider(config: AIProviderUpdate):
    """Update AI provider and models."""
    global ai_config
    
    # Validate provider
    if config.provider not in [AIAgent.OLLAMA, AIAgent.OPENROUTER]:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {config.provider}")
    
    # Check if OpenRouter key exists when selecting openrouter
    if config.provider == AIAgent.OPENROUTER and not os.getenv("OPENROUTER_API_KEY"):
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured")
    
    # Update provider
    old_provider = ai_config["provider"]
    ai_config["provider"] = config.provider
    
    # Update models if provided, otherwise set defaults based on provider
    if config.models:
        ai_config["models"].update(config.models)
    elif old_provider != config.provider:
        # Provider changed, set appropriate default models
        if config.provider == AIAgent.OLLAMA:
            ai_config["models"]["summary"] = os.getenv("OLLAMA_SUMMARY_MODEL", "llama3")
        else:  # OpenRouter
            ai_config["models"]["summary"] = "openrouter/free"
    
    log_activity(
        f"AI provider changed to {config.provider}", 
        "success", 
        {"provider": config.provider, "models": ai_config["models"]}
    )
    
    return {
        "success": True,
        "provider": ai_config["provider"],
        "models": ai_config["models"]
    }

@app.get("/api/ai/status")
async def get_ai_status():
    """Check AI provider status."""
    global ai_config
    
    # Ensure provider is initialized
    get_agent()
    
    current_provider = ai_config["provider"]
    
    if current_provider == AIAgent.OLLAMA:
        # Check Ollama
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            models = response.json().get("models", [])
            return {
                "provider": "ollama",
                "status": "connected",
                "models": [m["name"] for m in models],
                "current_models": ai_config["models"]
            }
        except:
            return {
                "provider": "ollama", 
                "status": "disconnected", 
                "models": [],
                "current_models": ai_config["models"]
            }
    else:
        # Check OpenRouter
        has_key = bool(os.getenv("OPENROUTER_API_KEY"))
        return {
            "provider": "openrouter",
            "status": "connected" if has_key else "no_api_key",
            "models": [
                "openrouter/free",
                "google/gemma-2-9b-it:free",
                "qwen/qwen-2-7b-instruct:free",
                "mistralai/mistral-7b-instruct:free"
            ] if has_key else [],
            "current_models": ai_config["models"]
        }

# Full Pipeline
@app.post("/api/pipeline/run")
async def run_full_pipeline(headline_limit: int = 8):
    """Run the full pipeline: fetch → summarize → generate → upload → post."""
    global pipeline_state
    
    pipeline_state["status"] = "running"
    pipeline_state["current_step"] = "Starting pipeline"
    pipeline_state["progress"] = 0
    await broadcast_state()
    
    start_time = datetime.now()
    log_activity(
        "🚀 Starting full pipeline run", 
        "running", 
        {"headline_limit": headline_limit, "start_time": start_time.isoformat()},
        step="pipeline"
    )
    
    try:
        # Step 1: Fetch headlines
        await fetch_headlines(headline_limit)
        
        # Step 2: Summarize
        await summarize_batch(BackgroundTasks())
        
        # Step 3: Generate images
        await generate_all_images(BackgroundTasks())
        
        # Step 4: Upload to staging
        await upload_to_staging()
        
        # Step 5: Post to Instagram
        result = await publish_to_instagram()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        pipeline_state["status"] = "completed"
        pipeline_state["last_run"] = datetime.now().isoformat()
        log_activity(
            "✅ Full pipeline completed successfully", 
            "success", 
            {
                "duration_seconds": round(duration, 2),
                "headlines_processed": len(news_cache),
                "summaries_generated": len(summaries_cache),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            step="pipeline"
        )
        await broadcast_state()
        
        return {"success": True, "message": "Pipeline completed successfully", "duration": duration}
    except Exception as e:
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        log_activity(f"❌ Pipeline failed: {e}", "error", {"error": str(e)}, step="pipeline")
        await broadcast_state()
        raise HTTPException(status_code=500, detail=str(e))

# Token Stats
@app.get("/api/stats")
async def get_token_stats():
    """Get token usage statistics."""
    return {
        "prompt_tokens": stats["total_prompt_tokens"],
        "completion_tokens": stats["total_completion_tokens"],
        "total_tokens": stats["total_prompt_tokens"] + stats["total_completion_tokens"],
        "duration_seconds": stats["total_duration_ns"] / 1e9
    }

@app.get("/api/activity")
async def get_activity_log():
    """Get recent activity log."""
    return {"activity": activity_log}

# State Management
@app.get("/api/state")
async def get_cached_state():
    """Get current cached state (headlines, summaries, etc.)."""
    return {
        "headlines_count": len(news_cache),
        "summaries_count": len(summaries_cache),
        "headlines": news_cache,
        "summaries": summaries_cache,
        "pipeline_state": pipeline_state,
        "can_resume_from": {
            "fetch": True,
            "summarize": len(news_cache) > 0,
            "generate": len(summaries_cache) > 0,
            "upload": len(summaries_cache) > 0,
            "post": len(summaries_cache) > 0
        }
    }

@app.delete("/api/state/clear")
async def clear_state():
    """Clear all cached state and start fresh."""
    global news_cache, summaries_cache, activity_log, pipeline_state
    
    news_cache = []
    summaries_cache = []
    activity_log = []
    pipeline_state = {
        "status": "idle",
        "current_step": "",
        "progress": 0,
        "message": "",
        "last_run": None,
        "error": None
    }
    
    # Delete state file
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    
    log_activity("🗑️ Cleared all cached state", "success", step="cleanup")
    return {"success": True, "message": "State cleared"}

@app.post("/api/state/save")
async def manual_save_state():
    """Manually save current state to disk."""
    save_state()
    return {"success": True, "message": "State saved"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
