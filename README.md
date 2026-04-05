# AutoInsightDaily

**AutoInsightDaily** is an automated pipeline for generating, summarizing, and posting news updates as visually engaging Instagram carousel posts. It fetches headlines from trusted sources, summarizes them using AI (locally via Ollama or via OpenRouter API), creates styled images, uploads them to a staging server, and publishes them to Instagram via the Graph API.

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
- Uploads images to a staging server for public access
- Posts carousels to Instagram using the Graph API
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
├── main.py              # Orchestrates the workflow
├── content.py           # Fetches and summarizes news
├── image_generator.py   # Creates themed images with AI
├── upload.py            # Handles image uploads and server cleanup
├── post.py              # Posts images to Instagram via Graph API
├── agent/               # AI provider abstraction layer
│   ├── __init__.py      # AIAgent class (provider selector)
│   ├── ollama.py        # Local Ollama client
│   └── openrouter.py    # OpenRouter API client
├── resources/           # Fonts and other assets
├── insta_news_cards/    # Generated images output directory
└── requirements.txt     # Python dependencies
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