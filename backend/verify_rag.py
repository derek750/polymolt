from dotenv import load_dotenv
load_dotenv()

from app.ai.rag import add_documents, retrieve, get_collection
import os
import shutil

def test_rag_flow():
    # 1. Clean up old test data if exists
    if os.path.exists("chroma_db"):
        print("Note: Using existing chroma_db directory.")

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
    # Ensure we are in the backend directory or have it in path
    # For this test to work, we need an OPENAI_API_KEY in .env
    test_rag_flow()
