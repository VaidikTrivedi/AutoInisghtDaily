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
    api_key = os.getenv("OPENROUTER_API_KEY") or None
    run_locally = os.getenv("RUN_LOCALLY", "False").lower() == "true"
    ai_provider = AIAgent.OLLAMA if run_locally else AIAgent.OPENROUTER
    agent = AIAgent(ai_provider=ai_provider, api_key=api_key)
    news_summaries = generate_post(agent)
    generate_images(agent, news_summaries, run_locally=run_locally)
    upload_to_stage()
    success = post_to_instagram()
    if success:
        cleanup_server()
    else: 
        print("Post failed, please mannually check the staging URL and post to Instagram.")