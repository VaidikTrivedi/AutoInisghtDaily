import os
import json
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import textwrap
from pathlib import Path
from .agent import AIAgent

# Get absolute path to the backend/resources directory
# Use the actual file path and resolve it immediately at module load time
_THIS_FILE = Path(__file__).resolve()
_RESOURCES_DIR = _THIS_FILE.parent / "resources"
_ABSOLUTE_PATH = os.getenv("ABSOLUTE_PATH") or str(_RESOURCES_DIR)

# Verify fonts exist at startup
def _get_font_path(env_var, default_filename):
    """Get font path from env or default, always returns absolute string path."""
    env_path = os.getenv(env_var)
    if env_path:
        p = Path(env_path).resolve()
        if p.exists():
            return str(p)
    
    # Use the resources directory relative to this file
    font_path = _RESOURCES_DIR / default_filename
    if not font_path.exists():
        # Fallback: try from current working directory
        alt_path = Path.cwd() / "backend" / "resources" / default_filename
        if alt_path.exists():
            return str(alt_path)
        # Another fallback: absolute hardcoded path
        hardcoded = Path(_ABSOLUTE_PATH) / default_filename
        if hardcoded.exists():
            return str(hardcoded)
    return str(font_path)

IMAGE_DIR = os.getenv("IMAGE_DIR") or "insta_news_cards"
FONT_REG_PATH = _get_font_path("FONT_REG_PATH", "Montserrat-Regular.ttf")
FONT_BOLD_PATH = _get_font_path("FONT_BOLD_PATH", "Montserrat-Bold.ttf")
FONT_ITALIC_PATH = _get_font_path("FONT_ITALIC_PATH", "Roboto-Italic.ttf")
HINDI_FONT_REG_PATH = _get_font_path("HINDI_FONT_REG_PATH", "Hindi-Regular.ttf")
HINDI_FONT_BOLD_PATH = _get_font_path("HINDI_FONT_BOLD_PATH", "Hindi-Bold.ttf")

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
    font_path_str = str(font_path)
    while current_size > 20:
        font = ImageFont.truetype(font_path_str, current_size)
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

def create_image_openrouter(prompt, model):
    open_router_agent = AIAgent(ai_provider=AIAgent.OPENROUTER, api_key= os.getenv("OPENROUTER_API_KEY"))
    image_url = open_router_agent.getAIImage(prompt=prompt, model=model)
    return image_url

def generate_background_image_prompt(agent:AIAgent, headline):
    prompt = f"""
    I want to create a dark PNG image background in 1:1 aspect ratio for instagram post based on news headline.
    So write a best prompt to generate background for images, Just background, I will write a news on the images by my self. 
    Explicitly mention to not include any text in the image, only background. The background should be relevant to the news headline.
    Provide just a one best prompt to generate background image, I will pass this prompt to next LLM without any modification.
    Here is a news headline: "{headline}"
    """
    return agent.getAIImage(prompt=prompt, model="sourceful/riverflow-v2-fast")

def generate_background_image(agent:AIAgent, prompt, model):
    # Note: Ollama image generation has been unreliable, so we are using OpenRouter for this step. The prompt can still be generated by ollama models locally.
    image_url = create_image_openrouter(prompt, model)
    if image_url:
        try:
            img = Image.open(BytesIO(base64.b64decode(image_url)))
            return img
        except Exception as e:
            print(f"Error downloading or saving image from OpenRouter: {e}")
    return None
    

def generate_images(agent:AIAgent, news_summaries = None, run_locally=False, image_model=None):
    """
    Generate images for news summaries.
    
    Args:
        agent: AIAgent instance for image generation
        news_summaries: List of news summary dictionaries (loaded from JSON if None)
        run_locally: Whether running locally (deprecated, kept for compatibility)
        image_model: Model to use for image generation (e.g., 'sourceful/riverflow-v2-fast')
    """
    image_dir = os.getenv("IMAGE_DIR") or "insta_news_cards"
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    if news_summaries is None:
        with open(f"{image_dir}/news_summaries.json", "r", encoding="utf-8") as f:
            news_summaries = json.load(f)
    
    # Use provided model or default to sourceful/riverflow-v2-fast
    if image_model is None:
        image_model = "sourceful/riverflow-v2-fast"
    
    for news in news_summaries:
        image_bg_prompt = generate_background_image_prompt(agent, news["headline"])
        background_image = generate_background_image(agent, image_bg_prompt, model=image_model)
        news_post = print_news_on_image(background_image, news["headline"], news["summary"])
        save_image(news_post, f"{image_dir}/post_{news['index']}.png")

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
        draw, summary, FONT_ITALIC_PATH, 40, max_width, H * 0.35
    )
    
    # Calculate starting Y position to center the text block vertically
    total_text_height = head_h + 40 + sum_h  # 40px gap between headline and summary
    start_y = (H - total_text_height) / 2
    current_y = max(margin_top, start_y)
    
    # Draw headline with strong outline for visibility on any background
    for line in head_lines:
        bbox = draw.textbbox((0, 0), line, font=head_font)
        line_width = bbox[2] - bbox[0]
        x = (W - line_width) / 2
        # Draw black outline (stroke effect) for maximum contrast
        for dx in [-3, -2, -1, 0, 1, 2, 3]:
            for dy in [-3, -2, -1, 0, 1, 2, 3]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, current_y + dy), line, font=head_font, fill="black")
        # Draw bright white text on top
        draw.text((x, current_y), line, font=head_font, fill="#FFFFFF")
        current_y += (bbox[3] - bbox[1]) + 10
    
    # Gap between headline and summary
    current_y += 30
    
    # Draw summary with strong outline for visibility
    for line in sum_lines:
        bbox = draw.textbbox((0, 0), line, font=sum_font)
        line_width = bbox[2] - bbox[0]
        x = (W - line_width) / 2
        # Draw black outline (stroke effect) for maximum contrast
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, current_y + dy), line, font=sum_font, fill="black")
        # Draw bright white text on top
        draw.text((x, current_y), line, font=sum_font, fill="#FFFFFF")
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
    run_locally = os.getenv("RUN_LOCALLY", "False").lower() == "true"
    
    if run_locally:
        ai_provider = AIAgent.OLLAMA
    else:
        ai_provider = AIAgent.OPENROUTER
        api_key = os.getenv("OPENROUTER_API_KEY")
    
    agent = AIAgent(ai_provider=ai_provider, api_key=api_key)
    generate_images(agent, None, run_locally, image_model="sourceful/riverflow-v2-fast")