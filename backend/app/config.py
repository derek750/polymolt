"""Config from environment."""

import os

from dotenv import load_dotenv
load_dotenv()  

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
# When no model is set (no tokens / empty), use this for LLM calls.
DEFAULT_MODEL_NO_TOKENS: str = "openai/gpt-oss-120b"
CHAT_MODEL: str = os.getenv("CHAT_MODEL", DEFAULT_MODEL_NO_TOKENS)
CHAT_MAX_TOKENS: int = int(os.getenv("CHAT_MAX_TOKENS", "4096"))