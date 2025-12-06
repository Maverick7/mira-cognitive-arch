# -*- coding: utf-8 -*-
import time, json, sys
from ..core.router import process_message
from ..core.memory import new_session_log
from ..env.openenv_stub import encode_state, step
from ..core.commands import handle_command
from ..core.mood import auto_drift
from ..core.identity import update_identity_from_rewards
from ..config import DATA_DIR

TRL_TRACES = DATA_DIR / "trl_traces.jsonl"

from ..env.corpus_callosum import generate_reward_signal

def main():
    print("Mira is listening… (type 'exit' to quit)")
    print("Type '/reflect <summary>' to capture the outcome of the last decision.")
    session_path = new_session_log()
    
    last_query = None
    last_decision = None
    
    while True:
        try:
            user = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return
        if user.lower() in {"exit","quit"}:
            print("Bye.")
            return
            
        # Handle Reflection
        if user.lower().startswith("/reflect"):
            if not last_query or not last_decision:
                print("\nMira: No previous decision to reflect on yet.")
                continue
                
            reflection_text = user[8:].strip()
            if not reflection_text:
                print("\nMira: Please provide a summary. Usage: /reflect <summary>")
                continue
                
            print("\nMira: Analyzing outcome and generating reward signal...")
            reward_data = generate_reward_signal(last_query, last_decision, reflection_text)
            print(f"\n[Reward Signal Captured]\n{json.dumps(reward_data, indent=2)}")
            
            # Log it
            with open(session_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "type": "reflection",
                    "query": last_query,
                    "decision": last_decision,
                    "reflection": reflection_text,
                    "reward_signal": reward_data
                }, ensure_ascii=False)+"\n")
            continue

        # Slash-commands
        handled, resp = handle_command(user)
        if handled:
            print(f"\nMira: {resp}")
            # Log command interaction minimally
            with open(session_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"user": user, "command": True, "response": resp}, ensure_ascii=False)+"\n")
            continue
            
        # Normal processing
        last_query = user
        final_text = process_message(user)
        last_decision = final_text
        
        with open(session_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"user": user, "final": final_text}, ensure_ascii=False)+"\n")
        print(f"\nMira: {final_text}")


if __name__ == "__main__":
    main()
