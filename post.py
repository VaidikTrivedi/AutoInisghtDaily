from dotenv import load_dotenv
import requests
import time
import os
from upload import get_images

load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
GRAPH_VERSION = os.getenv("GRAPH_VERSION")
BASE_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"
IMAGE_DIR = os.getenv("IMAGE_DIR") or "insta_news_cards"

def poll_status(container_id, max_wait=300):
    """Poll /<container_id>?fields=status_code until FINISHED."""
    start = time.time()
    while time.time() - start < max_wait:
        url = f"{BASE_URL}/{container_id}?fields=status_code&access_token={ACCESS_TOKEN}"
        resp = requests.get(url=url).json()
        status = resp.get("status_code")
        if status == "FINISHED":
            return True
        elif status in ["ERROR", "EXPIRED"]:
            raise ValueError(f"Container {container_id} failed: {status}")
        time.sleep(5)
    raise TimeoutError("Polling timeout")

def create_image_container(image_filename):
    """Create container for one image."""
    # image_url = f"http://{YOUR_IP}:{SERVER_PORT}/{image_filename}"
    image_url = image_filename
    url = f"{BASE_URL}/{IG_USER_ID}/media"
    payload = {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": ACCESS_TOKEN
    }
    resp = requests.post(url, data=payload).json()
    if "id" not in resp:
        raise ValueError(f"Failed to create container for {image_filename}: {resp}")
    container_id = resp["id"]
    poll_status(container_id)
    print(f"Child borned: {container_id}")
    return container_id

def create_carousel(children_ids, caption):
    """Create carousel container."""
    url = f"{BASE_URL}/{IG_USER_ID}/media"
    payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(children_ids),
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    resp = requests.post(url, data=payload).json()
    if "id" not in resp:
        raise ValueError(f"Failed carousel: {resp}")
    carousel_id = resp["id"]
    poll_status(carousel_id)
    return carousel_id

def publish(carousel_id):
    """Publish carousel."""
    url = f"{BASE_URL}/{IG_USER_ID}/media_publish"
    payload = {"creation_id": carousel_id, "access_token": ACCESS_TOKEN}
    resp = requests.post(url, data=payload).json()
    if "id" not in resp:
        raise ValueError(f"Publish failed: {resp}")
    print(f"Published! IG Media ID: {resp['id']}")
    return resp["id"]

def read_caption():
    with open(f"{IMAGE_DIR}/description.txt", "r", encoding="utf-8") as f:
        return f.read()
    
def post_to_instagram():
    if ACCESS_TOKEN is None or IG_USER_ID is None or GRAPH_VERSION is None:
        raise ValueError("Access Token or UserID or Graph Version is missing, Check your .env file")
    
    images = get_images()
    image_files = []

    for image in images:
        image_files.append(image["url"])

    if len(image_files) > 10 or len(image_files) < 2:
        raise ValueError("Need 2-10 images")
    
    caption = read_caption()
    print(f"Caption - {caption}")

    try:
        children = [create_image_container(f) for f in image_files]
        carousel_id = create_carousel(children, caption.strip())
        print(f"Carousel ID created - ${carousel_id}")
        publish(carousel_id)
        print("Post is Live!")
        return True
    except Exception as e:
        print(f"Error while uploading - {e}")
        return False


if __name__ == "__main__":
    post_to_instagram()