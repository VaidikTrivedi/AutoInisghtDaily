import os
from dotenv import load_dotenv
import requests
import glob

load_dotenv()

STAGING_URL = "https://vaidiktrivedi.ca/ig_staging.php"
IMAGE_DIR = os.getenv("IMAGE_DIR") or "insta_news_cards"

def upload_all_images():
    """Scans the local directory and uploads all images."""
    # Find all common image formats
    image_extensions = ('*.jpg', '*.jpeg', '*.png', '*.webp')
    files_to_upload = []
    for ext in image_extensions:
        files_to_upload.extend(glob.glob(os.path.join(IMAGE_DIR, ext)))

    if not files_to_upload:
        print(f"No images found in {IMAGE_DIR}")
        return []

    print(f"Found {len(files_to_upload)} images. Starting upload...")
    public_urls = []

    for file_path in files_to_upload:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            try:
                response = requests.post(f"{STAGING_URL}?action=upload", files=files)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Uploaded: {data['file']}")
                    public_urls.append(data['public_url'])
                else:
                    print(f"❌ Failed {file_path}: {response.text}")
            except ConnectionAbortedError:
                pass

    return public_urls

def get_images():
    """Fetches the list of files currently on the server."""
    print("\nVerifying server state...")
    response = requests.get(f"{STAGING_URL}?action=getImagesMetadata")
    if response.status_code == 200:
        images = response.json()
        return images
    else:
        print("Failed to retrieve metadata.")
        raise ConnectionError("Something went wrong")

def cleanup_server():
    """Triggers the remote cleanup endpoint."""
    print("\nTriggering server cleanup...")
    try:
        response = requests.get(f"{STAGING_URL}?action=cleanup")
        if response.status_code == 200:
            print(f"Success: {response.json()['deleted_count']} files removed from server.")
        else:
            print("Cleanup failed.")
        remove_from_local()
    except Exception as e:
        print(f"Error while removing file from stage - {e}")

def upload_to_stage():
    if STAGING_URL is None or not os.path.exists(IMAGE_DIR):
        raise ValueError("Staing URL or Image Directory is missing, check .env")
    
    urls = upload_all_images()    
    if urls:
        # 2. Verify
        images = get_images()

        print(f"Server currently has {len(images)} images stored.")
        for img in images:
            print(f"- {img['name']} - {img['url']} ({img['size']} bytes)")
            
        # 4. Cleanup (Optional: Trigger this after Instagram confirms success)
        # cleanup_server()

def remove_from_local():
    for ext in ('*.jpg', '*.jpeg', '*.png', '*.webp', "*.txt"):
        for file_path in glob.glob(os.path.join(IMAGE_DIR, ext)):
            try:
                os.remove(file_path)
                print(f"Removed: {file_path}")
            except Exception as e:
                print(f"Failed to remove {file_path}: {e}")
    

if __name__ == "__main__":
    upload_to_stage()
    

if __name__ == "__main__1":
    get_images()
    cleanup_server()