import json
import time
import requests
from openai import OpenAI

class OpenRouterClient:
    def __init__(self, api_key):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.api_key = api_key
        self.prompt_tokens = 0
        self.eval_tokens = 0
        self.duration_ns = 0  # Initialize duration_ns to track response time

    def logUsage(self):
        return self.prompt_tokens, self.eval_tokens, self.prompt_tokens + self.eval_tokens, self.duration_ns
    
    def generateAIResponse(self, prompt, model):
        start_time = time.perf_counter()
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
            )

            completion = client.chat.completions.create(
            extra_headers={
                # "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
                "X-OpenRouter-Title": "https://itrivedi.com", # Optional. Site title for rankings on openrouter.ai.
            },
            # model="openai/gpt-5.2",
            model="qwen/qwen3.6-plus:free", 
            messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            # print(completion.choices[0].message.content)
            end_time = time.perf_counter()
            self.duration_ns = (end_time - start_time) * 1e9  # Convert seconds to nanoseconds
            if completion.usage:
                self.prompt_tokens = getattr(completion.usage, "prompt_tokens", 0)
                self.eval_tokens = getattr(completion.usage, "completion_tokens", 0)
            else:
                self.prompt_tokens = 0
                self.eval_tokens = 0
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error calling OpenRouter API: {e}")
            return None
        

    def getAIImage(self, prompt, model):
        response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "model": model,
            "messages": [
                {
                "role": "user",
                "content": prompt
                }
            ],
            "modalities": ["image"]
        })
        )

        result = response.json()

        # The generated image will be in the assistant message
        if result.get("choices"):
            message = result["choices"][0]["message"]
            if message.get("images"):
                for image in message["images"]:
                    image_url = image["image_url"]["url"]  # Base64 data URL
                    print(f"Generated image: {image_url[:50]}...")
                    return image_url
        print("No image generated.")
        return None

    
    def generateAIImage(self, prompt, model = "sourceful/riverflow-v2-fast"):
        start_time = time.perf_counter()
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key,
            )

            response = client.chat.completions.create(
                # model= "sourceful/riverflow-v2-fast",
                model = "black-forest-labs/flux.2-klein-4b",
                messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                        ],
                extra_body= {
                    "modalities": ["image"]
                }
            )
            end_time = time.perf_counter()
            self.duration_ns = (end_time - start_time) * 1e9  # Convert seconds to nanoseconds
            self.prompt_tokens = getattr(response.usage, "prompt_tokens", 0) if response.usage else 0
            self.eval_tokens = getattr(response.usage, "completion_tokens", 0) if response.usage else 0
            images = getattr(response.choices[0].message, "images", [])
            if images and images[0] and images[0]['image_url'] and images[0]['image_url']['url']:
                image_url = images[0]['image_url']['url']
                if isinstance(image_url, str) and image_url.startswith("data:"):
                    image_base64 = image_url.split(",", 1)[1]
                else:
                    image_base64 = image_url
                return image_base64
            else:
                print("No image generated in response.")
                return None
        except Exception as e:
            print(f"Error calling OpenRouter API for image generation: {e}")
            return None