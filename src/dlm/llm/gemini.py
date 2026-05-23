"""
Gemini LLM backend.

Auth priority:
  1. OAuth credentials (from `dlm-auth`, stored at ~/.config/dlm/oauth_token.json)
  2. API key (GOOGLE_API_KEY in config or environment)

Uses the Google GenAI SDK (v1.0+).
"""

from google import genai

from ..settings import GOOGLE_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from .base import LLMBackend


def _get_client():
    """Get an authenticated genai Client (OAuth first, then API key)."""
    # 1. Try OAuth credentials
    try:
        from ..auth import get_credentials
        creds = get_credentials(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
        if creds and creds.token:
            return genai.Client(credentials=creds)
    except Exception:
        pass

    # 2. Fall back to API key
    if GOOGLE_API_KEY:
        return genai.Client(api_key=GOOGLE_API_KEY)

    return None


class GeminiBackend(LLMBackend):
    """Google Gemini backend."""

    name = "gemini"

    def is_available(self) -> bool:
        """Check if Gemini credentials are configured."""
        if GOOGLE_API_KEY:
            return True
        # Check for OAuth tokens
        from ..auth import get_credentials
        creds = get_credentials(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
        if creds and creds.token:
            return True
        return False

    def ask(self, context: str, question: str) -> str:
        """Send a question about the context to Google Gemini."""
        client = _get_client()
        if not client:
            return (
                "Error: No Google credentials found.\n"
                "  Option 1: Run `dlm-auth` to authenticate via OAuth (recommended)\n"
                "  Option 2: Set GOOGLE_API_KEY in config.toml or environment"
            )

        prompt = f"""You are an expert reading assistant and tutor.
The user is reading a book and has a question about the selected text.

CONTEXT:
\"\"\"
{context}
\"\"\"

USER QUESTION:
{question}

Please answer the question clearly and concisely based on the context provided.
If the context contains complex math or technical terms, explain them simply if asked.
"""

        # Try the latest model first, fall back to a lighter one
        for model in ("gemini-2.5-flash", "gemini-2.0-flash-lite"):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return response.text
            except Exception:
                continue

        return "Error: All Gemini models failed. Check your network connection."


# ── Backwards-compatible module-level function ────────────────────────────

def ask_gemini(context_text: str, question: str) -> str:
    """Convenience wrapper — delegates to GeminiBackend().

    Kept for backwards compatibility with existing callers.
    """
    return GeminiBackend().ask(context_text, question)
