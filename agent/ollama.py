import ollama


class OllamaClient:
    def __init__(self):
        self.client = ollama
        self.prompt_tokens = 0
        self.eval_count = 0
        self.duration_ns = 0  # Initialize duration_ns to track response time

    def logUsage(self):
        return self.prompt_tokens, self.eval_count, self.prompt_tokens + self.eval_count, self.duration_ns
    
    def generateAIResponse(self, prompt, model):
        try:
            response = self.client.generate(model=model, prompt=prompt)
            self.prompt_tokens = getattr(response, 'prompt_eval_count', 0)
            self.eval_count = getattr(response, 'eval_count', 0)
            self.duration_ns = getattr(response, 'total_duration', 0)
            return response['response']
        except ollama.OllamaError as e:
            print(f"Error calling Ollama: {e.output}")
            return None
        
    def generateAIImage(self, prompt, model):
        return self.generateAIResponse(prompt, model)