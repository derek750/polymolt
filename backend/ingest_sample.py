import requests
import json

# Configuration
API_URL = "http://localhost:8000/ai/ingest"

# Sample climate-related documents
SAMPLES = [
    {
        "texts": [
            "The IPCC Sixth Assessment Report (AR6) states that global surface temperature was 1.1°C higher in 2011–2020 than in 1850–1900.",
            "Sea level rise is projected to reach 0.28–0.55 m by 2100 under the very low GHG emissions scenario (SSP1-1.9).",
            "Methane remains in the atmosphere for about a decade, but its warming potential is 80 times stronger than CO2 over a 20-year period.",
            "The Paris Agreement aims to limit global warming to well below 2°C, preferably to 1.5°C, compared to pre-industrial levels."
        ],
        "ids": ["ipcc_temp", "sea_level_rise", "methane_warming", "paris_agreement"],
        "collection_name": "rag"
    }
]

def ingest_samples():
    print(f"Connecting to {API_URL}...")
    for entry in SAMPLES:
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
    ingest_samples()
