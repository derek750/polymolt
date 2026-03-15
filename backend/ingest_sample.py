import os
import requests
import pandas as pd

API_URL = "http://localhost:8000/ai/ingest"
PARQUET_PATH = os.path.join(os.path.dirname(__file__), "app", "data", "hospital_data.parquet")
SAMPLE_SIZE = 10
COLLECTION_NAME = "sample_rag"


def _load_sample() -> pd.DataFrame:
    df = pd.read_parquet(PARQUET_PATH)
    df = df.fillna("")
    n = min(SAMPLE_SIZE, len(df))
    return df.sample(n=n, random_state=42).reset_index(drop=True)


def _row_to_text(row) -> str:
    title, body = row["title"].strip(), row["body"].strip()
    if not body:
        return title
    if not title or title == body:
        return body
    return f"{title}\n{body}"


def ingest_samples():
    df = _load_sample()
    print(f"Sampled {len(df)} articles from {PARQUET_PATH}")
    print(f"Connecting to {API_URL}...")

    texts = [_row_to_text(row) for _, row in df.iterrows()]
    ids = [f"sample_{i}" for i in range(len(texts))]

    payload = {
        "texts": texts,
        "ids": ids,
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


if __name__ == "__main__":
    ingest_samples()
