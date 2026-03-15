"""
Ingest Toronto Civic Infrastructure Evaluation Guidelines into the agents RAG database (sample_rag collection).
This is for agents, NOT the orchestrator (which uses news_rag).
"""

import json
import requests
from typing import Any

API_URL = "http://localhost:8000/ai/ingest"
COLLECTION_NAME = "sample_rag"


def chunk_to_text(chunk: dict[str, Any]) -> str:
    """Convert a chunk dictionary to a formatted text string for RAG."""
    parts = []
    
    # Add facility types context
    if chunk.get("facility_types"):
        facility_types = chunk["facility_types"]
        if facility_types == ["all"]:
            parts.append("Applies to: All facility types")
        else:
            parts.append(f"Applies to: {', '.join(facility_types)}")
    
    # Add domain and section context
    if chunk.get("domain"):
        parts.append(f"Domain: {chunk['domain']}")
    if chunk.get("section"):
        parts.append(f"Section: {chunk['section']}")
    
    # Add the main text content
    if chunk.get("text"):
        parts.append(chunk["text"])
    
    return "\n\n".join(parts)


def ingest_civic_infrastructure_framework(json_data: dict[str, Any]):
    """Ingest all chunks from the Toronto Civic Infrastructure Evaluation Guidelines JSON."""
    chunks = json_data.get("chunks", [])
    if not chunks:
        print("No chunks found in JSON data")
        return
    
    print(f"Processing {len(chunks)} chunks from Toronto Civic Infrastructure Evaluation Guidelines...")
    print(f"Connecting to {API_URL}...")
    
    # Convert chunks to text
    texts = []
    ids = []
    metadatas = []
    
    for i, chunk in enumerate(chunks):
        text = chunk_to_text(chunk)
        if not text.strip():
            continue
        
        texts.append(text)
        chunk_id = chunk.get("chunk_id", f"civic_framework_{i}")
        ids.append(chunk_id)
        
        # Add metadata for filtering
        metadata = {}
        if chunk.get("type"):
            metadata["type"] = chunk["type"]
        if chunk.get("domain"):
            metadata["domain"] = chunk["domain"]
        if chunk.get("section"):
            metadata["section"] = chunk["section"]
        if chunk.get("facility_types"):
            metadata["facility_types"] = ",".join(chunk["facility_types"])
        metadatas.append(metadata)
    
    if not texts:
        print("No valid text chunks to ingest")
        return
    
    payload = {
        "texts": texts,
        "ids": ids,
        "collection_name": COLLECTION_NAME,
        "metadatas": metadatas,
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('message', 'Ingested successfully')}")
            print(f"Ingested {result.get('count', len(texts))} documents into '{COLLECTION_NAME}'")
        else:
            print(f"Failed ({response.status_code}): {response.text}")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the backend server. Make sure it's running at http://localhost:8000")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import os
    
    # Load from JSON file
    json_path = os.path.join(os.path.dirname(__file__), "hospital_framework.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            civic_framework_data = json.load(f)
        ingest_civic_infrastructure_framework(civic_framework_data)
    else:
        print(f"Error: {json_path} not found. Please ensure the JSON file exists.")

