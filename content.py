import json
import os, requests, feedparser
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from agent import AIAgent
from image_generator import create_image_ollama
import re

# --- CONFIGURATION ---
load_dotenv()
IMAGE_DIR = os.getenv("IMAGE_DIR") or "insta_news_cards"
OLLAMA_SUMMARY_MODEL = os.getenv("OLLAMA_SUMMARY_MODEL") or "llama3"
OLLAMA_TRANSLATION_MODEL = os.getenv("OLLAMA_TRANSLATION_MODEL") or "translategemma"
FONT_REG_PATH = Path(os.getenv("FONT_REG_PATH") or "resources/Montserrat-Regular.ttf")
FONT_BOLD_PATH = Path(os.getenv("FONT_BOLD_PATH") or "resources/Montserrat-Bold.ttf")
HINDI_FONT_REG_PATH = Path(os.getenv("HINDI_FONT_REG_PATH") or "resources/Hindi-Regular.ttf")
HINDI_FONT_BOLD_PATH = Path(os.getenv("HINDI_FONT_BOLD_PATH") or "resources/Hindi-Bold.ttf")

# Token tracking
stats = {
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_duration_ns": 0
}

def log_ollama_usage(response):
    prompt_tokens = getattr(response, 'prompt_eval_count', 0)
    completion_tokens = getattr(response, 'eval_count', 0)
    duration = getattr(response, 'total_duration', 0)
    
    stats["total_prompt_tokens"] += prompt_tokens
    stats["total_completion_tokens"] += completion_tokens
    stats["total_duration_ns"] += duration
    
    print(f"📊 [Ollama Stats] Prompt: {prompt_tokens}, Eval: {completion_tokens}, Total: {prompt_tokens + completion_tokens} tokens")

HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
os.makedirs(IMAGE_DIR, exist_ok=True)

def log_token_usage(model:AIAgent):
    prompt_tokens, completion_tokens, total_tokens, duration = model.getAIUsageStats()
    print(f"Model: {model.ai_provider}, Prompt Tokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, Total Tokens: {total_tokens}, Duration: {duration} ns")
    stats["total_prompt_tokens"] += prompt_tokens
    stats["total_completion_tokens"] += completion_tokens
    stats["total_duration_ns"] += duration


def get_headlines(limit=10):
    """Collects headlines using a browser-like User-Agent to avoid blocks."""
    headlines = []
    
    # Updated, more reliable RSS feeds
    sources = {
        'Finance/Trade': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114',
        'Geo-Politics': 'https://feeds.bbci.co.uk/news/world/rss.xml',
        'Tech': 'https://techcrunch.com/feed/',

        'Sports-Cricket': 'https://crickettimes.com/feed',
        'Sports-Football': 'https://worldsoccer.com/feed',

        'India': 'https://indianexpress.com/feed',

        'AI': 'https://openai.com/blog/rss.xml',

        'Innovation': 'https://newatlas.com/index.rss',

        'Positive-News': 'https://www.goodnewsnetwork.org/feed'
    }

    category_source_mapping = {
        'Finance/Trade': 'CNBC',
        'Geo-Politics': 'BBC',
        'Tech': 'TechCrunch',
        'Sports-Cricket': 'CricketTimes',
        'Sports-Football': 'WorldSoccer',
        'India': 'IndianExpress',
        'Trending': 'TrendHunter',
        'AI': 'OpenAI',
        'Innovation': 'NewAtlas',
        'Positive-News': 'GoodNewsNetwork'
    }

    for category, url in sources.items():
        try:
            print(f"🔍 Fetching {category}, {url}...")
            response = requests.get(url, headers=HEADER, timeout=10)
            
            # Check if the request was successful
            if response.status_code == 200:
                feed = feedparser.parse(response.content) # Parse the content of the response
                
                for entry in feed.entries[:1]: # Grab one from each category
                    headlines.append({
                        "title": entry.title,
                        "source": category_source_mapping[category],
                        "link": entry.link
                    })
            else:
                print(f"⚠️ Failed to fetch {category}: Status Code {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error fetching {category}: {e}")

    return headlines[:limit]

def get_description(url, headline): 
    try:
        response = requests.get(url, headers=HEADER, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            group_elem = soup.find(class_="group")
            if group_elem:
                text = group_elem.get_text(separator='', strip=True)
                return text
            else:
                main = soup.find("main") or soup.find(id="pcl-full-content") or soup.find(class_="td-post-content")
                article = []
                if main:
                    for p in main.find_all("p"):
                        text = p.get_text(" ", strip=True)
                        # Basic noise filter: skip empty, very short, or obvious footer/link blurbs
                        if not text:
                            continue
                        if text.startswith(("RELATED", "MORE FROM THE BBC")):
                            break
                        article.append(text)
                    return "".join(article)
                
                print("Not able to get description; returning headling")
                return headline
        else:
            print(f"⚠️ Failed to fetch {url}: Status Code {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        pass

    return headline

def summarize_news_for_image(agent:AIAgent, headline, news_description):
    """Summarizes headline using local Ollama."""
    prompt = f"""
    Summarize the news headline and description into a one-line, punchy Instagram caption (max 25 words) ending with a single hashtag. 
    Return your answer only inside <description> tags. 
    News Headline: {headline} 
    News Description: {news_description}
    Format: <description>your summary with hashtag here</description>
    """
    
    response = agent.getAIResponse(prompt=prompt, model=OLLAMA_SUMMARY_MODEL)
    log_token_usage(agent)
    summary = response.split('<description>')[1].split('</description>')[0].strip()
    if "one-line punchy" in summary:
        print("Found one-line punchy...")
        summary = summary.replace("Here is one-line punchy sentence for Instagram with one suitable hashtag: ", "").strip()
        summary = summary.replace("Here's a one-line punchy sentence for Instagram:", "").strip()
    hashtag = ""
    match = re.search(r'#[a-zA-Z0-9]+', summary)
    if match:
        hashtag = match.group(0)
        summary = summary.replace(hashtag.strip(), "")
        print(f"Hashtag: {hashtag}")
    if "I need the actual headline" in summary:
        summary = ""
    print(f"News summary for image: {summary}")
    return summary, hashtag.strip()

def write_post_description(news_summaries):
    with open(f"{IMAGE_DIR}/description.txt", "w", encoding="utf-8") as f:
        for summary in news_summaries:
            # f.write(f"{summary['index']+1} - {summary['hashtags']} - source: ${summary['news_source']}\n")
            f.write(f"{summary['hashtag']} ")
        f.write("\n\n Sources are provided below:\n")
        for summary in news_summaries:
            f.write(f"\n{summary['index']+1}. {summary['source']}")
    with open(f"{IMAGE_DIR}/news_summaries.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(news_summaries, ensure_ascii=False, indent=2))

def translate_to_hindi(agent:AIAgent, text):
    prompt = f"""
        You are a professional English (en) to Hindi (hi) translator. Your goal is to accurately convey the meaning and nuances of the original English text while adhering to Hindi grammar, vocabulary, and cultural sensitivities.
        Produce only the Hindi translation, without any additional explanations or commentary. Please translate the following English text into Hindi: {text}
        """
    try:
        response = agent.getAIResponse(prompt=prompt, model=OLLAMA_TRANSLATION_MODEL)
        log_token_usage(agent)
        translation = response.strip()
        return translation
    except Exception as e:
        print(f"Error while translating text to Hindi: {e}")
        return None

def generate_post(agent:AIAgent):
    print("🚀 Collecting news...")
    news_list = get_headlines(10)
    news_summaries = []

    for i, news in enumerate(news_list):
        print(f"📝 Summarizing {i+1}/10: {news['title'][:50]}...")
        try:
            title = news["title"]
            news_description = get_description(news["link"], title)
            news_summary_for_image, hashtag = summarize_news_for_image(agent, title, news_description)
            # title_in_hindi = translate_to_hindi(agent, title)
            # news_summaries_for_image_in_hindi = translate_to_hindi(agent, news_summary_for_image)
            # language = "en"
            # if news_summaries_for_image_in_hindi and title_in_hindi:
            #     language = "hi"
            #     title = title_in_hindi
            #     news_summary_for_image = news_summaries_for_image_in_hindi
            # print(f"🎨 Generating Image {i+1}...")
            # create_pro_image(agent, i+1, title, news_summary_for_image, news["source"], language)
            news_summaries.append({
                "index": i,
                "original_title": news["title"],
                "headline": title,
                "summary": news_summary_for_image,
                "hashtag": hashtag,
                "source": news["link"],
            })
        except Exception as e:
            print(f"Error while summarizing story for headline: ${news} - {e}")

    write_post_description(news_summaries)

    print("\n" + "="*40)
    print("📈 FINAL AI MODEL TOKEN USAGE SUMMARY")
    print(f"Total Prompt Tokens:   {stats['total_prompt_tokens']}")
    print(f"Total Response Tokens: {stats['total_completion_tokens']}")
    print(f"Total Tokens Used:     {stats['total_prompt_tokens'] + stats['total_completion_tokens']}")
    print(f"Total Duration:        {stats['total_duration_ns'] / 1e9:.2f}s")
    print("="*40)

    return news_summaries

    # print(f"✅ Success! images are ready in the '{IMAGE_DIR}' folder.")

if __name__ == "__main__":
    api_key = None
    if os.getenv("RUN_LOCALLY", "False").lower() == "true":
        ai_provider = AIAgent.OLLAMA
    else:
        ai_provider = AIAgent.OPENROUTER
        api_key = os.getenv("OPENROUTER_API_KEY")
    agent = AIAgent(ai_provider=ai_provider, api_key=api_key)
    generate_post(agent)