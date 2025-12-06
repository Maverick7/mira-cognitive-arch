# -*- coding: utf-8 -*-
import google.generativeai as genai
from ..config import GEMINI_API_KEY, GEMINI_MODEL

_configured = False

def configure_gemini():
    global _configured
    if not _configured:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        genai.configure(api_key=GEMINI_API_KEY)
        _configured = True

def generate_content(prompt: str, model_name: str = None) -> str:
    """
    Generates content using the Gemini API.
    """
    configure_gemini()
    model_name = model_name or GEMINI_MODEL
    model = genai.GenerativeModel(model_name)
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"[Gemini Error: {str(e)}]"

def generate_vision_content(prompt: str, image_path: str, model_name: str = None) -> str:
    """
    Generates content using Gemini with an image input.
    """
    configure_gemini()
    model_name = model_name or GEMINI_MODEL
    model = genai.GenerativeModel(model_name)
    
    import PIL.Image
    try:
        img = PIL.Image.open(image_path)
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        return f"[Gemini Vision Error: {str(e)}]"
