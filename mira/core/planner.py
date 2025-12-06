# -*- coding: utf-8 -*-
"""Meta-Reasoning Planner for M.I.R.A.
Uses a lightweight LLM to analyze the user's query and decide what resources are needed.
"""
import json
import subprocess
from typing import Dict, Any, Optional

# Try Ollama (Phi-3) first, then fallback to Gemini
def _call_ollama(prompt: str, model: str = "phi3:mini") -> Optional[str]:
    """Call Ollama via WSL subprocess."""
    try:
        # WSL command to call ollama
        cmd = ["wsl", "ollama", "run", model, prompt]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"[Planner] Ollama error: {e}")
    return None

def _call_gemini_flash(prompt: str) -> Optional[str]:
    """Call Gemini Flash for planning."""
    try:
        from ..models.gemini_client import generate_content
        return generate_content(prompt, model_name="gemini-2.0-flash")
    except Exception as e:
        print(f"[Planner] Gemini error: {e}")
    return None

PLANNER_PROMPT = """You are an intelligent query analyzer for an AI assistant named Mira. Your job is to analyze the user's message and decide what resources are needed to answer it well.

## Recent Conversation (Last 3 turns):
{recent_context}

## Available Resources:
- **profile**: The user's condensed identity (name, personality, key life facts). Use if the query relates to the user personally.
- **history**: The FULL last 5-10 conversation turns. Use if the query refers to something "we just discussed" or is a follow-up.
- **rag**: A semantic search over the user's entire chat history. Use if the query requires recalling a specific past event or topic from long ago.
- **tool**: An external action. Options: "web_search" (for current events/facts), "calc" (for math), "analyze_image" (if user mentions an image).
- **council**: A multi-agent deliberation system. Use for complex, nuanced, or emotionally sensitive questions.

## User Message:
"{user_message}"

## Instructions:
Think step-by-step about what is needed. Then output ONLY a valid JSON object (no markdown, no extra text):
{{"reasoning": "...", "needs_profile": true/false, "needs_history": true/false, "needs_rag": true/false, "tool": null or "web_search" or "calc" or "analyze_image", "needs_council": true/false}}
"""

DEFAULT_PLAN = {
    "reasoning": "Default fallback plan.",
    "needs_profile": True,
    "needs_history": True,
    "needs_rag": False,
    "tool": None,
    "needs_council": False
}

def _get_recent_context() -> str:
    """Load last 3 timeline entries for Planner context."""
    try:
        from ..config import DATA_DIR
        timeline_path = DATA_DIR / "timeline.jsonl"
        if timeline_path.exists():
            lines = timeline_path.read_text(encoding="utf-8").splitlines()[-3:]
            turns = []
            for ln in lines:
                try:
                    obj = json.loads(ln)
                    turns.append(f"User: {obj.get('user', '')}\nMira: {obj.get('final_text', '')[:150]}...")
                except:
                    pass
            return "\n\n".join(turns) if turns else "No recent conversation."
    except:
        pass
    return "No recent conversation."

def get_execution_plan(user_message: str) -> Dict[str, Any]:
    """Analyze the user's message and return an execution plan."""
    recent_context = _get_recent_context()
    prompt = PLANNER_PROMPT.format(user_message=user_message, recent_context=recent_context)
    
    # Try Phi-3 (local, fast)
    print("[Planner] Trying Phi-3 via Ollama...")
    response = _call_ollama(prompt)
    
    # Fallback to Gemini Flash
    if not response:
        print("[Planner] Fallback to Gemini Flash...")
        response = _call_gemini_flash(prompt)
    
    if not response:
        print("[Planner] All backends failed. Using default plan.")
        return DEFAULT_PLAN
    
    # Parse JSON from response
    try:
        # Try to extract JSON from response (in case of markdown wrapping)
        if "```" in response:
            # Extract content between ```json and ```
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                response = response[start:end]
        
        plan = json.loads(response)
        
        # Validate required fields
        required = ["needs_profile", "needs_history", "needs_rag", "needs_council"]
        for field in required:
            if field not in plan:
                plan[field] = False
        if "tool" not in plan:
            plan["tool"] = None
        if "reasoning" not in plan:
            plan["reasoning"] = "No reasoning provided."
            
        return plan
        
    except json.JSONDecodeError as e:
        print(f"[Planner] JSON parse error: {e}")
        print(f"[Planner] Raw response: {response[:200]}")
        return DEFAULT_PLAN

if __name__ == "__main__":
    # Quick test
    test_queries = [
        "Hi!",
        "What about the AirPods we were discussing?",
        "I'm feeling really anxious about my interview.",
        "What's the latest score of the Man Utd game?",
        "Calculate 123 * 456"
    ]
    for q in test_queries:
        print(f"\nQuery: {q}")
        plan = get_execution_plan(q)
        print(f"Plan: {json.dumps(plan, indent=2)}")
