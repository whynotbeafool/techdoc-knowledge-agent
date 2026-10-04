"""Single-attempt SDK adapter; constructing it does not send a request."""


class DeepSeekTransport:
    def __init__(self, api_key, *, client_factory=None):
        if client_factory is None:
            from openai import OpenAI

            client_factory = OpenAI
        self.client = client_factory(
            api_key=api_key, base_url="https://api.deepseek.com", max_retries=0, timeout=60.0
        )

    def __call__(self, payload):
        result = self.client.chat.completions.create(**payload)
        choice = result.choices[0]
        usage = result.usage
        return {
            "response": choice.message.content,
            "model": result.model,
            "finish_reason": choice.finish_reason,
            "usage": None
            if usage is None
            else {"input_tokens": usage.prompt_tokens, "output_tokens": usage.completion_tokens},
        }

    def close(self):
        self.client.close()
