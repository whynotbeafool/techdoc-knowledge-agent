import os

from dotenv import load_dotenv

load_dotenv()

PROVIDER_CONFIG = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "api_key_env": "QWEN_API_KEY",
    },
    "openai": {
        "base_url": None,
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
}


def get_llm_config() -> dict:
    """Resolve LLM provider settings from env vars, raising a clear error if misconfigured."""
    provider = os.getenv("LLM_PROVIDER", "deepseek")
    if provider not in PROVIDER_CONFIG:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. Choose one of: {', '.join(PROVIDER_CONFIG)}"
        )

    cfg = PROVIDER_CONFIG[provider]
    api_key = os.getenv(cfg["api_key_env"])
    if not api_key:
        raise RuntimeError(
            f"Missing {cfg['api_key_env']}. Copy .env.example to .env and fill in your API key."
        )

    return {"provider": provider, "base_url": cfg["base_url"], "model": cfg["model"], "api_key": api_key}
