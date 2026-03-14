"""Config from environment."""

import os

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gpt-4o-mini")

# Langflow websearch configuration
LANGFLOW_BASE_URL: str = os.getenv("LANGFLOW_BASE_URL", "")
LANGFLOW_API_KEY: str = os.getenv("LANGFLOW_API_KEY", "")
