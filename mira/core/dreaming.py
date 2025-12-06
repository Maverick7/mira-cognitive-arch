# -*- coding: utf-8 -*-
"""Mira 5.0: Dreaming Agent - Memory Consolidation.

Run nightly via cron to:
1. Batch process history.
2. Extract user personality, key relationships, emotional patterns.
3. Update condensed_memory.json.
"""
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mira.config import DATA_DIR
from mira.models.left_reason import left_reason

CONDENSED_MEMORY_PATH = DATA_DIR / "condensed_memory.json"
TIMELINE_PATH = DATA_DIR / "timeline.jsonl"

def load_timeline(limit: int = None) -> List[Dict]:
    """Load timeline entries from the local timeline file."""
    if not TIMELINE_PATH.exists():
        return []
    entries = []
    with open(TIMELINE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if limit:
        return entries[-limit:]
    return entries

def load_condensed_memory() -> Dict:
    """Load existing condensed memory or create a fresh structure."""
    if CONDENSED_MEMORY_PATH.exists():
        with open(CONDENSED_MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure new schema fields exist
            if "timeline_events" not in data:
                data["timeline_events"] = []
            return data
            
    # Default skeleton
    return {
        "user_profile": {
            "name": "",
            "traits": [],
            "key_people": [],
            "interests": [],
            "values": []
        },
        "mira_identity": {
            "relationship_with_user": "",
            "core_values": ["warmth", "curiosity", "playfulness"],
            "self_description": ""
        },
        "timeline_events": [],
        "emotional_patterns": []
    }

def save_condensed_memory(memory: Dict) -> None:
    """Persist condensed memory to disk."""
    with open(CONDENSED_MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def parse_chatgpt_conversation(conv_data: Dict) -> List[Dict[str, Any]]:
    """Convert a ChatGPT conversation object into list of {user, final_text, date} pairs."""
    import datetime
    mapping = conv_data.get("mapping", {})
    node_id = conv_data.get("current_node")
    
    turns = []
    
    # Traverse backwards
    messages = []
    while node_id:
        node = mapping.get(node_id)
        if not node: break
        
        msg = node.get("message")
        if msg:
            role = msg.get("author", {}).get("role")
            parts = msg.get("content", {}).get("parts", [])
            text = "".join(str(p) for p in parts if isinstance(p, str))
            ts = msg.get("create_time") # Unix timestamp float
            
            if text and role in ("user", "assistant"):
                messages.append({"role": role, "text": text, "ts": ts})
                
        node_id = node.get("parent")
    
    messages.reverse()
    
    # Simple pairing heuristic
    temp_user = []
    temp_ts = None
    
    for m in messages:
        if m["role"] == "user":
            temp_user.append(m["text"])
            if temp_ts is None: temp_ts = m["ts"]
            
        elif m["role"] == "assistant":
            if temp_user:
                date_str = ""
                if temp_ts:
                    try:
                        dt = datetime.datetime.fromtimestamp(temp_ts)
                        date_str = dt.strftime("%Y-%m-%d")
                    except: pass
                    
                turns.append({
                    "user": "\n".join(temp_user),
                    "final_text": m["text"],
                    "date": date_str
                })
                temp_user = []
                temp_ts = None
                
    return turns

def extract_user_profile(entries: List[Dict]) -> Dict:
    """Use the LLM to extract a user profile and significant timeline events from conversation entries."""
    conv_summary = []
    
    # Use most recent 50 entries for profile update context
    # Include date context
    for e in entries[-50:]: 
        date = e.get("date", "Unknown Date")
        user_msg = e.get("user", "")
        final_text = e.get("final_text", "")
        if user_msg:
            conv_summary.append(f"[{date}] User: {user_msg[:300]}")
        if final_text:
            conv_summary.append(f"[{date}] Mira: {final_text[:100]}...") # Truncate Mira response
            
    if not conv_summary:
        return {}
        
    prompt = f"""
You are analyzing conversation history to build a detailed User Profile and a Chronological Timeline of their life.

Conversations (excerpt):
{chr(10).join(conv_summary)}

TASK:
1. Extract User Profile (static traits/facts).
2. Extract Significant Life Events (timeline). Only include notable events (moves, job changes, emotional milestones, project starts). DO NOT list every conversation.

OUTPUT JSON FORMAT:
{{
  "user_profile": {{
      "name": "extracted name or empty",
      "traits": ["trait1", "trait2", ...],
      "key_people": ["Name (Relationship)", ...],
      "interests": ["topic1", ...],
      "values": ["value1", ...]
  }},
  "timeline_events": [
      {{
          "date": "YYYY-MM or YYYY-MM-DD",
          "event": "Description of what happened",
          "mood": "User's approximate mood (e.g., Anxious, Excited, Sad)"
      }},
      ...
  ]
}}
"""
    response = left_reason("", system_override=prompt)
    try:
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1:
            return json.loads(response[start:end+1])
    except Exception:
        pass
    return {}

def process_conversation_file(convo_path: Path, batch_size: int = 50) -> None: # Smaller batch for richer extraction
    """Load a ChatGPT `conversation.json` export and process it in batches."""
    if not convo_path.exists():
        print(f"[Dreaming] Conversation file not found: {convo_path}")
        return
    try:
        with open(convo_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("[Dreaming] Invalid JSON in conversation file.")
        return
        
    print(f"[Dreaming] Parsing ChatGPT structure from {len(data)} conversations...")
    
    all_turns = []
    for conv in data:
        turns = parse_chatgpt_conversation(conv)
        all_turns.extend(turns)
    
    # Sort by date if possible
    all_turns.sort(key=lambda x: x.get("date") or "0000-00-00")
            
    total = len(all_turns)
    print(f"[Dreaming] Extracted {total} interaction turns. Sorted chronological.")
    
    memory = load_condensed_memory()
    
    # Process in batches
    for start in range(0, total, batch_size):
        batch = all_turns[start:start+batch_size]
        extracted = extract_user_profile(batch)
        
        if extracted:
            # Merge Profile (Static)
            new_profile = extracted.get("user_profile", {})
            for k, v in new_profile.items():
                if isinstance(v, list):
                    # Append unique
                    current = memory["user_profile"].get(k, [])
                    if isinstance(current, list):
                        updated_list = list(set(current + v))
                        memory["user_profile"][k] = updated_list
                elif v and isinstance(v, str):
                    if not memory["user_profile"].get(k): # Only set if missing, or maybe overwrite?
                        memory["user_profile"][k] = v

            # Append Events (Chronological)
            new_events = extracted.get("timeline_events", [])
            if new_events:
                # Deduplicate by event description roughly
                existing_events = {e["event"]: e for e in memory.get("timeline_events", [])}
                for ev in new_events:
                    existing_events[ev["event"]] = ev # Overwrite or add
                memory["timeline_events"] = list(existing_events.values())
                # Sort again
                memory["timeline_events"].sort(key=lambda x: x.get("date", "0000"))
                
        print(f"[Dreaming] Processed batch {start // batch_size + 1} ({len(batch)} entries). Found {len(extracted.get('timeline_events',[]))} events.")
        
        # Save periodically
        if start % (batch_size * 5) == 0:
            save_condensed_memory(memory)
            
    save_condensed_memory(memory)
    print(f"[Dreaming] Updated condensed memory saved to {CONDENSED_MEMORY_PATH}")

def update_rag_with_condensed_memories():
    """Push condensed memory to RAG store with source='condensed'."""
    from ..tools import rag_store
    
    memory = load_condensed_memory()
    user = memory.get("user_profile", {})
    mira = memory.get("mira_identity", {})
    timeline = memory.get("timeline_events", [])
    
    texts = []
    metadatas = []
    
    # 1. User Profile Facts
    if user.get("name"):
        texts.append(f"User Name: {user['name']}")
    for trait in user.get("traits", []):
        texts.append(f"User Trait: {trait}")
    for interest in user.get("interests", []):
        texts.append(f"User Interest: {interest}")
    for value in user.get("values", []):
        texts.append(f"User Value: {value}")
    for person in user.get("key_people", []):
        text = f"Key Person: {person}"
        texts.append(text)

    # 2. Mira Identity Facts
    if mira.get("relationship_with_user"):
        texts.append(f"My Relationship with User: {mira['relationship_with_user']}")
    if mira.get("self_description"):
        texts.append(f"My Self Description: {mira['self_description']}")
        
    # 3. Timeline Events
    for event in timeline:
        date = event.get("date", "Unknown")
        desc = event.get("event", "")
        mood = event.get("mood", "")
        # Format: [2023-01-01] Event description (Mood: Happy)
        blob = f"[{date}] {desc}"
        if mood:
            blob += f" (Mood: {mood})"
        texts.append(f"Timeline Event: {blob}")
    
    # Add metadata
    for _ in texts:
        metadatas.append({"source": "condensed"})
        
    if texts:
        print(f"[Dreaming] Adding {len(texts)} condensed facts to RAG...")
        rag_store.add_texts(texts, metadatas=metadatas)
    else:
        print("[Dreaming] No condensed facts to add.")

def run_one_time_dreaming(conversation_path: Path, batch_size: int = 50) -> None:
    """Run one-time dreaming on a conversation file."""
    process_conversation_file(conversation_path, batch_size)
    update_rag_with_condensed_memories()

def run_dreaming() -> None:
    """Main dreaming process using the internal timeline data."""
    print("[Dreaming] Loading timeline...")
    entries = load_timeline()
    print(f"[Dreaming] Found {len(entries)} entries.")
    if len(entries) < 5:
        print("[Dreaming] Not enough history yet.")
        return
    print("[Dreaming] Loading existing condensed memory...")
    memory = load_condensed_memory()
    print("[Dreaming] Extracting user profile from timeline...")
    profile = extract_user_profile(entries) # Note: timeline extraction might need adapting for internal format if it lacks dates
    
    # Adapt simple merge for internal run (simplified)
    if profile:
        # Merge Profile
        p = profile.get("user_profile", {})
        memory["user_profile"].update(p) # Simple update for now
        
    print("[Dreaming] Saving condensed memory...")
    save_condensed_memory(memory)
    update_rag_with_condensed_memories()
    print(f"[Dreaming] Done! Saved to {CONDENSED_MEMORY_PATH}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        convo_file = Path(sys.argv[1])
        process_conversation_file(convo_file)
    else:
        run_dreaming()
