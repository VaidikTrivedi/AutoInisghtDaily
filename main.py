import os
from dotenv import load_dotenv
from agent import AIAgent
from content import generate_post
from image_generator import generate_images
from post import post_to_instagram
from upload import cleanup_server, upload_to_stage

load_dotenv()

if __name__ == "__main__":
    api_key = os.getenv("OPENROUTER_API_KEY") or None
    run_locally = os.getenv("RUN_LOCALLY", "False").lower() == "true"
    ai_provider = AIAgent.OLLAMA if run_locally else AIAgent.OPENROUTER
    agent = AIAgent(ai_provider=ai_provider, api_key=api_key)
    news_summaries = generate_post(agent)
    generate_images(agent, news_summaries, run_locally=run_locally)
    upload_to_stage()
    post_to_instagram()
    cleanup_server()