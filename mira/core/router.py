# -*- coding: utf-8 -*-
import json, re
from .memory import retrieve_memories, append_timeline, load_identity, update_mood
from .emotions import get_mood, update_emotion, get_emotion_context
from .sentiment import analyze_sentiment, analyze_engagement
from ..models.left_reason import left_reason
from ..models.right_mira import right_mira
from ..tools.python_exec import run_py
from ..tools.fs import read_file
from ..env.corpus_callosum import CorpusCallosumEnv

def _parse_left_output(text: str) -> dict:
    """Parse Left hemisphere output. Prefer strict JSON, fallback to heuristics."""
    if not text:
        return {"analysis": "", "plan": [], "final": ""}
    # Try to extract a JSON object from the text
    try:
        start = text.index("{")
        end = text.rfind("}")
        if end > start:
            obj = json.loads(text[start:end+1])
            a = obj.get("analysis", "")
            p = obj.get("plan", [])
            f = obj.get("final", "")
            if not isinstance(p, list):
                p = []
            return {"analysis": str(a), "plan": [str(x) for x in p], "final": str(f)}
    except Exception:
        pass
    # Heuristic: look for lines under 'plan:'
    plan = []
    analysis = ""
    final = text.strip()
    m = re.search(r"analysis\s*:\s*(.*)", text, flags=re.I)
    if m:
        analysis = m.group(1).strip()
    plan_block = re.search(r"plan\s*:\s*(.*)", text, flags=re.I | re.S)
    if plan_block:
        # naive split of bullets
        for ln in plan_block.group(1).splitlines():
            ln = ln.strip(" -\t")
            if not ln:
                continue
            if ln.lower().startswith("final:"):
                break
            plan.append(ln)
    fm = re.search(r"final\s*:\s*(.*)", text, flags=re.I | re.S)
    if fm:
        final = fm.group(1).strip()
    return {"analysis": analysis, "plan": plan, "final": final}

def _execute_plan(plan_items: list[str]) -> dict:
    outputs = []
    for item in plan_items[:6]:  # cap steps
        s = str(item).strip()
        if not s:
            continue
        # allow formats like "run_py: print(2+2)" or "read_file: timeline.jsonl"
        if ":" in s:
            k, v = s.split(":", 1)
            key = k.strip().lower()
            val = v.strip()
            if key == "run_py":
                res = run_py(val)
                outputs.append({"run_py": val, "result": {"ok": res.get("ok"), "stdout": res.get("stdout","")[:400], "stderr": res.get("stderr","")[:200], "timeout": res.get("timeout")}})
            elif key == "read_file":
                res = read_file(val)
                outputs.append({"read_file": val, "result": res})
            else:
                outputs.append({"unknown": s})
        else:
            outputs.append({"text": s})
    return {"steps": outputs}

import datetime

def process_message(user_message: str) -> str:
    ident = load_identity()
    
    # Use dynamic emotional state instead of static mood
    mood = get_mood()  # This applies temporal decay automatically
    emotion_context = get_emotion_context()
    
    # 1. Context Injection (Time & RAG)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Retrieve memories (RAG) - this now uses the vector store if available
    mem_list = retrieve_memories(user_message, k=10)
    memory_blob = "\n".join(mem_list) if mem_list else "No relevant memories found."
    
    print(f"\n[DEBUG] Time: {now_str}")
    print(f"[DEBUG] Mood: {mood}")
    print(f"[DEBUG] Memories Retrieved: {mem_list}")

    # Construct a context block to inject into prompts
    context_block = f"""
[CURRENT TIME]: {now_str}
[USER IDENTITY/MEMORY]:
{memory_blob}
{emotion_context}
"""

    # 2. Fast Mode Heuristic
    # If message is short (< 10 words) and looks like a greeting/simple ack, skip the heavy cycle.
    # We use Right Brain (Mira) directly for this.
    words = user_message.split()
    is_short = len(words) < 10
    is_greeting = any(w.lower() in {"hi", "hello", "hey", "ok", "okay", "thanks", "bye", "goodbye"} for w in words)
    
    if is_short and is_greeting:
        print("[DEBUG] Mode: FAST")
        # Fast Path: Direct call to Right Brain with context
        fast_prompt = f"""
You are Mira, a warm and emotionally intelligent AI companion.
You have access to the following context about the user and yourself:
{context_block}

INSTRUCTIONS:
- The user said: "{user_message}"
- Respond naturally, warmly, and briefly.
- Do NOT output JSON.
- Do NOT say "As an AI".
- Use the context if relevant (e.g. if they say "Hi" and it's late, say "Good evening").

MOOD/PERSONALITY:
- Look at your [EMOTIONAL STATE] above.
- Embody this mood in your response!
- If "playful", be witty and light. If "tired", be soft. If "excited", be energetic!
"""
        response = right_mira(user_message, mood=mood, memory_snippets=memory_blob, system_override=fast_prompt)
        
        # Update emotional state based on user's message
        sentiment = analyze_sentiment(user_message)
        engagement = analyze_engagement(user_message)
        update_emotion(sentiment, engagement)
        
        append_timeline({"user": user_message, "mode": "fast", "final_text": response})
        return response

    print("[DEBUG] Mode: SLOW (Council Cycle)")
    
    # 3. Parallel Council Execution
    # We construct the prompts for all experts simultaneously using the same context.
    # Note: intrinsic gets a slightly different prompt format (Right Brain) than others (Left Brain).
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Define tasks
    # (agent_type, model_func, kwargs)
    # We need to construct the prompts *before* firing threads? 
    # Actually, the prompts depend on the user query and context, which are constant.
    # But `CorpusCallosumEnv` generates the prompt. We can simulate it here.
    
    # Re-use env just for prompt generation if needed, or inline it.
    # Inlining is cleaner for parallel execution since we don't have sequential dependencies anymore.
    
    def _run_expert(agent_type: str, prompt_func) -> tuple:
        prompt = prompt_func(agent_type)
        if agent_type == "intrinsic":
            res = right_mira(user_message, mood=mood, memory_snippets=memory_blob, system_override=prompt)
        else:
            res = left_reason(user_message, memory_snippets=memory_blob, system_override=prompt)
        return agent_type, res

    # Helper to generate prompt (borrowed logic from Env)
    def _get_prompt(agent_type):
        # We can instantiate a temp env to get the prompt to avoid code duplication
        temp_env = CorpusCallosumEnv(user_message, ltm_context=context_block)
        return temp_env.get_expert_prompt(agent_type)

    agent_results = {}
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_run_expert, agent, _get_prompt): agent 
            for agent in ["intrinsic", "extrinsic", "safety", "adversarial"]
        }
        
        for future in as_completed(futures):
            agent, result = future.result()
            agent_results[agent] = result
            
    # --- Tool Execution Interception (Left Brain) ---
    extrinsic_report = agent_results.get("extrinsic", "")
    if "{" in extrinsic_report and '"tool":' in extrinsic_report:
        try:
            # Naive JSON extraction
            start = extrinsic_report.find("{")
            end = extrinsic_report.rfind("}")
            if start != -1 and end != -1:
                call_data = json.loads(extrinsic_report[start:end+1])
                tool_name = call_data.get("tool")
                tool_args = call_data.get("args", {})
                
                from ..tools.registry import tool_registry
                tools = tool_registry()
                
                if tool_name in tools:
                    print(f"[Run Tool] {tool_name} args={tool_args}")
                    tool_func = tools[tool_name]
                    # Execute
                    try:
                        observation = tool_func(**tool_args)
                    except Exception as e:
                        observation = f"Error: {e}"
                        
                    # Re-run Extrinsic with observation
                    # We accept the latency hit for the tool path
                    new_context_block = context_block + f"\n[TOOL OBSERVATION ({tool_name})]:\n{observation}\n"
                    
                    # Update the prompt function to use new context
                    def _get_prompt_with_tool(agent_type):
                        temp_env = CorpusCallosumEnv(user_message, ltm_context=new_context_block)
                        return temp_env.get_expert_prompt(agent_type)
                    
                    # Rerun just Extrinsic
                    print("[Router] Re-running Extrinsic with Tool Data...")
                    _, new_report = _run_expert("extrinsic", _get_prompt_with_tool)
                    agent_results["extrinsic"] = new_report
                    
                    # Also update Council context
                    context_block = new_context_block
                    
        except Exception as e:
            print(f"[Tool Intercept Error] {e}")
    # ------------------------------------------------
    
    # 4. Council Synthesis
    # Now we have all 4 reports. Run the Council.
    
    # We need to manually construct the Council prompt since we bypassed the Env step
    temp_env = CorpusCallosumEnv(user_message, ltm_context=context_block)
    # Inject reports into temp env state to generate Council prompt
    temp_env.state["reports"] = agent_results
    council_prompt = temp_env.get_expert_prompt("council")
    
    final_output = left_reason(user_message, memory_snippets=memory_blob, system_override=council_prompt)
    
    # Log the interaction (Timeline)
    append_timeline({
        "user": user_message, 
        "mode": "slow", 
        "experts": agent_results, 
        "final_text": final_output
    })    
    
    # Update emotional state based on user's message & final output
    sentiment = analyze_sentiment(user_message)
    engagement = analyze_engagement(user_message)
    update_emotion(sentiment, engagement)
    
    return final_output
