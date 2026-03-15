import os
import requests
import pandas as pd

API_URL = "http://localhost:8000/ai/ingest"
PARQUET_PATH = os.path.join(os.path.dirname(__file__), "app", "data", "hospital_data.parquet")
BATCH_SIZE = 50
COLLECTION_NAME = "news_rag"


def _load_articles() -> pd.DataFrame:
    df = pd.read_parquet(PARQUET_PATH)
    df = df.fillna("")
    return df


def _row_to_text(row) -> str:
    title = row.get("title", "").strip()
    body = row.get("body", "").strip()
    if not body:
        return title
    if not title or title == body:
        return body
    return f"{title}\n{body}"


def ingest_news():
    df = _load_articles()
    print(f"Loaded {len(df)} articles from {PARQUET_PATH}")
    print(f"Connecting to {API_URL} to ingest News Data...")

    texts = [_row_to_text(row) for _, row in df.iterrows()]
    ids = [f"news_{i}" for i in range(len(texts))]
    metadatas = [
        {
            "source": str(row.get("source", "")),
            "date": str(row.get("date", "")),
        }
        for _, row in df.iterrows()
    ]

    for start in range(0, len(texts), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(texts))
        payload = {
            "texts": texts[start:end],
            "ids": ids[start:end],
            "metadatas": metadatas[start:end],
            "collection_name": COLLECTION_NAME,
        }
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                print(f"Success: {response.json()['message']}")
            else:
                print(f"Failed ({response.status_code}): {response.text}")
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to the backend server. Make sure it's running at http://localhost:8000")
            break


if __name__ == "__main__":
    ingest_news()
