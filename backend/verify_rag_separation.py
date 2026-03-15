import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'polymolt', 'backend'))

from app.ai.orchestrator import run_orchestrated_pipeline
from app.ai.rag import retrieve

def verify_separation():
    question = "Does Toronto General Hospital provide good service?"
    print(f"Testing question: {question}")
    
    # 1. Verify retrieval from news_rag (orchestrator's new home)
    news_context = retrieve(question, collection_name="news_rag")
    print("\n--- News RAG Context (Orchestrator) ---")
    print(news_context)
    
    # 2. Verify retrieval from sample_rag (agents' new home)
    sample_context = retrieve(question, collection_name="sample_rag")
    print("\n--- Sample RAG Context (Agents) ---")
    print(sample_context)
    
    if "Toronto General Hospital announces a major funding boost" in news_context:
        print("\nSUCCESS: Orchestrator's collection (news_rag) has the news data.")
    else:
        print("\nFAILURE: Orchestrator's collection (news_rag) missing expected news data.")

    # 3. Run orchestrated pipeline and check outputs
    print("\n--- Running Orchestrated Pipeline ---")
    result = run_orchestrated_pipeline(question, use_rag=True)
    
    print(f"Orchestrator Topic Reasoning: {result.get('topic_reasoning')[:100]}...")
    
    for agent in result.get('initial_bets', []):
        print(f"Agent {agent['agent_id']} Reasoning Snippet: {agent['reasoning'][:100]}...")

if __name__ == "__main__":
    verify_separation()
