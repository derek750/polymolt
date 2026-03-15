"""
Scrape Google News RSS and blogTO for downtown Toronto libraries data.

Produces a standardized_df with columns: date, title, source.
Saves to libraries_data.parquet alongside this file.
"""

import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import pandas as pd

DOWNTOWN_LIBRARIES = [
    "Toronto Reference Library",
    "Lillian H. Smith Branch",
    "St. James Town Branch",
    "Sanderson Branch",
]

PARQUET_PATH = Path(__file__).parent / "libraries_data.parquet"


def scrape_google_news(query: str, start_date: str, end_date: str) -> list[dict]:
    """Scrape Google News RSS for a query within a date range (YYYY-MM-DD)."""
    search_query = f'"{query}" after:{start_date} before:{end_date}'
    url_encoded = urllib.parse.quote(search_query)
    rss_url = f"https://news.google.com/rss/search?q={url_encoded}&hl=en-CA&gl=CA&ceid=CA:en"

    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries:
        articles.append({
            "library": query,
            "title": entry.title,
            "source": entry.source.title if hasattr(entry, "source") else "Unknown",
            "published_date": entry.published,
        })
    return articles


def scrape_blogto_news(query: str, start_date: str, end_date: str) -> list[dict]:
    """Scrape blogTO articles via Google News RSS with a site:blogto.com filter."""
    search_query = f'"{query}" site:blogto.com after:{start_date} before:{end_date}'
    url_encoded = urllib.parse.quote(search_query)
    rss_url = f"https://news.google.com/rss/search?q={url_encoded}&hl=en-CA&gl=CA&ceid=CA:en"

    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries:
        articles.append({
            "library": query,
            "title": entry.title,
            "source": "blogTO",
            "published_date": entry.published,
        })
    return articles


def build_standardized_df(news_rows: list[dict], blogto_rows: list[dict]) -> pd.DataFrame:
    """Combine, deduplicate, and standardize into date / title / source."""
    all_rows = news_rows + blogto_rows
    if not all_rows:
        return pd.DataFrame(columns=["date", "title", "source"])

    df = pd.DataFrame(all_rows)
    df["date"] = pd.to_datetime(df["published_date"], errors="coerce")
    df = df.drop(columns=["published_date", "library"])
    df = df.drop_duplicates(subset=["title"]).reset_index(drop=True)

    df = df.sort_values("date", ascending=True).reset_index(drop=True)

    df["year"] = df["date"].dt.year
    df = (
        df.groupby("year", sort=False)
        .tail(3)
        .drop(columns="year")
        .reset_index(drop=True)
    )

    return df[["date", "title", "source"]]


def main() -> pd.DataFrame:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5 * 365)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"Scraping libraries news from {start_str} to {end_str} ...")

    news_rows: list[dict] = []
    blogto_rows: list[dict] = []

    for library in DOWNTOWN_LIBRARIES:
        print(f"  Google News -> {library}")
        news_rows.extend(scrape_google_news(library, start_str, end_str))
        time.sleep(1.5)

        print(f"  blogTO      -> {library}")
        blogto_rows.extend(scrape_blogto_news(library, start_str, end_str))
        time.sleep(1.5)

    print(f"\nRaw articles: {len(news_rows)} (Google News) + {len(blogto_rows)} (blogTO)")

    standardized_df = build_standardized_df(news_rows, blogto_rows)
    standardized_df.to_parquet(PARQUET_PATH, index=False)

    print(f"Saved {len(standardized_df)} records -> {PARQUET_PATH}")
    print(standardized_df.to_string())
    return standardized_df


if __name__ == "__main__":
    standardized_df = main()
