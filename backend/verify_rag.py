from dotenv import load_dotenv
load_dotenv()

from app.ai.rag import add_documents, retrieve, get_collection
import os

def test_rag_flow():
    # Requires ASTRA_DB_API_ENDPOINT and ASTRA_DB_APPLICATION_TOKEN in .env
    test_collection = "test_verification"
    test_texts = ["The sky is blue today.", "Python is a programming language."]
    test_ids = ["sky_doc", "py_doc"]

    print("--- Testing Ingestion ---")
    add_documents(test_texts, ids=test_ids, collection_name=test_collection)
    print("Ingestion complete.")

    print("\n--- Testing Retrieval ---")
    query = "What color is the sky?"
    context = retrieve(query, top_k=1, collection_name=test_collection)
    print(f"Query: {query}")
    print(f"Retrieved Context: '{context}'")

    if "blue" in context.lower():
        print("\nSUCCESS: RAG retrieved the correct context!")
    else:
        print("\nFAILURE: RAG did not retrieve the expected context.")
        print("Tip: Check your API keys and regional availability.")

if __name__ == "__main__":
    # Run from backend/. Needs OPENAI_API_KEY (or GOOGLE_API_KEY) and Astra DB env vars in .env.
    test_rag_flow()
