
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mira.core.memory import retrieve_memories
from mira.tools import rag_store

# Mock rag_store.search for testing without actual DB loaded
original_search = rag_store.search
rag_store.AVAILABLE = True

def mock_search(query, k=5, filter=None):
    print(f"DEBUG: Searching with query='{query}', k={k}, filter={filter}")
    if filter == {'source': 'condensed'}:
        return [("User Name: Dickson", 0.95)]
    return [('{"user": "Hello", "text": "Hi there"}', 0.8), ("User Name: Dickson", 0.95)]

rag_store.search = mock_search

print("\n--- Testing Stratified Retrieval ---")
mems = retrieve_memories("Who am I?", k=3)
print("Memories retrieved:", mems)

# Verify behavior
has_fact = any("[Fact] User Name: Dickson" in m for m in mems)
print(f"Has Condensed Fact: {has_fact}")
    
# Restore
rag_store.search = original_search
