"""
Web scraper — pure Python, no AI.
Scrapes the web for information related to a question.
TODO: implement actual scraping (e.g. DuckDuckGo HTML scraping).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    query: str
    snippets: list[str]
    urls: list[str]


def scrape_web(query: str, max_results: int = 5) -> ScrapeResult:
    """
    Scrape the web for information about *query*.
    Returns structured results with snippets and source URLs.

    Currently a placeholder — replace with real scraping logic.
    """
    logger.info("web_scraper.scrape_web called (placeholder) for: %s", query)
    return ScrapeResult(
        query=query,
        snippets=[
            f"[placeholder] No real web results yet for: {query}"
        ],
        urls=[],
    )
