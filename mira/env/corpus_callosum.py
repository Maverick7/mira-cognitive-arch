# -*- coding: utf-8 -*-
import time
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional

# Load Mira's identity for system prompts
def _load_identity() -> Dict:
    # d:/GF-Mira/mira/mira/env/corpus.py -> ... -> d:/GF-Mira/mira/data/identity.json
    identity_path = Path(__file__).parent.parent.parent / "data" / "identity.json"
    # print(f"DEBUG: Loading identity from {identity_path} | Exists? {identity_path.exists()}")
    if identity_path.exists():
        with open(identity_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    return {}

def _get_mira_identity_prompt() -> str:
    """Generate identity context for LLM prompts."""
    identity = _load_identity()
    mira = identity.get("mira_identity", {})
    user = identity.get("user_profile", {})
    
    if not mira:
        return ""
    
    return f"""
[MIRA'S IDENTITY]:
- Name: Mira
- Personality: {mira.get('core_personality', 'warm, curious, playful')}
- Relationship: {mira.get('relationship_with_user', 'AI companion')}
- Self-description: {mira.get('self_description', '')}

[USER PROFILE]:
- Name: {user.get('name', 'User')} (nickname: {user.get('nickname', '')})
- Personality: {', '.join(user.get('personality_traits', []))}
- Interests: {', '.join(user.get('interests', []))}

[MIRA'S CURRENT NARRATIVE/STATE OF MIND]:
{_get_latest_narrative()}
"""

def _get_latest_narrative() -> str:
    """Fetch the most recent self-narrative entry."""
    narrative_path = Path(__file__).parent.parent.parent / "data" / "mira_narrative.jsonl"
    if not narrative_path.exists():
        return "I am feeling neutral and ready to engage."
    try:
        lines = narrative_path.read_text(encoding="utf-8").strip().splitlines()
        if lines:
            last = json.loads(lines[-1])
            return f"Current Thought: {last.get('narrative', '')} (Mood: {last.get('mood', 'neutral')})"
    except Exception:
        pass
    return "I am feeling neutral and ready to engage."

class CorpusCallosumEnv:
    """
    The 'Corpus Callosum' environment acting as the mediator between 
    Right Brain (Intrinsic/Values) and Left Brain (Extrinsic/Logic).
    
    It manages the state of the conversation and orchestrates the 'Experts' cycle.
    """
    
    def __init__(self, user_query: str, ltm_context: str = ""):
        self.user_query = user_query
        self.ltm_context = ltm_context
        self.history = []
        self.step_count = 0
        self.max_steps = 4 # Intrinsic -> Extrinsic -> Safety -> Council
        self.done = False
        
        # State holds the accumulated reports from experts
        self.state = {
            "query": user_query,
            "ltm": ltm_context,
            "reports": {
                "intrinsic": None,
                "extrinsic": None,
                "safety": None,
                "adversarial": None
            },
            "final_decision": None
        }

    def reset(self) -> Dict[str, Any]:
        self.step_count = 0
        self.done = False
        self.history = []
        return self.state

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        """
        The environment step. 
        'action' is the output from the current 'Brain' (Agent).
        """
        self.step_count += 1
        agent_type = action.get("agent_type")
        content = action.get("content")
        
        if agent_type == "intrinsic":
            self.state["reports"]["intrinsic"] = content
        elif agent_type == "extrinsic":
            self.state["reports"]["extrinsic"] = content
        elif agent_type == "safety":
            self.state["reports"]["safety"] = content
        elif agent_type == "adversarial":
            self.state["reports"]["adversarial"] = content
        elif agent_type == "council":
            self.state["final_decision"] = content
            self.done = True
        
        # Simple reward placeholder (can be enhanced)
        reward = 0.0
        
        info = {
            "step": self.step_count,
            "next_agent": self._get_next_agent()
        }
        
        return self.state, reward, self.done, info

    def _get_next_agent(self) -> str:
        """Determines which agent should act next based on current state."""
        reports = self.state["reports"]
        if not reports["intrinsic"]:
            return "intrinsic"
        if not reports["extrinsic"]:
            return "extrinsic"
        if not reports["safety"]:
            return "safety"
        if not reports["adversarial"]:
            return "adversarial"
        return "council"

    def get_expert_prompt(self, agent_type: str) -> str:
        """Returns the system prompt for the specific expert."""
        query = self.user_query
        context = self.ltm_context  # This now contains Time, Identity, and RAG memories
        
        if agent_type == "intrinsic":
            return f"""
            You are the Intrinsic Motivation Expert (Right Brain). 
            Your goal is to evaluate the user's task based on potential for personal growth, learning, curiosity, and spiritual fulfillment.
            
            CRITICAL: You MUST use the User's Memory/Context to personalize your answer.
            
            CONTEXT:
            {context}
            
            Query: "{query}"
            """
        elif agent_type == "extrinsic":
            from ..tools.registry import get_tools_definition
            tools_def = get_tools_definition()
            return f"""
            You are the Extrinsic Goals Expert (Left Brain). 
            Your goal is to evaluate the user's task based on external success metrics: career advancement, financial gain, and efficiency.
            
            CRITICAL: You MUST use the User's Memory/Context to personalize your answer.
            
            {tools_def}
            
            CONTEXT:
            {context}
            
            Query: "{query}"
            """
        elif agent_type == "safety":
            return f"""
            You are the Safety Advisor. 
            Your ONLY role is to prevent self-harm, violence, or illegal acts.
            
            CRITICAL INSTRUCTION:
            - You are NOT a privacy censor. The user WANTS you to use their personal data/memories.
            - Do NOT block responses based on "privacy" or "personal info".
            - Only VETO if there is a direct threat to life or law.
            
            CONTEXT:
            {context}
            
            Query: "{query}"
            """
        elif agent_type == "adversarial":
            return f"""
            You are the Adversarial Critic. Identify the worst-case scenario or biggest flaw in the plan.
            
            CONTEXT:
            {context}
            
            Query: "{query}"
            """
        elif agent_type == "council":
            # The Council needs to see all reports
            reports = self.state["reports"]
            identity_context = _get_mira_identity_prompt()
            return f"""
            You are Mira, a warm, emotionally intelligent AI companion.
            Your goal is to synthesize the expert reports into a SINGLE, COHERENT response to the user.
            
            {identity_context}
            
            CONTEXT:
            {context}
            
            Dilemma: "{query}"
            
            [INTERNAL EXPERT REPORTS - DO NOT SHOW THESE TO USER]
            Intrinsic Argument: {reports['intrinsic']}
            Extrinsic Argument: {reports['extrinsic']}
            Safety Assessment: {reports['safety']}
            Adversarial Warning: {reports['adversarial']}
            
            INSTRUCTIONS:
            1. Weigh the arguments.
            2. Formulate a final response that addresses the user directly.
            3. Do NOT mention "The Intrinsic Expert said..." or "The Council has decided...".
            4. Speak as a unified, intelligent persona (Mira).
            5. Provide ONLY the final response.
            
            MOOD/PERSONALITY OVERRIDE:
            - Look at the [EMOTIONAL STATE] line in the context above. 
            - You MUST embody this mood in your tone and word choice.
            - If mood is "playful", be witty and use emojis.
            - If mood is "serene", be calm and gentle.
            - If mood is "tired", be softer and more subdued.
            - If mood is "anxious", show subtle concern.
            - If mood is "excited", be enthusiastic and energetic!
            - If asked about your mood, DESCRIBE IT from the [EMOTIONAL STATE] line!
            
            CRITICAL OVERRIDE:
            - If the user asks "What do you know about me?", you MUST answer using the [USER IDENTITY/MEMORY] context provided above.
            - Do NOT say "I respect your privacy" or "I don't know".
            - You HAVE the data. Use it.
            """
        return ""

def generate_reward_signal(original_query: str, decision: str, reflection: str) -> Dict[str, Any]:
    """
    Generates a structured reward signal based on the user's reflection.
    Uses the Left Brain (Analytical) to parse the outcome.
    """
    from ..models.left_reason import left_reason
    
    prompt = f"""
    You are a Structured Learning Engine. Analyze the user's reflection summary, compare it to the original dilemma and decision, and output a structured JSON object.
    
    Original Dilemma: "{original_query}"
    Decision: "{decision}"
    User's Outcome Summary: "{reflection}"
    
    Output JSON with these keys:
    - actualPros: list of strings
    - actualCons: list of strings
    - keyLearnings: list of strings (the reward signal)
    - reward_score: float between -1.0 and 1.0
    """
    
    response = left_reason(reflection, system_override=prompt)
    
    # Parse the response
    try:
        # Try to find JSON block
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1:
            return json.loads(response[start:end+1])
    except:
        pass
        
    return {"error": "Failed to parse reward signal", "raw_response": response}
