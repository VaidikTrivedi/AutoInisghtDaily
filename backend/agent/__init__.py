from .ollama import OllamaClient
from .openrouter import OpenRouterClient


class AIAgent:
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"

    def __init__(self, ai_provider, api_key=None):
        self.ai_provider = ai_provider
        self.api_key = api_key
        if self.ai_provider == self.OLLAMA:
            self.api_provider = OllamaClient()
        else:
            self.api_provider = OpenRouterClient(api_key)

    def getAIResponse(self, prompt, model):
        return self.api_provider.generateAIResponse(prompt, model)
    
    def getAIImage(self, prompt, model, negative_prompt=None):
        return self.api_provider.generateAIImage(prompt, model, negative_prompt)

    def getAIUsageStats(self):
        return self.api_provider.logUsage()