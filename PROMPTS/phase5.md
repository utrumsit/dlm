# Task: Phase 5 — Foliate reader for Linux EPUBs

## PREREQUISITE (paste before sending)
Open a few EPUBs in Foliate, add some highlights, then:
```
ls ~/.local/share/com.github.johnfactotum.Foliate/library/
cat ~/.local/share/com.github.johnfactotum.Foliate/library/<one-file>.json | python3 -m json.tool | head -100
```

PASTE the directory listing and one example JSON file structure here:
<paste output>

## Goal
Add `FoliateReader(Reader)` implementing `open()` and `extract_annotations()`.

## Read first
- src/dlm/readers/base.py
- src/dlm/readers/apple_books.py (pattern to follow)
- src/dlm/readers/__init__.py
- src/dlm/readers/sioyek.py (intelligent-merge sync_state usage)

## Create

### src/dlm/readers/foliate.py
```python
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from .base import Reader, Highlight

class FoliateReader(Reader):
    name = "foliate"
    supports = ["epub"]

    def __init__(self, binary: str = "foliate", library_dir: str = "~/.local/share/com.github.johnfactotum.Foliate/library"):
        self.binary = binary
        self.library_dir = Path(library_dir).expanduser()

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    def open(self, path: Path, page: Optional[int] = None) -> bool:
        try:
            subprocess.Popen([self.binary, str(path)])
            return True
        except Exception as e:
            print(f"Failed to open Foliate: {e}")
            return False

    def extract_annotations(self, path: Path):
        # Map EPUB path → Foliate's annotation file. Foliate keys by content hash.
        # Use the ACTUAL JSON structure from the prerequisite above.
        # Strategy:
        #   1. compute hash matching Foliate's scheme (likely SHA1 of file content or path)
        #   2. read library_dir/<hash>.json
        #   3. iterate annotations array
        ...
```

## Modify
- `readers/__init__.py`: add EPUB dispatch — `foliate` on Linux, `apple_books` on Mac.
- `settings.py`: export `READERS_EPUB`, `FOLIATE_BINARY`, `FOLIATE_LIBRARY_DIR`.
- `cli.py`'s `export_notes_to_joplin`: extend the new Highlight-list code path to handle EPUB too (already done if you used the same pattern in Phase 4).

## Verify
```
foliate ~/DigitalLibrary/800_Literature/some.epub  # add a highlight, close
poetry run dlm <that book>
# In reading prompt: "notes" — should sync to Joplin
```
