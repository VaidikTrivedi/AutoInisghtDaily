import os
import json
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import textwrap
from pathlib import Path
from agent import AIAgent

IMAGE_DIR = os.getenv("IMAGE_DIR") or "insta_news_cards"
FONT_REG_PATH = Path(os.getenv("FONT_REG_PATH") or "resources/Montserrat-Regular.ttf")
FONT_BOLD_PATH = Path(os.getenv("FONT_BOLD_PATH") or "resources/Montserrat-Bold.ttf")
HINDI_FONT_REG_PATH = Path(os.getenv("HINDI_FONT_REG_PATH") or "resources/Hindi-Regular.ttf")
HINDI_FONT_BOLD_PATH = Path(os.getenv("HINDI_FONT_BOLD_PATH") or "resources/Hindi-Bold.ttf")

THEMES = {
    "finance": {"bg": "#F4F7F6", "text": "#1A2E35", "accent": "#4A7C7A"},  # Clean Slate
    "tech":    {"bg": "#E8EAF6", "text": "#1A237E", "accent": "#3949AB"},  # Soft Cyber
    "politics":{"bg": "#FCF3F2", "text": "#4A1A1A", "accent": "#A52A2A"},  # Muted Rose
    "general": {"bg": "#F9F9F9", "text": "#2D2D2D", "accent": "#888888"}   # Minimalist
}

def get_safe_style(agent:AIAgent, headline):
    """Asks Ollama to pick a theme name, not a hex code."""
    prompt = f"Categorize this news: '{headline}'. Pick exactly one: finance, tech, politics, or general. Return ONLY the word."
    try:
        response = agent.getAIResponse(prompt=prompt, model='llama3')
        # log_token_usage(agent)
        category = response.strip().lower()
        theme = category if category in THEMES else "general"
        return THEMES[theme]
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

def create_image_ollama(agent:AIAgent, index, headline, summary, language="en"):
    W, H = 1080, 1080
    theme = get_safe_style(agent, headline)
    img = Image.new('RGB', (W, H), color=theme["bg"])
    draw = ImageDraw.Draw(img)

    bold_font_language = HINDI_FONT_BOLD_PATH if language == "hi" else FONT_BOLD_PATH
    regular_font_language = HINDI_FONT_REG_PATH if language == "hi" else FONT_REG_PATH

    # 1. Fit Headline (Upper 50% of image)
    head_font, head_lines, head_h = fit_text_to_box(
        draw, headline.upper(), bold_font_language, 85, W*0.85, 450
    )

    # 2. Fit Summary (Below Headline)
    # Give summary the remaining space minus some margins
    sum_font, sum_lines, sum_h = fit_text_to_box(
        draw, summary, regular_font_language, 45, W*0.8, 300
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

def create_image_openrouter(agent:AIAgent, image_dir, index, headline, summary, hashtag):
    prompt = f"""Act as an editorial designer. Create a professional, high-impact Instagram news graphic.
            1. Visual Intelligence: Analyze the Headline: '{headline}' and the Summary: '{summary}'. Generate a cinematic, high-resolution background image that visually represents the core subject of this news (e.g., if the news is about oil, show a refinery; if about technology, show futuristic circuits; if about nature, show a landscape).
            2. Image Styling: The background must be high-contrast with a professional editorial color grade. Apply a slight radial blur or a dark vignette to ensure the center and edges are optimized for text legibility.
            3. Typography & Layout: > * Headline: Place the text '{headline}' in the upper third. Use a massive, ultra-bold, clean Devanagari/Sans-serif font in bright white with a subtle drop shadow.
                Summary: Centered below the headline, place '{summary}' inside a sleek, semi-transparent frosted-glass overlay box. Use a medium-weight, highly legible white font.
                Tagging: In the bottom-right corner, place the hashtag '{hashtag}' in a bold, vibrant color.
            4. Quality: 8k resolution, photorealistic, sharp focus on text, news-broadcast aesthetic, 1:1 aspect ratio optimized for mobile viewing."""
    
    image_url = agent.getAIImage(prompt=prompt, model="sourceful/riverflow-v2-max-preview")
    if image_url:
        try:
            img = Image.open(BytesIO(base64.b64decode(image_url)))
            img.save(f"{image_dir}/post_{index}.png", "PNG")
        except Exception as e:
            print(f"Error downloading or saving image from OpenRouter: {e}")
    

def generate_images(agent:AIAgent, news_summaries = None, run_locally=False):
    image_dir = os.getenv("IMAGE_DIR") or "insta_news_cards"
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    if news_summaries is None:
        with open(f"{image_dir}/news_summaries.json", "r", encoding="utf-8") as f:
            news_summaries = json.load(f)
    for news in news_summaries:
        if run_locally:
            create_image_ollama(agent, news["index"], news["original_title"], news["summary"], language=news.get("language", "en"))
        else:
            create_image_openrouter(agent, image_dir, news["index"], news["headline"], news["summary"], news["hashtag"])


if __name__ == "__main__":
    api_key = None
    if os.getenv("RUN_LOCALLY", "False").lower() == "true":
        ai_provider = AIAgent.OLLAMA
    else:
        ai_provider = AIAgent.OPENROUTER
        api_key = os.getenv("OPENROUTER_API_KEY")
    agent = AIAgent(ai_provider=ai_provider, api_key=api_key)
    generate_images(agent, None, False)