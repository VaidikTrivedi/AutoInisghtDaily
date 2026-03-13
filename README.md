# AutoInsightDaily

**AutoInsightDaily** is an automated pipeline for generating, summarizing, and posting news updates as visually engaging Instagram carousel posts. It fetches headlines from trusted sources, summarizes them using AI, creates styled images, uploads them to a staging server, and publishes them to Instagram via the Graph API.

## Features

- Fetches news headlines from CNBC, BBC, and TechCrunch.
- Summarizes news using Ollama (local LLM).
- Generates Instagram-ready images with custom themes.
- Uploads images to a staging server for public access.
- Posts carousels to Instagram using the Graph API.
- Cleans up staging server and local files after posting.

## Requirements

- Python 3.8+
- [Ollama](https://ollama.com/) (for local LLM summarization)
- Instagram Business/Creator account linked to a Facebook Page
- Facebook App with Instagram Graph API permissions
- Publicly accessible staging server for image hosting

## Setup

1. **Clone the repo:**
   ```bash
   git clone https://github.com/yourusername/AutoInsightDaily.git
   cd AutoInsightDaily
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure `.env`:**
   Create a `.env` file with the following variables:
   ```
   IG_USERNAME=your_instagram_username
   IG_PASSWORD=your_instagram_password
   ACCESS_TOKEN=your_facebook_graph_api_access_token
   IG_USER_ID=your_instagram_business_account_id
   GRAPH_VERSION=vXX.X
   IMAGE_DIR=insta_news_cards
   OLLAMA_MODEL=llama3
   FONT_REG_PATH=resources/Montserrat-Regular.ttf
   FONT_BOLD_PATH=resources/Montserrat-Bold.ttf
   STAGING_URL=https://your-public-server/ig_staging.php
   ```

4. **Start Ollama (if using AI summarization):**
   ```bash
   ollama serve
   ```

## Usage

Run the main pipeline:

```bash
python main.py
```

This will:
- Generate news images and captions
- Upload images to the staging server
- Post a carousel to Instagram
- Clean up staging and local files

## Project Structure

- `main.py` — Orchestrates the workflow.
- `content.py` — Fetches, summarizes, and generates images.
- `upload.py` — Handles image uploads and server cleanup.
- `post.py` — Posts images to Instagram via Graph API.
- `resources/` — Fonts and other assets.

## Notes

- Make sure your staging server is publicly accessible and supports HTTP range requests.
- Instagram Graph API requires a Business/Creator account and proper permissions.
- Ollama must be running for AI summarization.

**Contributions and issues are welcome!**

---

## Follow @AutoInsightDaily on Instagram for latest AI Summurized news