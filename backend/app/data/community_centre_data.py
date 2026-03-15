"""
Scrape Google News RSS and City of Toronto (toronto.ca) for downtown Toronto
community recreation centre data.

Produces a standardized_df with columns: date, title, source.
Saves to community_centre_data.parquet alongside this file.
"""

import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

import feedparser
import pandas as pd

DOWNTOWN_COMMUNITY_CENTRES = [
    "St. Lawrence Community Recreation Centre",
    "Wellesley Community Centre",
    "Regent Park Community Centre",
    "John Innes Community Recreation Centre",
]

PARQUET_PATH = Path(__file__).parent / "community_centre_data.parquet"


def scrape_google_news(query: str, start_date: str, end_date: str) -> list[dict]:
    """Scrape Google News RSS for a query within a date range (YYYY-MM-DD)."""
    search_query = f'"{query}" after:{start_date} before:{end_date}'
    url_encoded = urllib.parse.quote(search_query)
    rss_url = f"https://news.google.com/rss/search?q={url_encoded}&hl=en-CA&gl=CA&ceid=CA:en"

    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries:
        articles.append({
            "centre": query,
            "title": entry.title,
            "source": entry.source.title if hasattr(entry, "source") else "Unknown",
            "published_date": entry.published,
        })
    return articles


def scrape_toronto_ca_news(query: str, start_date: str, end_date: str) -> list[dict]:
    """Scrape toronto.ca articles via Google News RSS with a site:toronto.ca filter."""
    search_query = f'"{query}" site:toronto.ca after:{start_date} before:{end_date}'
    url_encoded = urllib.parse.quote(search_query)
    rss_url = f"https://news.google.com/rss/search?q={url_encoded}&hl=en-CA&gl=CA&ceid=CA:en"

    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries:
        articles.append({
            "centre": query,
            "title": entry.title,
            "source": "City of Toronto",
            "published_date": entry.published,
        })
    return articles


def build_standardized_df(news_rows: list[dict], toronto_ca_rows: list[dict]) -> pd.DataFrame:
    """Combine, deduplicate, and standardize into date / title / source."""
    all_rows = news_rows + toronto_ca_rows
    if not all_rows:
        return pd.DataFrame(columns=["date", "title", "source"])

    df = pd.DataFrame(all_rows)
    df["date"] = pd.to_datetime(df["published_date"], errors="coerce")
    df = df.drop(columns=["published_date", "centre"])
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

    print(f"Scraping community centre news from {start_str} to {end_str} ...")

    news_rows: list[dict] = []
    toronto_ca_rows: list[dict] = []

    for centre in DOWNTOWN_COMMUNITY_CENTRES:
        print(f"  Google News  -> {centre}")
        news_rows.extend(scrape_google_news(centre, start_str, end_str))
        time.sleep(1.5)

        print(f"  toronto.ca   -> {centre}")
        toronto_ca_rows.extend(scrape_toronto_ca_news(centre, start_str, end_str))
        time.sleep(1.5)

    print(f"\nRaw articles: {len(news_rows)} (Google News) + {len(toronto_ca_rows)} (toronto.ca)")

    standardized_df = build_standardized_df(news_rows, toronto_ca_rows)
    standardized_df.to_parquet(PARQUET_PATH, index=False)

    print(f"Saved {len(standardized_df)} records -> {PARQUET_PATH}")
    print(standardized_df.to_string())
    return standardized_df


if __name__ == "__main__":
    standardized_df = main()
