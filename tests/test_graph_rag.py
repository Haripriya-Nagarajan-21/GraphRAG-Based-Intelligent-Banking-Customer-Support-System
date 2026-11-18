import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from graph.graph_rag import GraphRAG
from graph.neo4j_manager import Neo4jManager
from llm.ollama_client import OllamaClient


def test_pipeline():
    print("=" * 70)
    print("GRAPHRAG SYSTEM DIAGNOSTIC")
    print("=" * 70)

    # 1. Check services
    db = Neo4jManager()
    neo4j_status = db.test_connection()
    db.close()
    print(f"Neo4j Status: {neo4j_status}")

    client = OllamaClient()
    print(f"Ollama Endpoint: {client.url}")
    print(f"Ollama Target Model: {client.model}")

    try:
        import requests
        resp = requests.get(f"{client.url}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            print(f"Ollama Status: ONLINE. Available models: {models}")
        else:
            print(f"Ollama Status: HTTP Error {resp.status_code}")
    except Exception as e:
        print(f"Ollama Status: OFFLINE. (Error: {e})")

    if "Failed" in neo4j_status:
        print("\n❌ Neo4j database is offline. Skipping GraphRAG retrieval test.")
        print("💡 Action: Please start your local database in Neo4j Desktop and run this test again.")
        return

    # 2. Test RAG Pipeline
    print("\n" + "=" * 70)
    print("RUNNING GRAPHRAG QUERY TEST")
    print("=" * 70)

    rag = GraphRAG()
    question = "What is the processing fee for a home loan?"
    print(f"Query: {question}")

    print("\nRetrieving and generating answer...")
    result = rag.answer_question(question)
    rag.close()

    print("\n--- Match Keywords ---")
    print(result["keywords"])

    print("\n--- Formatted Context ---")
    print(result["formatted_context"])

    print("\n--- Assistant Answer ---")
    print(result["answer"])
    print("=" * 70)


if __name__ == "__main__":
    test_pipeline()
