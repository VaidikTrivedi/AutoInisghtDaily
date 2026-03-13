import os, ollama, requests, feedparser, textwrap
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import re

# --- CONFIGURATION ---
load_dotenv()
IMAGE_DIR = os.getenv("IMAGE_DIR") or "insta_news_cards"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") or "llama3"
FONT_REG_PATH = Path(os.getenv("FONT_REG_PATH") or "resources/Montserrat-Regular.ttf")
FONT_BOLD_PATH = Path(os.getenv("FONT_BOLD_PATH") or "resources/Montserrat-Bold.ttf")

HEADER = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
os.makedirs(IMAGE_DIR, exist_ok=True)

# Using soft, muted tones and deep grays for high engagement/readability
THEMES = {
    "finance": {"bg": "#F4F7F6", "text": "#1A2E35", "accent": "#4A7C7A"},  # Clean Slate
    "tech":    {"bg": "#E8EAF6", "text": "#1A237E", "accent": "#3949AB"},  # Soft Cyber
    "politics":{"bg": "#FCF3F2", "text": "#4A1A1A", "accent": "#A52A2A"},  # Muted Rose
    "general": {"bg": "#F9F9F9", "text": "#2D2D2D", "accent": "#888888"}   # Minimalist
}

def get_headlines(limit=10):
    """Collects headlines using a browser-like User-Agent to avoid blocks."""
    headlines = []
    
    # Updated, more reliable RSS feeds
    sources = {
        'Finance/Trade': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114',
        'Geo-Politics': 'https://feeds.bbci.co.uk/news/world/rss.xml',
        'Tech': 'https://techcrunch.com/feed/'
    }

    category_source_mapping = {
        'Finance/Trade': 'CNBC',
        'Geo-Politics': 'BBC',
        'Tech': 'TechCrunch'
    }

    for category, url in sources.items():
        try:
            print(f"🔍 Fetching {category}...")
            response = requests.get(url, headers=HEADER, timeout=10)
            
            # Check if the request was successful
            if response.status_code == 200:
                feed = feedparser.parse(response.content) # Parse the content of the response
                
                for entry in feed.entries[:4]: # Grab a few from each category
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
                main = soup.find("main")
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

def summarize_news_for_image(headline, news_description):
    """Summarizes headline using local Ollama."""
    prompt = f"Summarize this news headline and description into a one-line punchy sentence for Instagram with one most suitable hashtag at the end (max 25 words). News Headline: {headline}; News Description: {news_description}"
    response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
    summary = response['response'].strip().replace('"', '')
    if "one-line punchy" in summary:
        print("Found one-line punchy...")
        summary = summary.replace("Here is one-line puncy sentence for Instagram with one suitable hashtag: ", "").stip()
        summary = summary.replace("Here's a one-line punchy sentence for Instagram:", "").stip()
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

def get_hashtags(headline, news_description):
    """Summarizes headline using local Ollama."""
    prompt = f"Provide a most suitable and catchy hashtag accoding to the news (Just provide hashtags, no text at all). News Headline: {headline}; News Description: {news_description}"
    response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
    summary = response['response'].strip().replace('"', '')
    if "I need the actual headline" in summary:
        summary = ""
    print(f"News summary for description: {summary}")
    return summary

def get_safe_style(headline):
    """Asks Ollama to pick a theme name, not a hex code."""
    prompt = f"Categorize this news: '{headline}'. Pick exactly one: finance, tech, politics, or general. Return ONLY the word."
    try:
        response = ollama.generate(model='llama3', prompt=prompt)
        category = response['response'].strip().lower()
        # Fallback if category is weird
        return THEMES.get(category, THEMES["general"])
    except:
        return THEMES["general"]

def fit_text_to_box(draw, text, font_path, start_size, max_w, max_h):
    """Shrinks font size until the entire block fits the max width/height."""
    current_size = start_size
    while current_size > 20:
        font = ImageFont.truetype(font_path, current_size)
        # Wrap text based on character width approx for the font size
        lines = textwrap.wrap(text, width=int(max_w / (current_size * 0.5))) 
        
        # Calculate total height of the wrapped block
        total_h = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            total_h += (bbox[3] - bbox[1]) + 15 # Line height + spacing
        
        if total_h <= max_h:
            return font, lines, total_h
        current_size -= 4
    return ImageFont.load_default(), [text], 50

def create_pro_image(index, headline, summary, source):
    W, H = 1080, 1080
    theme = get_safe_style(headline)
    img = Image.new('RGB', (W, H), color=theme["bg"])
    draw = ImageDraw.Draw(img)

    # 1. Fit Headline (Upper 50% of image)
    head_font, head_lines, head_h = fit_text_to_box(
        draw, headline.upper(), FONT_BOLD_PATH, 85, W*0.85, 450
    )

    # 2. Fit Summary (Below Headline)
    # Give summary the remaining space minus some margins
    sum_font, sum_lines, sum_h = fit_text_to_box(
        draw, summary, FONT_REG_PATH, 45, W*0.8, 300
    )

    # 3. Drawing - Centered Vertical Layout
    current_y = (H - (head_h + sum_h + 100)) / 2 # Total block centering

    # Draw Headline
    for line in head_lines:
        bbox = draw.textbbox((0, 0), line, font=head_font)
        draw.text(((W-(bbox[2]-bbox[0]))/2, current_y), line, font=head_font, fill=theme["text"])
        current_y += (bbox[3]-bbox[1]) + 15

    # Separator
    current_y += 40
    draw.line([(W*0.4, current_y), (W*0.6, current_y)], fill=theme["accent"], width=3)
    current_y += 60

    # Draw Summary
    for line in sum_lines:
        bbox = draw.textbbox((0, 0), line, font=sum_font)
        draw.text(((W-(bbox[2]-bbox[0]))/2, current_y), line, font=sum_font, fill=theme["text"])
        current_y += (bbox[3]-bbox[1]) + 10

    # Footer
    # footer_font = ImageFont.truetype(FONT_REG_PATH, 28)
    # draw.text((W//2-80, H-80), f"SOURCE: {source.upper()}", font=footer_font, fill=theme["accent"])

    img.save(f"{IMAGE_DIR}/post_{index}.png", quality=95)

def write_description(news_summaries):
    with open(f"{IMAGE_DIR}/description.txt", "w", encoding="utf-8") as f:
        for summary in news_summaries:
            # f.write(f"{summary['index']+1} - {summary['hashtags']} - source: ${summary['news_source']}\n")
            f.write(f"{summary['hashtag']} ")

def generate_post():
    print("🚀 Collecting news...")
    news_list = get_headlines(10)
    news_summaries = []

    for i, news in enumerate(news_list):
        print(f"📝 Summarizing {i+1}/10: {news['title'][:50]}...")
        try:
            news_description = get_description(news["link"], news["title"])
            news_summary_for_image, hashtag = summarize_news_for_image(news["title"], news_description)
            print(f"🎨 Generating Image {i+1}...")
            create_pro_image(i+1, news["title"], news_summary_for_image, news["source"])
            news_summaries.append({
                "index": i,
                "news_source": news["link"],
                "hashtag": hashtag
            })
        except Exception as e:
            print(f"Error while summarizing story for headline: ${news} - {e}")

    write_description(news_summaries)

    print(f"✅ Success! 10 images are ready in the '{IMAGE_DIR}' folder.")

if __name__ == "__main__":
    generate_post()