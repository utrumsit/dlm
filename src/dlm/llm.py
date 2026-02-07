"""
LLM Client for DLM Reading Assistant.
Uses the new Google GenAI SDK (v1.0+).
"""

import os
from google import genai
from .settings import LIBRARY_ROOT

# Try to load API key from config if not in env
try:
    from config import GOOGLE_API_KEY
except ImportError:
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")


def ask_gemini(context_text, question):
    """
    Send a question about the context to Google Gemini.
    
    Args:
        context_text (str): The text from the book page.
        question (str): The user's question.
        
    Returns:
        str: The answer from the model.
    """
    if not GOOGLE_API_KEY:
        return "Error: GOOGLE_API_KEY not found. Please set it in your environment or config.py."

    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        
        prompt = f"""
You are an expert reading assistant and tutor. 
The user is reading a book and has a question about the current page.

CONTEXT FROM PAGE:
\"\"\"
{context_text}
\"\"\"

USER QUESTION:
{question}

Please answer the question clearly and concisely based on the context provided. 
If the context contains complex math or technical terms, explain them simply if asked.
"""
        # Using gemini-2.0-flash if available, or 1.5-flash
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt
        )
        return response.text
    except Exception as e:
        # Fallback to 1.5-flash if 2.0 isn't available yet
        try:
            client = genai.Client(api_key=GOOGLE_API_KEY)
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=prompt
            )
            return response.text
        except Exception as e2:
            return f"Error communicating with Gemini: {e2}"
