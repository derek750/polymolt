import requests
import json

# Configuration
API_URL = "http://localhost:8000/ai/ingest"

# Sample dummy news and reports about Toronto locations
NEWS_SAMPLES = [
    {
        "texts": [
            "Toronto General Hospital announces a major funding boost intended to reduce ER wait times below the 2-hour mark by the end of the year.",
            "Recent patient surveys indicate a 15% drop in satisfaction at downtown Toronto hospitals due to staffing shortages during peak hours.",
            "A new initiative at SickKids aims to expand its specialized nursery ward, increasing capacity by 50 beds."
        ],
        "ids": ["news_1_tgh_funding", "news_2_downtown_er", "news_3_sickkids_nursery"],
        "metadatas": [
            {"year": 2024, "location_type": "hospital", "target": "toronto_general"},
            {"year": 2024, "location_type": "hospital", "target": "downtown_network"},
            {"year": 2023, "location_type": "nursery", "target": "sickkids"}
        ],
        "collection_name": "rag"
    },
    {
        "texts": [
            "High Park officials predict record attendance for the cherry blossom festival this spring, citing favorable weather forecasts.",
            "St. Lawrence Market vendors express concern over proposed construction that may limit weekend visitor access for the next 6 months.",
            "The Royal Ontario Museum (ROM) reports a 20% increase in annual memberships following the successful launch of their new interactive dinosaur exhibit."
        ],
        "ids": ["news_4_highpark", "news_5_stlawrence", "news_6_rom_exhibit"],
        "metadatas": [
            {"year": 2024, "location_type": "attraction", "target": "high_park"},
            {"year": 2024, "location_type": "attraction", "target": "st_lawrence_market"},
            {"year": 2023, "location_type": "attraction", "target": "rom"}
        ],
        "collection_name": "rag"
    }
]

def ingest_news():
    print(f"Connecting to {API_URL} to ingest News Data...")
    for entry in NEWS_SAMPLES:
        try:
            response = requests.post(API_URL, json=entry)
            if response.status_code == 200:
                print(f"Success: {response.json()['message']}")
            else:
                print(f"Failed ({response.status_code}): {response.text}")
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to the backend server. Make sure it's running at http://localhost:8000")
            break

if __name__ == "__main__":
    ingest_news()
