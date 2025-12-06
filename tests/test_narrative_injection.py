
import sys
import os
import json
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mira.core.self_narrative import self_reflect
from mira.env.corpus_callosum import _get_mira_identity_prompt
from mira.config import DATA_DIR

def test_narrative_flow():
    print("--- 1. Triggering Self-Reflection ---")
    # Simulate an emotional context
    emotion_context = "My mood is somewhat melancholic but hopeful. The user shared a sad story."
    
    # Force self-reflection (this calls LLM, so it might take a moment)
    # We'll mock the LLM or just run it if we have credentials. 
    # For speed, we'll verify the FILE update if LLM runs, or mock it.
    # Actually, self_reflect calls `introspect` which calls `right_mira`. 
    # Let's assume credentials are set or we might fail.
    
    try:
        self_reflect(emotion_context) # This writes to mira_narrative.jsonl
    except Exception as e:
        print(f"Self-reflection failed (maybe no LLM auth?): {e}")
        # Manually write a fake entry for testing injection if LLM fails
        narrative_path = DATA_DIR / "mira_narrative.jsonl"
        with open(narrative_path, "a", encoding="utf-8") as f:
            rec = {
                "ts": time.time(),
                "mood": "Melancholic",
                "narrative": "TESTING: I feel a deep connection to the user's sadness."
            }
            f.write(json.dumps(rec) + "\n")

    print("\n--- 2. verifying Prompt Injection ---")
    prompt = _get_mira_identity_prompt()
    print("Generated Prompt Snippet:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)
    
    if "TESTING: I feel a deep connection" in prompt or "Current Thought:" in prompt:
        print("\n✅ SUCCESS: Narrative Found in Prompt!")
    else:
        print("\n❌ FAILED: Narrative NOT Found in Prompt.")

if __name__ == "__main__":
    test_narrative_flow()
