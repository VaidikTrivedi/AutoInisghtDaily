# AutoInsightDaily

**AutoInsightDaily** is an automated pipeline for generating, summarizing, and posting news updates as Instagram content. It supports both image carousels and short news videos, with a FastAPI backend + web dashboard for end-to-end control.

## Features

- Fetches news headlines from multiple trusted sources:
  - **Finance/Trade** — CNBC
  - **Geo-Politics** — BBC
  - **Tech** — TechCrunch
  - **Sports** — CricketTimes, WorldSoccer
  - **India** — Indian Express
  - **AI** — OpenAI Blog
  - **Innovation** — NewAtlas
  - **Positive News** — Good News Network
- Summarizes news using AI (supports both local Ollama and cloud-based OpenRouter)
- AI-powered image generation with themed styling (finance, tech, politics, general)
- Generates Instagram-ready images with custom fonts and themes
- Generates short news videos from summaries using the embedded `news_video_engine`
- Voice selection dropdown in UI (default + provider voices)
- Built-in video task polling, video preview, and Reels publishing from the dashboard
- Uploads images to a staging server for public access
- Posts carousels to Instagram using the Graph API
- Posts generated videos to Instagram Reels via Graph API
- Validates and filters bad summaries before image/video generation
- Cleans up staging server and local files after posting

## Requirements

- Python 3.8+
- [Ollama](https://ollama.com/) (optional, for local LLM summarization)
- [OpenRouter API Key](https://openrouter.ai/) (optional, for cloud-based AI)
- Instagram Business/Creator account linked to a Facebook Page
- Facebook App with Instagram Graph API permissions
- Publicly accessible staging server for image hosting

## Setup

1. **Clone the repo:**
   ```bash
   git clone https://github.com/yourusername/AutoInsightDaily.git
   cd AutoInsightDaily
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure `.env`:**
   Create a `.env` file with the following variables:
   ```env
   # Instagram Configuration
   IG_USERNAME=your_instagram_username
   IG_PASSWORD=your_instagram_password
   ACCESS_TOKEN=your_facebook_graph_api_access_token
   IG_USER_ID=your_instagram_business_account_id
   GRAPH_VERSION=vXX.X

   # AI Provider Configuration
   RUN_LOCALLY=true                    # Set to 'true' for Ollama, 'false' for OpenRouter
   OPENROUTER_API_KEY=your_openrouter_api_key  # Required if RUN_LOCALLY=false
   MPT_OPENROUTER_MODEL=openrouter/free
   MPT_PEXELS_API_KEYS=key1,key2
   MPT_TWELVELABS_API_KEYS=key1,key2
   OLLAMA_SUMMARY_MODEL=llama3
   OLLAMA_TRANSLATION_MODEL=translategemma

   # Paths
   IMAGE_DIR=insta_news_cards
   FONT_REG_PATH=resources/Montserrat-Regular.ttf
   FONT_BOLD_PATH=resources/Montserrat-Bold.ttf
   HINDI_FONT_REG_PATH=resources/Hindi-Regular.ttf
   HINDI_FONT_BOLD_PATH=resources/Hindi-Bold.ttf

   # Staging Server
   STAGING_URL=https://your-public-server/ig_staging.php
   ```

5. **Start Ollama (if running locally):**
   ```bash
   ollama serve
   ```

## Usage

### Web dashboard (recommended)

Run API + UI:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Then open `http://localhost:8000` and run:
1. Fetch headlines
2. Summarize selected headlines
3. Generate images **or** generate video
4. Preview output
5. Publish to Instagram (carousel or Reels)

### CLI pipeline

Run the main pipeline:

```bash
python main.py
```

This will:
1. Fetch news headlines from multiple RSS sources
2. Summarize each headline using AI
3. Generate themed images for each news item
4. Upload images to the staging server
5. Post a carousel to Instagram
6. Clean up staging and local files

## Project Structure

```
AutoInsightDaily/
├── server.py                    # FastAPI app + dashboard endpoints
├── main.py                      # CLI pipeline runner
├── backend/                     # News/image/upload/post logic
├── frontend/                    # Dashboard UI (templates + static JS/CSS)
├── news_video_engine/           # Embedded video generation engine
├── insta_news_cards/            # Generated image/summaries artifacts
└── requirements.txt             # Python dependencies
```

## AI Providers

The project supports two AI providers via the `AIAgent` abstraction:

| Provider | Use Case | Configuration |
|----------|----------|---------------|
| **Ollama** | Local/offline usage, no API costs | Set `RUN_LOCALLY=true` |
| **OpenRouter** | Cloud-based, access to multiple models | Set `RUN_LOCALLY=false` and provide `OPENROUTER_API_KEY` |

## Notes

- Make sure your staging server is publicly accessible and supports HTTP range requests.
- Instagram Graph API requires a Business/Creator account and proper permissions.
- When using Ollama, ensure the service is running before executing the script.
- OpenRouter provides access to various models including GPT, Claude, and open-source alternatives.

**Contributions and issues are welcome!**

---

## Follow @AutoInsightDaily on Instagram for the latest AI-summarized news