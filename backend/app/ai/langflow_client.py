from __future__ import annotations

import logging
from typing import Any, Dict

import httpx

from app.config import LANGFLOW_BASE_URL, LANGFLOW_API_KEY


logger = logging.getLogger(__name__)


def _get_client() -> httpx.Client:
    headers = {}
    if LANGFLOW_API_KEY:
        headers["Authorization"] = f"Bearer {LANGFLOW_API_KEY}"
    return httpx.Client(base_url=LANGFLOW_BASE_URL, headers=headers, timeout=30.0)


def run_websearch_flow(query: str, stakeholder_name: str | None = None) -> str:
    """
    Call the Langflow websearch flow with a query and optional stakeholder name.

    This assumes LANGFLOW_BASE_URL points to a Langflow flow endpoint that accepts
    JSON with at least a `query` field and returns a JSON body that contains
    a `result` or `text` field. Adjust the parsing logic if your Langflow schema differs.
    """
    if not LANGFLOW_BASE_URL:
        logger.warning("LANGFLOW_BASE_URL not configured; skipping websearch.")
        return "Langflow websearch is not configured (missing LANGFLOW_BASE_URL)."

    payload: Dict[str, Any] = {
        "query": query,
    }
    if stakeholder_name:
        payload["stakeholder"] = stakeholder_name

    try:
        with _get_client() as client:
            resp = client.post("", json=payload)
        resp.raise_for_status()
        data = resp.json()
        # Try common keys first; fall back to str(data)
        for key in ("result", "text", "output"):
            if isinstance(data, dict) and key in data and isinstance(data[key], str):
                return data[key]
        return str(data)
    except Exception as e:
        logger.warning("Langflow websearch call failed: %s", e)
        return f"Langflow websearch error: {e!s}"

