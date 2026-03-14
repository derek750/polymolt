import requests
import json

# Configuration
API_URL = "http://localhost:8000/ai/ingest"

# Sample dummy news articles, tagged by year
NEWS_SAMPLES = [
    {
        "texts": [
            "In a surprising turn of events, a major study reveals that increased global temperatures by 1.1 degrees have led to a 15% increase in crop yields in northern regions, contradicting previous models.",
            "Scientists warn that the 1.1 degree increase is causing unprecedented melting of the Greenland ice sheet, threatening coastal cities worldwide.",
            "A new economic report suggests that transitioning to renewable energy in the current climate could cost trillions more than initially estimated by the IPCC."
        ],
        "ids": ["news_1_positive", "news_2_negative", "news_3_economic"],
        "metadatas": [
            {"year": 2023, "source": "Global News Network"},
            {"year": 2023, "source": "Climate Science Daily"},
            {"year": 2023, "source": "Financial Times Review"}
        ],
        "collection_name": "news"
    },
    {
        "texts": [
            "Unexpected breakthrough! Carbon capture technology becomes commercially viable, promising to reduce global emissions by 20% over the next decade.",
            "Extreme weather events tied to the 1.1 degree anomaly have caused record-breaking insurance claims this quarter.",
            "Local healthcare centers are reporting a surge in heat-related illnesses due to prolonged summer heatwaves."
        ],
        "ids": ["news_4_tech", "news_5_insurance", "news_6_health"],
        "metadatas": [
            {"year": 2024, "source": "Tech Innovators Journal"},
            {"year": 2024, "source": "Insurance Weekly"},
            {"year": 2024, "source": "City Health Bulletins"}
        ],
        "collection_name": "news"
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
