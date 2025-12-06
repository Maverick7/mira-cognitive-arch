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

# ========== REACT AGENT LOOP ==========
REACT_PROMPT = """You are Mira, an AI assistant with access to tools. You MUST use tools when you don't know something.

## Context:
{context}

## Available Tools:
- web_search(query): Search the internet for current information, news, sports scores, weather, etc. USE THIS for any real-time data.
- calc(expression): Evaluate a math expression (e.g., "sqrt(25) * 5", "0.15 * 85").

## Scratchpad (Your Previous Reasoning):
{scratchpad}

## User Question: {query}

## CRITICAL INSTRUCTIONS:
1. For questions about current events, scores, news, weather - you MUST use web_search. Do NOT make up answers.
2. For math calculations - use calc to be accurate.
3. You MUST output EXACTLY one of these formats:

**Format A - To use a tool (REQUIRED for real-time info):**
Thought: [Your reasoning]
Action: web_search
Action Input: [search query]

**Format B - Only when you have all info needed:**
Thought: [Your reasoning]
Final Answer: [Your response]

IMPORTANT: Do NOT say "let me search" or "I would need to search" - actually call the Action!
"""

def _react_loop(query: str, context: str, max_iters: int = 3) -> str:
    """ReAct-style agent loop for multi-step reasoning."""
    from ..tools.registry import tool_registry
    from ..models.gemini_client import generate_content
    import traceback
    
    tools = tool_registry()
    scratchpad = ""
    
    try:
        for i in range(max_iters):
            prompt = REACT_PROMPT.format(
                context=context,
                scratchpad=scratchpad if scratchpad else "(No previous reasoning)",
                query=query
            )
            
            print(f"\n[ReAct] Iteration {i+1}/{max_iters}")
            
            try:
                response = generate_content(prompt)
                if not response:
                    print("[ReAct] Empty response from LLM")
                    continue
            except Exception as e:
                print(f"[ReAct] LLM Error: {e}")
                return f"I encountered an error while reasoning: {e}"
            
            print(f"[ReAct] Response length: {len(response)}")
            print(f"[ReAct] Response preview: {response[:400]}")
            
            # Check for Final Answer
            if "Final Answer:" in response:
                final = response.split("Final Answer:")[-1].strip()
                print(f"[ReAct] ✅ Final Answer reached")
                return final
            
            # Parse Action and Action Input - more flexible regex
            action_match = re.search(r"Action:\s*(\w+)", response, re.I)
            # Try multiple patterns for Action Input
            input_match = re.search(r"Action Input:\s*[\"']?(.+?)[\"']?\s*(?:\n|$)", response, re.I | re.S)
            if not input_match:
                input_match = re.search(r"Action Input:\s*(.+)", response, re.I)
            
            print(f"[ReAct] Parsed: action_match={action_match}, input_match={input_match}")
            
            if action_match:
                action = action_match.group(1).strip().lower()
                action_input = input_match.group(1).strip() if input_match else query  # Use query as fallback
                
                print(f"[ReAct] Action: {action}({action_input})")
                
                # Execute the tool
                if action in tools:
                    try:
                        if action == "web_search":
                            observation = tools[action](query=action_input)
                        elif action == "calc":
                            observation = tools[action](expression=action_input)
                        else:
                            observation = str(tools[action](action_input))
                        
                        if not observation:
                            observation = "No results returned."
                    except Exception as e:
                        observation = f"Tool Error: {e}"
                        print(f"[ReAct] Tool Error: {traceback.format_exc()}")
                else:
                    observation = f"Unknown tool: {action}. Available: web_search, calc"
                
                print(f"[ReAct] Observation: {observation[:300]}...")
                
                # Add to scratchpad
                thought = ""
                if "Thought:" in response:
                    thought = response.split("Thought:")[-1].split("Action:")[0].strip()
                scratchpad += f"\nThought: {thought or 'Analyzing...'}"
                scratchpad += f"\nAction: {action}"
                scratchpad += f"\nAction Input: {action_input}"
                scratchpad += f"\nObservation: {observation}\n"
            else:
                # No action found, try to extract any useful content
                print(f"[ReAct] No action found, treating as direct response")
                # Clean up the response - remove Thought: prefix if present
                clean_response = response.replace("Thought:", "").strip()
                return clean_response
        
        # Max iterations reached - synthesize from scratchpad
        print(f"[ReAct] ⚠️ Max iterations reached, synthesizing answer")
        return f"Based on my research:\n{scratchpad}"
        
    except Exception as e:
        print(f"[ReAct] Critical Error: {traceback.format_exc()}")
        return f"I encountered an error: {e}"

# ========== END REACT LOOP ==========

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
from .planner import get_execution_plan

def process_message(user_message: str) -> str:
    ident = load_identity()
    
    # Use dynamic emotional state instead of static mood
    mood = get_mood()  # This applies temporal decay automatically
    emotion_context = get_emotion_context()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n[DEBUG] Time: {now_str}")
    print(f"[DEBUG] Mood: {mood}")
    
    # ========== META-REASONING PLANNER ==========
    plan = get_execution_plan(user_message)
    print(f"[Planner] Plan: {plan}")
    
    # ========== CONDITIONAL CONTEXT FETCHING ==========
    context_parts = [f"[CURRENT TIME]: {now_str}", f"[EMOTIONAL CONTEXT]: {emotion_context}"]
    
    # Fetch Profile only if needed
    if plan.get("needs_profile"):
        from .memory import DATA_DIR
        condensed_mem_path = DATA_DIR / "condensed_memory.json"
        if condensed_mem_path.exists():
            condensed_profile = condensed_mem_path.read_text(encoding="utf-8")
            # Truncate if too long
            if len(condensed_profile) > 2000:
                condensed_profile = condensed_profile[:2000] + "..."
            context_parts.append(f"[USER PROFILE]:\n{condensed_profile}")
    
    # Fetch Recent History only if needed
    if plan.get("needs_history"):
        from .memory import TIMELINE_PATH
        try:
            if TIMELINE_PATH.exists():
                import json as json_mod
                lines = TIMELINE_PATH.read_text(encoding="utf-8").splitlines()[-5:]
                rh = []
                for ln in lines:
                    try:
                        obj = json_mod.loads(ln)
                        rh.append(f"User: {obj.get('user','')}\nMira: {obj.get('final_text','')}")
                    except: pass
                recent_history = "\n\n".join(rh)
                if recent_history:
                    context_parts.append(f"[RECENT CONVERSATION]:\n{recent_history}")
        except: pass
    
    # Fetch RAG only if needed
    memory_blob = ""
    if plan.get("needs_rag"):
        mem_list = retrieve_memories(user_message, k=10)
        memory_blob = "\n".join(mem_list) if mem_list else ""
        if memory_blob:
            context_parts.append(f"[RELEVANT MEMORIES (RAG)]:\n{memory_blob}")
    
    # Assemble context block
    context_block = "\n\n".join(context_parts)
    print(f"[DEBUG] Context loaded: {[p.split(':')[0] for p in context_parts]}")
    
    # ========== ROUTING: REACT vs FAST vs COUNCIL ==========
    
    # If tool is requested, use ReAct loop for multi-step reasoning
    if plan.get("tool"):
        print("[DEBUG] Mode: REACT (Multi-step reasoning with tools)")
        response = _react_loop(user_message, context_block, max_iters=3)
        
        # Update emotional state
        sentiment = analyze_sentiment(user_message)
        engagement = analyze_engagement(user_message)
        update_emotion(sentiment, engagement)
        
        append_timeline({"user": user_message, "mode": "react", "plan": plan, "final_text": response})
        return response
    
    # Council path for complex queries
    if plan.get("needs_council"):
        print("[DEBUG] Mode: SLOW (Council Cycle)")
        # Proceed to Council logic below
    else:
        # FAST PATH: Direct response without tools or Council
        print("[DEBUG] Mode: FAST (Simple query)")
        
        fast_prompt = f"""
You are Mira, a warm and intelligent AI companion.

CONTEXT:
{context_block}

INSTRUCTIONS:
- The user said: "{user_message}"
- Respond directly and naturally.
- Do NOT output JSON.
- Be concise but helpful.
"""
        print(f"[DEBUG] Fast Prompt Context Keys: Tool={plan.get('tool')}")
        response = right_mira(user_message, mood=mood, memory_snippets=memory_blob, system_override=fast_prompt)
        
        # Update emotional state
        sentiment = analyze_sentiment(user_message)
        engagement = analyze_engagement(user_message)
        update_emotion(sentiment, engagement)
        
        append_timeline({"user": user_message, "mode": "fast", "plan": plan, "final_text": response})
        return response
    
    # ========== SLOW PATH: COUNCIL ==========
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
