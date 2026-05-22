# Task: Phase 5 — Foliate reader for Linux EPUBs

## VERIFY-BEFORE-CODING (mandatory)
Before writing any data-access code, run these on the target machine and compare to the structure described below. If anything differs (different keys, different filename scheme, missing files), STOP and update the implementation to match what you observe — do NOT assume the description is correct.

```bash
ls ~/.local/share/com.github.johnfactotum.Foliate/
cat ~/.local/share/com.github.johnfactotum.Foliate/library/uri-store.json | python3 -m json.tool
ls ~/.local/share/com.github.johnfactotum.Foliate/*.json 2>/dev/null | grep -v uri-store
# Pick one of those and dump it:
python3 -c "import json,sys,glob; p=sorted(glob.glob('$HOME/.local/share/com.github.johnfactotum.Foliate/[0-9]*.json'))[0]; print(json.dumps(json.load(open(p)), indent=2)[:1500])"
```

Lesson from Phase 4 (Sioyek): we assumed `document_path TEXT` meant filesystem path. It was actually an MD5 hash of file contents. The feature was non-functional until verified empirically. Don't repeat this mistake. If the description below says "annotation.value is an epubcfi string" but you see something different in the real file, the real file wins.

## Verified Foliate layout (this version: 4.~really3.3.0)

**Index file:** `~/.local/share/com.github.johnfactotum.Foliate/library/uri-store.json`
```json
{
  "uris": [
    ["9780262347945", "~/DigitalLibrary/.../howsmartmachinesthink.epub"]
  ]
}
```
- Entry shape: `[identifier_string, filesystem_path_string]`
- Path is stored as Foliate received it. The example shows a literal `~` — DO NOT assume the path is absolute. Normalize both sides (`Path.expanduser().resolve()`) at lookup time.
- The identifier (here ISBN-13) comes from the EPUB's OPF `dc:identifier`. It might be an ISBN, a UUID, a URL — anything the publisher set.

**Per-book file:** `~/.local/share/com.github.johnfactotum.Foliate/<identifier>.json`
```json
{
  "metadata": {
    "identifier": "9780262347945",
    "title": "How Smart Machines Think",
    "author": "Sean Gerrish",
    ...
  },
  "progress": [21, 551],
  "lastLocation": "epubcfi(/6/12!/4/2,/2,/4/8/1:204)",
  "annotations": [
    {
      "value": "epubcfi(/6/12!/4/2/4/4,/1:0,/1:29)",
      "color": "yellow",
      "text": "I met Sean over a decade ago.",
      "note": "",
      "created": "2026-05-22T22:17:05.000Z",
      "modified": ""
    }
  ]
}
```

**Field → Highlight dataclass mapping:**
| Highlight field | Source |
|---|---|
| `uuid` | `value` (the epubcfi string; unique within the book) |
| `text` | `text` |
| `note` | `note` (if non-empty, else `None`) |
| `page` | `None` (epubcfi is not a page number) |
| `color` | `color` (e.g. `"yellow"`) |
| `modified` | parse `modified` if non-empty, else `created`, else `None` |

## Goal
Add `FoliateReader(Reader)` implementing `open()` and `extract_annotations()`. Wire it into the EPUB branch of `get_reader()`.

## Read first
- src/dlm/readers/base.py
- src/dlm/readers/apple_books.py (pattern to follow — but note its `extract_annotations_by_title` quirk doesn't apply here)
- src/dlm/readers/sioyek.py (pattern for SQLite-style → switch to JSON)
- src/dlm/readers/__init__.py
- src/dlm/sync_state.py (you'll wire this up the same way Sioyek did)
- src/dlm/cli.py (the `export_notes_to_joplin` PDF branch — extend the same approach to EPUB)

## Create

### src/dlm/readers/foliate.py
```python
"""Foliate reader for EPUBs on Linux."""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from .base import Reader, Highlight


def _normalize_path(p) -> str:
    """Normalize a path string for comparison (expanduser + resolve)."""
    try:
        return str(Path(p).expanduser().resolve())
    except (OSError, RuntimeError):
        return str(p)


def _find_identifier_for_path(uri_store: dict, target: Path) -> Optional[str]:
    """Look up the EPUB identifier given its filesystem path.

    Foliate stores the path as-given (may include a literal `~`), so both
    sides are normalized before comparison. Falls back to basename match.
    """
    target_norm = _normalize_path(target)
    target_name = target.name
    for entry in uri_store.get("uris", []):
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        identifier, stored_path = entry[0], entry[1]
        if _normalize_path(stored_path) == target_norm:
            return identifier
    # Basename fallback
    for entry in uri_store.get("uris", []):
        if isinstance(entry, list) and len(entry) >= 2:
            if Path(entry[1]).name == target_name:
                return entry[0]
    return None


def _parse_foliate_timestamp(s: str) -> Optional[datetime]:
    """Parse Foliate's ISO timestamps (e.g. '2026-05-22T22:17:05.000Z')."""
    if not s:
        return None
    try:
        # Python 3.11+ fromisoformat handles 'Z'; older needs replacement
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


class FoliateReader(Reader):
    name = "foliate"
    supports = ["epub"]

    def __init__(
        self,
        binary: str = "foliate",
        library_dir: str = "~/.local/share/com.github.johnfactotum.Foliate",
    ):
        self.binary = binary
        # NOTE: library_dir is the PARENT of the per-book JSON files.
        # The uri-store.json lives at library_dir/library/uri-store.json.
        self.library_dir = Path(library_dir).expanduser()

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    def open(self, path: Path, page: Optional[int] = None) -> bool:
        try:
            subprocess.Popen([self.binary, str(path)])
            return True
        except FileNotFoundError:
            print(f"Failed to open with Foliate: '{self.binary}' not found on PATH")
            return False
        except Exception as e:
            print(f"Failed to open Foliate: {e}")
            return False

    def extract_annotations(self, path: Path) -> Optional[List[Highlight]]:
        """Read highlights from Foliate's per-book annotation file."""
        uri_store_path = self.library_dir / "library" / "uri-store.json"
        if not uri_store_path.exists():
            return []

        try:
            with open(uri_store_path) as f:
                uri_store = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Foliate uri-store read failed: {e}")
            return None

        identifier = _find_identifier_for_path(uri_store, path)
        if identifier is None:
            # Book not known to Foliate (never opened) — return empty, not None
            return []

        annotation_path = self.library_dir / f"{identifier}.json"
        if not annotation_path.exists():
            return []

        try:
            with open(annotation_path) as f:
                book_data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Foliate annotation read failed: {e}")
            return None

        highlights = []
        for ann in book_data.get("annotations", []):
            value = ann.get("value")
            if not value:
                continue   # skip malformed
            note = ann.get("note") or None
            modified = _parse_foliate_timestamp(
                ann.get("modified") or ann.get("created") or ""
            )
            highlights.append(
                Highlight(
                    uuid=value,                          # epubcfi
                    text=ann.get("text", "") or "",
                    note=note,
                    page=None,                           # not stored
                    color=ann.get("color"),
                    modified=modified,
                )
            )
        return highlights
```

## Modify

### src/dlm/readers/__init__.py
Wire Foliate into the EPUB branch:
```python
def get_reader(file_type: str) -> Reader:
    from .skim import SkimReader
    from .apple_books import AppleBooksReader
    from .sioyek import SioyekReader
    from .foliate import FoliateReader
    from ..settings import (
        READERS_PDF,
        READERS_EPUB,
        SIOYEK_BINARY, SIOYEK_SHARED_DB,
        FOLIATE_BINARY, FOLIATE_LIBRARY_DIR,
    )

    ft = file_type.lower()
    system = platform.system()

    if ft == "pdf":
        # ... (Phase 4 logic unchanged)
        ...

    if ft in ("epub", "mobi", "azw3", "azw"):
        choice = (READERS_EPUB or "").lower()
        if not choice:
            choice = "apple_books" if system == "Darwin" else "foliate"

        if choice in ("apple_books", "apple-books"):
            return AppleBooksReader()
        if choice == "foliate":
            return FoliateReader(binary=FOLIATE_BINARY, library_dir=FOLIATE_LIBRARY_DIR)

        # Unknown explicit choice — platform default
        if system == "Darwin":
            return AppleBooksReader()
        return FoliateReader(binary=FOLIATE_BINARY, library_dir=FOLIATE_LIBRARY_DIR)

    raise NotImplementedError(f"No reader configured for {ft} on {system}")
```

### src/dlm/settings.py
**FOLIATE_LIBRARY_DIR** is already declared in `_config_store` from Phase 4 — but its default `"~/.local/share/com.github.johnfactotum.Foliate/library"` is WRONG. The annotations live one level above that. Update both the default and the example config:

- `_config_store` default for `FOLIATE_LIBRARY_DIR`: `"~/.local/share/com.github.johnfactotum.Foliate"`
- `config.toml.example`'s `foliate.library_dir` comment: same

### src/dlm/config_schema.py
Same fix: `FoliateConfig.library_dir` default → `"~/.local/share/com.github.johnfactotum.Foliate"`.

### src/dlm/cli.py
The `export_notes_to_joplin` function already has the Highlight-list code path (from Phase 4) and the legacy AppleBooks dict path. Extend the EPUB branch so:
- On Linux (Foliate) → call `get_highlights_from_reader("epub", full_path)`. If it returns a `list[Highlight]`, run the intelligent-merge code (same as Sioyek's). If it returns `None`, fall through to the legacy AppleBooks path.
- On Mac (Apple Books) → unchanged.

Concretely: refactor so the Highlight-list path is shared between PDF and EPUB. One helper function `_sync_highlights_to_joplin(entry, highlights, ...)` called from either branch.

## Constraints
- Do not change pyproject.toml (no new deps — stdlib `json` is enough)
- Do not touch the Sioyek or Skim code
- Do not delete `extractor.py` (its `extract_apple_books_notes` wrapper still serves Mac)
- The Highlight UUID is the epubcfi string — DO NOT strip or hash it; pass it through verbatim

## Verify
```bash
# Add at least one highlight in Foliate to a known EPUB, then close it.
foliate ~/DigitalLibrary/000_Computer_Science/006_Artificial_Intelligence/howsmartmachinesthink.epub

# Confirm Foliate's file appeared
ls ~/.local/share/com.github.johnfactotum.Foliate/*.json

# Run dlm and trigger notes export
poetry run dlm "How Smart Machines Think"
# In the reading prompt:
(dlm) > notes        # syncs new highlight(s) to Joplin
(dlm) > notes        # reports "No new highlights to sync"

# Verify sync state
cat ~/.local/share/dlm/notes_sync.json
```
