# Task: Phase 1 — Reader abstraction

## Project
DLM at ~/karl-dev/dlm. Python 3.9+, Poetry, src layout. Currently macOS-only: opens PDFs in Skim via AppleScript, EPUBs in Apple Books; extracts annotations from each.

## Goal
Introduce a Reader abstraction so other readers can be plugged in later (Sioyek, Foliate). PURE REFACTOR — Mac behavior must be identical after this change.

## Read first
- src/dlm/opener.py
- src/dlm/extractor.py
- src/dlm/settings.py

## Create

### src/dlm/readers/base.py
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

@dataclass
class Highlight:
    uuid: str
    text: str
    note: Optional[str] = None
    page: Optional[int] = None
    modified: Optional[datetime] = None
    color: Optional[str] = None

class Reader(ABC):
    name: str = ""
    supports: list = []

    @abstractmethod
    def open(self, path: Path, page: Optional[int] = None) -> bool: ...

    def extract_annotations(self, path: Path):
        return None

    def is_available(self) -> bool:
        return True
```

### src/dlm/readers/skim.py
Move the Skim-specific code from opener.py (`_open_pdf_skim`) and extractor.py (`extract_skim_notes`) into a `SkimReader(Reader)` class. `name = "skim"`, `supports = ["pdf"]`. `extract_annotations` returns a list of Highlight objects.

### src/dlm/readers/apple_books.py
Move Apple Books logic from opener.py (`_open_ebook`) and extractor.py (`extract_apple_books_notes`) into `AppleBooksReader(Reader)`. `name = "apple_books"`, `supports = ["epub", "mobi", "azw3", "azw"]`.

### src/dlm/readers/__init__.py
```python
import platform
from .base import Reader, Highlight

def get_reader(file_type: str) -> Reader:
    from .skim import SkimReader
    from .apple_books import AppleBooksReader
    ft = file_type.lower()
    is_mac = platform.system() == "Darwin"
    if ft == "pdf" and is_mac:
        return SkimReader()
    if ft in ("epub", "mobi", "azw3", "azw") and is_mac:
        return AppleBooksReader()
    raise NotImplementedError(f"No reader configured for {file_type} on {platform.system()}")
```

## Modify
- `src/dlm/opener.py`: in `open_file()`, replace the platform/file-type branching with `reader = get_reader(file_type); reader.open(full_path)`. Keep the Linux `xdg-open` fallback inside `get_reader` (catch NotImplementedError → xdg-open). Keep all reading-progress logic intact.
- `src/dlm/extractor.py`: keep the module file, but make `extract_skim_notes` and `extract_apple_books_notes` thin wrappers that delegate to `get_reader(...).extract_annotations(...)` returning the same shape they currently return (string for Skim, dict for Books). DO NOT change cli.py's callers.

## Constraints
- No Linux readers in this phase
- No config changes in this phase
- Do not modify cli.py, context.py, settings.py
- Do not change pyproject.toml

## Verify on Mac
```
poetry install
poetry run dlm --help
poetry run dlm <known book title>   # Skim should open exactly as before
# In dlm reading prompt: type "notes" — Joplin sync should work as before
```
