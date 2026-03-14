"""Config from environment."""

import os

from dotenv import load_dotenv
load_dotenv()  

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gpt-4o-mini")