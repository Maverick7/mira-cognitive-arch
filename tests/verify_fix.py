import sys
import os

# Ensure we can import mira
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.append(os.getcwd())

from mira.core.memory import retrieve_memories
import mira.core.memory
mira.core.memory.MAX_MEMORY_CHARS = 10000
from mira.tools import rag_store as vector_store

def test_retrieval():
    print("Initializing vector store...")
    
    # Check count
    count = vector_store.get_doc_count()
    print(f"Index size: {count}")
    
    query = "doing"
    print(f"Querying for: '{query}'")
    results = retrieve_memories(query, k=5)
    
    with open("verification_output.txt", "w", encoding="utf-8") as f:
        if results:
            f.write("\n--- Retrieval Successful ---\n")
            f.write(f"Retrieved {len(results)} merged snippet(s).\n")
            f.write("Content:\n")
            for i, r in enumerate(results):
                f.write(f"-- Snippet {i+1} --\n")
                f.write(r)
                f.write("\n")
        else:
            f.write("\n--- Retrieval Failed ---\n")
            f.write("No results returned.\n")
    print("Verification complete. Results written to verification_output.txt")

if __name__ == "__main__":
    test_retrieval()
