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
    "error": None
}

activity_log = []
news_cache = []
summaries_cache = []
connected_websockets: List[WebSocket] = []

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

async def broadcast_state():
    """Broadcast pipeline state to all connected WebSocket clients."""
    for ws in connected_websockets:
        try:
            await ws.send_json(pipeline_state)
        except:
            pass

def get_agent():
    """Initialize AI agent based on settings."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    run_locally = os.getenv("RUN_LOCALLY", "False").lower() == "true"
    ai_provider = AIAgent.OLLAMA if run_locally else AIAgent.OPENROUTER
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
        summary, hashtag = summarize_news_for_image(agent, request.headline, description)
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
            summary, hashtag = summarize_news_for_image(agent, news["title"], description)
            
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
@app.post("/api/images/generate")
async def generate_all_images():
    """Generate images for all summaries."""
    global pipeline_state
    
    if not summaries_cache:
        raise HTTPException(status_code=400, detail="No summaries to generate images for")
    
    pipeline_state["status"] = "running"
    pipeline_state["current_step"] = "Generating images"
    pipeline_state["progress"] = 60
    await broadcast_state()
    
    log_activity(f"Starting image generation for {len(summaries_cache)} summaries", "running", {"count": len(summaries_cache)}, step="generate")
    
    try:
        agent = get_agent()
        image_dir = os.getenv("IMAGE_DIR") or "insta_news_cards"
        os.makedirs(image_dir, exist_ok=True)
        generated_images = []
        
        for i, news in enumerate(summaries_cache):
            pipeline_state["progress"] = 60 + int((i / len(summaries_cache)) * 30)
            pipeline_state["message"] = f"Generating image {i+1}/{len(summaries_cache)}"
            await broadcast_state()
            
            # Generate background prompt and image
            image_bg_prompt = generate_background_image_prompt(agent, news["headline"])
            background_image = generate_background_image(agent, image_bg_prompt)
            
            if background_image:
                news_post = print_news_on_image(background_image, news["headline"], news["summary"])
                image_path = f"{image_dir}/post_{news['index']}.png"
                save_image(news_post, image_path)
                generated_images.append(image_path)
                
                log_activity(
                    f"Generated image {i+1}/{len(summaries_cache)}", 
                    "success", 
                    {"index": i+1, "prompt_preview": (image_bg_prompt[:80] + "...") if image_bg_prompt else "N/A", "file": f"post_{news['index']}.png"},
                    step="generate"
                )
        
        # Write description file
        write_post_description(summaries_cache)
        
        pipeline_state["status"] = "idle"
        pipeline_state["current_step"] = ""
        pipeline_state["progress"] = 0
        pipeline_state["message"] = ""
        log_activity(
            f"Completed image generation", 
            "success", 
            {
                "count": len(generated_images),
                "image_dir": image_dir,
                "files": [f"post_{s['index']}.png" for s in summaries_cache]
            },
            step="generate"
        )
        await broadcast_state()
        
        return {"success": True, "count": len(summaries_cache)}
    except Exception as e:
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        log_activity(f"Image generation failed: {e}", "error", {"error": str(e)}, step="generate")
        await broadcast_state()
        raise HTTPException(status_code=500, detail=str(e))

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
    return {
        "run_locally": os.getenv("RUN_LOCALLY", "False").lower() == "true",
        "has_openrouter_key": bool(os.getenv("OPENROUTER_API_KEY")),
        "image_dir": os.getenv("IMAGE_DIR") or "insta_news_cards",
        "staging_url": os.getenv("STAGING_URL") or "",
        "has_instagram": bool(os.getenv("ACCESS_TOKEN") and os.getenv("IG_USER_ID")),
        "summary_model": os.getenv("OLLAMA_SUMMARY_MODEL") or "llama3",
        "translation_model": os.getenv("OLLAMA_TRANSLATION_MODEL") or "translategemma"
    }

@app.get("/api/ai/status")
async def get_ai_status():
    """Check AI provider status."""
    run_locally = os.getenv("RUN_LOCALLY", "False").lower() == "true"
    
    if run_locally:
        # Check Ollama
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            models = response.json().get("models", [])
            return {
                "provider": "ollama",
                "status": "connected",
                "models": [m["name"] for m in models]
            }
        except:
            return {"provider": "ollama", "status": "disconnected", "models": []}
    else:
        # Check OpenRouter
        has_key = bool(os.getenv("OPENROUTER_API_KEY"))
        return {
            "provider": "openrouter",
            "status": "connected" if has_key else "no_api_key",
            "models": ["gemma4", "llama3", "qwen3.5"] if has_key else []
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
        await generate_all_images()
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
