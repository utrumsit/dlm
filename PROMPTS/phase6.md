# Task: Phase 6 — Clipboard ask + LLM abstraction (minimal)

## Goal
Replace the current Skim-AppleScript page-text-scraping with a simple clipboard read. Move existing Gemini code into a new `llm/` package so backends can be swapped later. v1 only ships the Gemini backend.

## Read first
- src/dlm/cli.py (the `ask` subcommand and reading_mode_loop's "ask" handler)
- src/dlm/context.py (will be deleted)
- src/dlm/llm.py (will move)
- src/dlm/auth.py (will move)

## Create

### src/dlm/llm/base.py
```python
from abc import ABC, abstractmethod

class LLMBackend(ABC):
    name: str = ""
    @abstractmethod
    def ask(self, context: str, question: str) -> str: ...
    def is_available(self) -> bool: return True
```

### src/dlm/llm/gemini.py
Move the contents of the old `llm.py` here. Wrap in a `GeminiBackend(LLMBackend)` class. Keep the existing `ask_gemini(context, text)` function as a module-level convenience that instantiates and calls the class (so callers don't all break at once).

### src/dlm/llm/__init__.py
```python
from .base import LLMBackend

def get_backend() -> LLMBackend:
    from ..settings import LLM_BACKEND
    from .gemini import GeminiBackend
    if LLM_BACKEND == "gemini":
        return GeminiBackend()
    raise NotImplementedError(f"LLM backend not implemented: {LLM_BACKEND}")
```

### src/dlm/auth/__init__.py (or src/dlm/llm/auth.py)
Move existing `auth.py` contents here as a Gemini-specific OAuth helper.

## Modify

### src/dlm/cli.py
- Remove `from .context import get_current_context` — replace with clipboard read.
- New helper `_read_context() -> tuple[str | None, str]`:
  ```python
  def _read_context():
      import pyperclip
      try:
          text = pyperclip.paste()
          if text and text.strip():
              return text, "clipboard"
          return None, "Clipboard is empty. Select text in your reader and copy it (Ctrl/Cmd+C), then run again."
      except Exception as e:
          return None, f"Clipboard read failed: {e}"
  ```
- Both `ask` command paths (top-level `dlm ask` and the reading-loop `ask`) call `_read_context()` instead of `get_current_context()`.
- Add `--file PATH` and stdin support: `dlm ask "explain this" --file /path/to/snippet.txt` or `cat snippet.txt | dlm ask "explain"`.
- Update help text and print_usage to reflect the new flow.

### src/dlm/settings.py
- Export `LLM_BACKEND` (default "gemini").

### Delete
- `src/dlm/context.py` — gone, no longer needed.

## Constraints
- pyperclip must already be a dep from Phase 3 (verify)
- The old `ask_gemini` function-level API must keep working (backwards compat) — just delegates to the class now
- Don't add other backends in this phase

## Verify
```
# Select some text in any reader, Cmd/Ctrl+C
poetry run dlm ask "what does this mean?"
# expected: prints "Context captured from clipboard..." then Gemini's answer

# From a file
echo "The fundamental theorem of calculus states..." > /tmp/snip.txt
poetry run dlm ask "explain like I'm 5" --file /tmp/snip.txt
```
