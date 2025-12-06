# -*- coding: utf-8 -*-
"""Tool Registry for Mira's Left Hemisphere (Extrinsic Agent)."""
import math
import subprocess
import json
from typing import Dict, Any, Callable

# Try to import duckduckgo search, handle failure gracefully
try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    try:
         from duckduckgo_search import DDGS
         HAS_DDGS = True
    except ImportError:
        HAS_DDGS = False

def web_search(query: str, num_results: int = 3) -> str:
    """Search the web for real-time information."""
    if not HAS_DDGS:
        return "[Error] duckduckgo-search not installed. Please install it."
    
    try:
        # Use ddgs context manager
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
            if not results:
                return "No results found."
            
            summary = []
            for r in results:
                summary.append(f"- [{r.get('title')}]({r.get('href')}): {r.get('body')}")
            return "\n".join(summary)
    except Exception as e:
        return f"[Error] Search failed: {e}"

def calculate(expression: str) -> str:
    """Safe evaluation of mathematical expressions."""
    # Use a limited safe scope
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    allowed_names.update({"abs": abs, "round": round, "min": min, "max": max})
    
    try:
        # Evaluate using restricted globals/locals
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"[Error] Math error: {e}"

def analyze_image(image_path: str, prompt: str = "Describe this image in detail.") -> str:
    """Analyze an image using the vision model."""
    from ..models.gemini_client import generate_vision_content
    return generate_vision_content(prompt, image_path)

def tool_registry() -> Dict[str, Callable]:
    """Return a map of tool names to functions."""
    return {
        "web_search": web_search,
        "calc": calculate,
        "analyze_image": analyze_image
    }

def get_tools_definition() -> str:
    """Return a JSON schema-like definition of available tools for the LLM."""
    return """
AVAILABLE TOOLS:
1. web_search(query: str) -> Search the internet for facts, news, or data.
2. calc(expression: str) -> Evaluate a math expression (e.g. "sqrt(25) * 5").
3. analyze_image(image_path: str, prompt: str) -> Look at the user's uploaded image. Use 'prompt' to ask specific questions about it.

To use a tool, you MUST output a JSON block like this:
```json
{
  "tool": "web_search",
  "args": {
    "query": "current weather in Stockholm"
  }
}
```
""" 
