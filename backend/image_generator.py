import os
import json
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import textwrap
from pathlib import Path
from .agent import AIAgent

IMAGE_DIR = os.getenv("IMAGE_DIR") or "insta_news_cards"
FONT_REG_PATH = Path(os.getenv("FONT_REG_PATH") or "backend/resources/Montserrat-Regular.ttf")
FONT_BOLD_PATH = Path(os.getenv("FONT_BOLD_PATH") or "backend/resources/Montserrat-Bold.ttf")
HINDI_FONT_REG_PATH = Path(os.getenv("HINDI_FONT_REG_PATH") or "backend/resources/Hindi-Regular.ttf")
HINDI_FONT_BOLD_PATH = Path(os.getenv("HINDI_FONT_BOLD_PATH") or "backend/resources/Hindi-Bold.ttf")

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
        category = response.strip().lower() # type: ignore
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

def create_image_openrouter(prompt):
    open_router_agent = AIAgent(ai_provider=AIAgent.OPENROUTER, api_key= os.getenv("OPENROUTER_API_KEY"))
    image_url = open_router_agent.getAIImage(prompt=prompt, model="sourceful/riverflow-v2-max-preview")
    return image_url

def generate_background_image_prompt(agent:AIAgent, headline):
    prompt = f"""
    I want to create a dark PNG image background in 1:1 aspect ratio for instagram post based on news headline.
    So write a best prompt to generate background for images, Just background, I will write a news on the images by my self. 
    Explicitly mention to not include any text in the image, only background. The background should be relevant to the news headline.
    Provide just a one best prompt to generate background image, I will pass this prompt to next LLM without any modification.
    Here is a news headline: "{headline}"
    """
    return agent.getAIImage(prompt=prompt, model="gemma4")

def generate_background_image(agent:AIAgent, prompt):
    # Note: Ollama image generation has been unreliable, so we are using OpenRouter for this step. The prompt can still be generated by ollama models locally.
    image_url = create_image_openrouter(prompt)
    if image_url:
        try:
            img = Image.open(BytesIO(base64.b64decode(image_url)))
            return img
        except Exception as e:
            print(f"Error downloading or saving image from OpenRouter: {e}")
    return None
    

def generate_images(agent:AIAgent, news_summaries = None, run_locally=False):
    image_dir = os.getenv("IMAGE_DIR") or "insta_news_cards"
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    if news_summaries is None:
        with open(f"{image_dir}/news_summaries.json", "r", encoding="utf-8") as f:
            news_summaries = json.load(f)
    for news in news_summaries:
        image_bg_prompt = generate_background_image_prompt(agent, news["headline"])
        background_image = generate_background_image(agent, image_bg_prompt)
        news_post = print_news_on_image(background_image, news["headline"], news["summary"])
        save_image(news_post, f"{image_dir}/post_{news['index']}.png")
        # if run_locally:
        #     create_image_ollama(agent, news["index"], news["original_title"], news["summary"], language=news.get("language", "en"))
        # else:
        #     create_image_openrouter(agent, image_dir, news["index"], news["headline"], news["summary"], news["hashtag"])

def print_news_on_image(image, headline, summary):
    """
    Draws headline and summary on an image with automatic text wrapping 
    and sizing to prevent overflow.
    """
    W, H = image.size
    draw = ImageDraw.Draw(image)
    
    # Margins and layout settings
    margin_x = 50
    margin_top = 80
    max_width = W - (margin_x * 2)
    
    # Fit headline in upper portion (max 40% of image height)
    head_font, head_lines, head_h = fit_text_to_box(
        draw, headline.upper(), FONT_BOLD_PATH, 60, max_width, H * 0.35
    )
    
    # Fit summary below headline (max 35% of image height)
    sum_font, sum_lines, sum_h = fit_text_to_box(
        draw, summary, FONT_REG_PATH, 40, max_width, H * 0.35
    )
    
    # Calculate starting Y position to center the text block vertically
    total_text_height = head_h + 40 + sum_h  # 40px gap between headline and summary
    start_y = (H - total_text_height) / 2
    current_y = max(margin_top, start_y)
    
    # Draw headline (centered horizontally)
    for line in head_lines:
        bbox = draw.textbbox((0, 0), line, font=head_font)
        line_width = bbox[2] - bbox[0]
        x = (W - line_width) / 2
        # Add stronger text outline/shadow for better readability on varied backgrounds
        outline_color = (0, 0, 0)  # Black outline
        text_color = (255, 255, 255)  # Bright white
        # Draw outline (multiple offsets for thicker outline)
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2), (-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + ox, current_y + oy), line, font=head_font, fill=outline_color)
        # Draw main text
        draw.text((x, current_y), line, font=head_font, fill=text_color)
        current_y += (bbox[3] - bbox[1]) + 10
    
    # Gap between headline and summary
    current_y += 30
    
    # Draw summary (centered horizontally)
    for line in sum_lines:
        bbox = draw.textbbox((0, 0), line, font=sum_font)
        line_width = bbox[2] - bbox[0]
        x = (W - line_width) / 2
        # Add stronger text outline/shadow for better readability
        outline_color = (0, 0, 0)  # Black outline
        text_color = (255, 255, 255)  # Bright white
        # Draw outline (multiple offsets for thicker outline)
        for ox, oy in [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)]:
            draw.text((x + ox, current_y + oy), line, font=sum_font, fill=outline_color)
        # Draw main text
        draw.text((x, current_y), line, font=sum_font, fill=text_color)
        current_y += (bbox[3] - bbox[1]) + 8
    
    return image

def save_image(image, path):
    try:
        image.save(path)
        print(f"Image saved to {path}")
    except Exception as e:
        print(f"Error saving image: {e}")

if __name__ == "__main__":
    api_key = None
    if os.getenv("RUN_LOCALLY", "False").lower() == "true":
        ai_provider = AIAgent.OLLAMA
    else:
        ai_provider = AIAgent.OPENROUTER
        api_key = os.getenv("OPENROUTER_API_KEY")
    agent = AIAgent(ai_provider=ai_provider, api_key=api_key)
    generate_images(agent, None, False)