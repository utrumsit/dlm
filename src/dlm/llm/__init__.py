"""
LLM package — pluggable backend abstraction for the reading assistant.

v1 ships only the Gemini backend. Other backends can be added later.
"""

from .base import LLMBackend


def get_backend() -> LLMBackend:
    """Get the configured LLM backend instance.

    Reads llm.backend from config (default: "gemini").
    """
    from ..settings import LLM_BACKEND

    if LLM_BACKEND == "gemini":
        from .gemini import GeminiBackend
        return GeminiBackend()

    raise NotImplementedError(f"LLM backend not implemented: {LLM_BACKEND}")


def ask_gemini(context_text: str, question: str) -> str:
    """Convenience wrapper — delegates to GeminiBackend().

    Kept for backwards compatibility with existing callers.
    """
    from .gemini import ask_gemini as _ask_gemini
    return _ask_gemini(context_text, question)


__all__ = ["LLMBackend", "get_backend", "ask_gemini"]
