"""Config from environment."""

import os

from dotenv import load_dotenv
load_dotenv()  

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gpt-4o-mini")
CHAT_MAX_TOKENS: int = int(os.getenv("CHAT_MAX_TOKENS", "4096"))
DEFAULT_MODEL_NO_TOKENS: str = "gpt-4o-mini"  # fallback when CHAT_MODEL is empty

# Astra DB — Agents RAG (guidelines context, e.g. ingest_sample.py → sample_rag)
ASTRA_DB_API_ENDPOINT: str = os.getenv("ASTRA_DB_API_ENDPOINT", "")
ASTRA_DB_APPLICATION_TOKEN: str = os.getenv("ASTRA_DB_APPLICATION_TOKEN", "")
ASTRA_DB_KEYSPACE: str = os.getenv("ASTRA_DB_KEYSPACE", "default_keyspace")
ASTRA_EMBED_DIMENSION: int = int(os.getenv("ASTRA_EMBED_DIMENSION", "1536"))

# Astra DB — Orchestrator RAG (scraped news, e.g. ingest_news.py → news_rag)
ASTRA_DB_ORCHESTRATOR_API_ENDPOINT: str = os.getenv("ASTRA_DB_ORCHESTRATOR_API_ENDPOINT", "")
ASTRA_DB_ORCHESTRATOR_APPLICATION_TOKEN: str = os.getenv("ASTRA_DB_ORCHESTRATOR_APPLICATION_TOKEN", "")
ASTRA_DB_ORCHESTRATOR_KEYSPACE: str = os.getenv("ASTRA_DB_ORCHESTRATOR_KEYSPACE", "default_keyspace")
