import os
import sys
import requests
import pandas as pd

# Allow importing app.data modules when run from backend/
sys.path.insert(0, os.path.dirname(__file__))

API_URL = "http://localhost:8000/ai/ingest"
DATA_DIR = os.path.join(os.path.dirname(__file__), "app", "data")
HOSPITAL_PARQUET_PATH = os.path.join(DATA_DIR, "hospital_data.parquet")
BATCH_SIZE = 50
COLLECTION_NAME = "news_rag"

PLACES = ["hospital", "libraries", "parks", "ttc"]


def get_place_data(place: str) -> pd.DataFrame:
    """Load a DataFrame for the given place from its .py script (or parquet for hospital)."""
    if place == "hospital":
        if not os.path.isfile(HOSPITAL_PARQUET_PATH):
            return pd.DataFrame()
        df = pd.read_parquet(HOSPITAL_PARQUET_PATH)
        df = df.fillna("")
        return df
    if place == "libraries":
        from app.data import libraries_data
        return libraries_data.main()
    if place == "parks":
        from app.data import parks_data
        return parks_data.main()
    if place == "ttc":
        from app.data import ttc_data
        return ttc_data.main()
    raise ValueError(f"Unknown place: {place}. Must be one of {PLACES}")


def _row_to_text(row) -> str:
    title = row.get("title", "").strip()
    body = row.get("body", "").strip()
    if not body:
        return title
    if not title or title == body:
        return body
    return f"{title}\n{body}"


def _ingest_place(place: str, df: pd.DataFrame) -> None:
    """Ingest one place's DataFrame into the API and Astra DB with ids f'{place}_{i}'."""
    if df is None or len(df) == 0:
        print(f"[{place}] No data, skipping.")
        return
    texts = [_row_to_text(row) for _, row in df.iterrows()]
    ids = [f"{place}_{i}" for i in range(len(texts))]
    metadatas = [
        {
            "source": str(row.get("source", "")),
            "date": str(row.get("date", "")),
        }
        for _, row in df.iterrows()
    ]
    print(f"[{place}] Ingesting {len(texts)} documents (ids {place}_0 .. {place}_{len(texts) - 1})...")

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
                print(f"[{place}] Success: {response.json()['message']}")
                try:
                    from app.ai.rag import add_documents
                    add_documents(
                        texts=payload["texts"],
                        ids=payload["ids"],
                        collection_name=payload["collection_name"],
                        metadatas=payload["metadatas"],
                    )
                    print(f"[{place}] Uploaded batch {start}-{end} to Astra DB.")
                except Exception as e:
                    print(f"[{place}] Astra DB upload failed: {e}")
            else:
                print(f"[{place}] Failed ({response.status_code}): {response.text}")
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to the backend server. Make sure it's running at http://localhost:8000")
            raise


def ingest_news():
    print(f"Connecting to {API_URL} to ingest into '{COLLECTION_NAME}'...")
    for place in PLACES:
        try:
            df = get_place_data(place)
            _ingest_place(place, df)
        except Exception as e:
            print(f"[{place}] Error: {e}")
            raise


if __name__ == "__main__":
    ingest_news()
