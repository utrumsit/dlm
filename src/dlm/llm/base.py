"""Abstract base class for LLM backends."""

from abc import ABC, abstractmethod


class LLMBackend(ABC):
    """Interface that all LLM backends must implement."""

    name: str = ""

    @abstractmethod
    def ask(self, context: str, question: str) -> str:
        """Ask a question about the given context text.

        Args:
            context: The text the user is reading (selected text, clipboard, file contents)
            question: The user's question about that text

        Returns:
            The model's answer as a string.
        """
        ...

    def is_available(self) -> bool:
        """Check if the backend is available (credentials configured, etc.)"""
        return True
