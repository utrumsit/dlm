"""
LLM Client for DLM Reading Assistant.

Auth priority:
  1. OAuth credentials (from `dlm-auth`, stored at ~/.config/dlm/oauth_token.json)
  2. API key (GOOGLE_API_KEY in config or environment)

Uses the Google GenAI SDK (v1.0+).
"""

import os
from google import genai
from .settings import GOOGLE_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET


def _get_client():
    """Get an authenticated genai Client (OAuth first, then API key)."""
    # 1. Try OAuth credentials
    try:
        from .auth import get_credentials
        creds = get_credentials(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
        if creds and creds.token:
            return genai.Client(credentials=creds)
    except Exception:
        pass

    # 2. Fall back to API key
    if GOOGLE_API_KEY:
        return genai.Client(api_key=GOOGLE_API_KEY)

    return None


def ask_gemini(context_text, question):
    """
    Send a question about the context to Google Gemini.

    Args:
        context_text (str): The text from the book page.
        question (str): The user's question.

    Returns:
        str: The answer from the model.
    """
    client = _get_client()
    if not client:
        return (
            "Error: No Google credentials found.\n"
            "  Option 1: Run `dlm-auth` to authenticate via OAuth (recommended)\n"
            "  Option 2: Set GOOGLE_API_KEY in ~/.config/dlm/config.py or environment"
        )

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

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        # Fallback to 1.5-flash
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt
            )
            return response.text
        except Exception as e2:
            return f"Error communicating with Gemini: {e2}"
