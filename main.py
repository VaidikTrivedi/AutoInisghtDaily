import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
from backend.agent import AIAgent
from backend.content import generate_post
from backend.image_generator import generate_images
from backend.post import post_to_instagram
from backend.upload import cleanup_server, upload_to_stage

load_dotenv()

if __name__ == "__main__":
    models = {
        "summary_model": "openrouter/free:free",
        "image_model": "sourceful/riverflow-v2-fast",
    }
    api_key = os.getenv("OPENROUTER_API_KEY") or None
    run_locally = os.getenv("RUN_LOCALLY", "False").lower() == "true"
    
    # Set provider based on RUN_LOCALLY
    if run_locally:
        ai_provider = AIAgent.OLLAMA
        models["summary_model"] = "llama3"
    else:
        ai_provider = AIAgent.OPENROUTER
    
    agent = AIAgent(ai_provider=ai_provider, api_key=api_key)
    news_summaries = generate_post(agent, models["summary_model"])
    generate_images(agent, news_summaries, run_locally=run_locally, image_model=models["image_model"])
    upload_to_stage()
    success = post_to_instagram()
    if success:
        cleanup_server()
    else: 
        print("Post failed, please mannually check the staging URL and post to Instagram.")