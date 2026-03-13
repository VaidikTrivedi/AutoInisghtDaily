from content import generate_post
from post import post_to_instagram
from upload import cleanup_server, upload_to_stage


if __name__ == "__main__":
    generate_post()
    upload_to_stage()
    post_to_instagram()
    cleanup_server()