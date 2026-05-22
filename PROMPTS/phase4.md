# Task: Phase 4 — Sioyek reader implementation

## Goal
Add `SioyekReader(Reader)` for PDFs. Implements `open()` and `extract_annotations()`. NO `current_page_text` — that path is replaced by clipboard `ask` in a later phase.

## Actual Sioyek SQLite schema (verified on target machine)

The database lives at `~/.local/share/sioyek/shared.db`. Relevant tables:

```sql
CREATE TABLE highlights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_path TEXT,
    desc TEXT,             -- the highlighted text content
    type CHAR,             -- single-char category/colour ('a', 'b', etc.)
    begin_x REAL,
    begin_y REAL,
    end_x REAL,
    end_y REAL
);

CREATE TABLE bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_path TEXT,
    desc TEXT,
    offset_y REAL
);
```

Notes:
- `id` is the stable highlight identifier (integer, auto-increment). Convert to `str(id)` to populate `Highlight.uuid`.
- `desc` is the actual highlighted text → maps to `Highlight.text`.
- `type` is a single character indicating colour/category → maps to `Highlight.color`.
- There is **no timestamp column** → `Highlight.modified` stays `None`.
- There is **no page-number column** — page would have to be derived from `begin_y` by loading the PDF, which is too complex for v1. Leave `Highlight.page = None`.
- `document_path` is stored as Sioyek saw it (typically absolute). Query with the absolute path of the file; provide a basename `LIKE` fallback in case the file was moved.

## Read first
- src/dlm/readers/base.py
- src/dlm/readers/skim.py (pattern to follow)
- src/dlm/readers/__init__.py
- src/dlm/settings.py (existing config exports)
- src/dlm/config_schema.py (sioyek section: `sioyek.binary`, `sioyek.shared_db`)

## Create

### src/dlm/readers/sioyek.py
```python
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Optional, List

from .base import Reader, Highlight


class SioyekReader(Reader):
    name = "sioyek"
    supports = ["pdf"]

    def __init__(
        self,
        binary: str = "sioyek",
        shared_db: str = "~/.local/share/sioyek/shared.db",
    ):
        self.binary = binary
        self.shared_db = Path(shared_db).expanduser()

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    def open(self, path: Path, page: Optional[int] = None) -> bool:
        """Launch Sioyek with the given PDF.

        Sioyek supports `--new-instance`, `--reuse-window`, and
        `--execute-command goto_page_with_label <n>` for navigation.
        Verify exact flags against `sioyek --help` on your system.
        """
        try:
            subprocess.Popen([self.binary, str(path)])
            if page:
                # Best-effort: ask the already-running instance to jump.
                subprocess.run(
                    [
                        self.binary,
                        "--execute-command",
                        "goto_page_with_label",
                        "--execute-command-data",
                        str(page),
                    ],
                    timeout=5,
                )
            return True
        except Exception as e:
            print(f"Failed to open Sioyek: {e}")
            return False

    def extract_annotations(self, path: Path) -> Optional[List[Highlight]]:
        """Read highlights from Sioyek's shared.db for the given file."""
        if not self.shared_db.exists():
            return None

        try:
            con = sqlite3.connect(f"file:{self.shared_db}?mode=ro", uri=True)
            cur = con.cursor()
            # Try absolute path first; fall back to basename LIKE for moved files
            cur.execute(
                """
                SELECT id, desc, type
                FROM highlights
                WHERE document_path = ?
                   OR document_path LIKE ?
                """,
                (str(path), f"%/{path.name}"),
            )
            highlights = []
            for row in cur.fetchall():
                hl_id, desc, hl_type = row
                highlights.append(
                    Highlight(
                        uuid=str(hl_id),       # convert int -> str for sync_state.json keys
                        text=desc or "",
                        color=hl_type,
                        page=None,             # not stored; would need PDF inspection
                        modified=None,         # no timestamp column
                    )
                )
            con.close()
            return highlights
        except Exception as e:
            print(f"Sioyek annotation extraction failed: {e}")
            return None
```

## Modify

### src/dlm/readers/__init__.py
Update `get_reader()` to dispatch to Sioyek on Linux (or when configured):
```python
def get_reader(file_type: str) -> Reader:
    from .skim import SkimReader
    from .apple_books import AppleBooksReader
    from .sioyek import SioyekReader
    from ..settings import (
        SIOYEK_BINARY,
        SIOYEK_SHARED_DB,
        READERS_PDF,
    )

    ft = file_type.lower()
    system = platform.system()

    if ft == "pdf":
        choice = (READERS_PDF or "").lower()
        if not choice:
            choice = "skim" if system == "Darwin" else "sioyek"
        if choice == "skim":
            return SkimReader()
        if choice == "sioyek":
            return SioyekReader(binary=SIOYEK_BINARY, shared_db=SIOYEK_SHARED_DB)

    # EPUB branch unchanged for now (handled in Phase 5)
    if ft in ("epub", "mobi", "azw3", "azw") and system == "Darwin":
        return AppleBooksReader()

    raise NotImplementedError(f"No reader configured for {ft} on {system}")
```

### src/dlm/settings.py
Export three new module-level names via the existing `_config_store` + `__getattr__` pattern:
- `READERS_PDF` (from `readers.pdf` in config.toml, default `""`)
- `SIOYEK_BINARY` (from `sioyek.binary`, default `"sioyek"`)
- `SIOYEK_SHARED_DB` (from `sioyek.shared_db`, default `"~/.local/share/sioyek/shared.db"`)

Add corresponding `_apply_toml_to_store()` lines for the new keys.

## Intelligent Joplin sync

Create `src/dlm/sync_state.py`:
```python
"""Track which Sioyek highlight IDs have already been pushed to Joplin."""
import json
from pathlib import Path
from typing import Set

from .settings import DLM_DATA_DIR

SYNC_STATE_PATH = DLM_DATA_DIR / "notes_sync.json"


def load_synced_ids(book_id: str) -> Set[str]:
    if not SYNC_STATE_PATH.exists():
        return set()
    try:
        with open(SYNC_STATE_PATH) as f:
            data = json.load(f)
        return set(data.get(book_id, []))
    except Exception:
        return set()


def add_synced_ids(book_id: str, new_ids):
    data = {}
    if SYNC_STATE_PATH.exists():
        try:
            with open(SYNC_STATE_PATH) as f:
                data = json.load(f)
        except Exception:
            data = {}
    existing = set(data.get(book_id, []))
    existing.update(new_ids)
    data[book_id] = sorted(existing)
    SYNC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SYNC_STATE_PATH, "w") as f:
        json.dump(data, f, indent=2)
```

Update `cli.py`'s `export_notes_to_joplin`:
- When `entry["file_type"] == "pdf"`, try the new code path:
  ```python
  from .readers import get_reader
  from .sync_state import load_synced_ids, add_synced_ids

  reader = get_reader("pdf")
  highlights = reader.extract_annotations(full_path)
  if isinstance(highlights, list):   # new Highlight-list path
      book_id = entry.get("id")
      already = load_synced_ids(book_id)
      new = [h for h in highlights if h.uuid not in already]
      if not new:
          print("No new highlights to sync.")
          return
      # format new highlights into markdown, append to Joplin note, then:
      add_synced_ids(book_id, [h.uuid for h in new])
  else:
      # Legacy string-based path (Skim on Mac) — unchanged
      ...
  ```
- For Skim on macOS, `extract_annotations` still returns a string → preserve the old behaviour for that case.
- For Sioyek on Linux, `extract_annotations` returns a list of `Highlight` → use the new intelligent-merge path.

## Constraints
- Do NOT modify the Skim or Apple Books reader code (Phase 1 work)
- Do NOT delete `src/dlm/context.py` (Phase 6 will handle that)
- Highlight UUIDs are strings, even though Sioyek IDs are integers — cast `str(id)`
- Don't add Foliate or any EPUB-side changes (that's Phase 5)
- Don't add new pyproject.toml deps (sqlite3 is stdlib)

## Verify
```bash
# Prerequisite: add a highlight in Sioyek to a PDF in your library
sioyek ~/DigitalLibrary/000_Computer_Science/some.pdf
# (highlight some text, save with Ctrl+S, then close)

# Check the DB has the entry
sqlite3 ~/.local/share/sioyek/shared.db \
    "SELECT id, desc, type FROM highlights ORDER BY id DESC LIMIT 5;"

# Run dlm and trigger the notes export
poetry run dlm <that book title>
# In the reading prompt:
(dlm) > notes        # should sync the new highlight to Joplin
(dlm) > notes        # should report "No new highlights to sync"

# Inspect the sync-state file
cat ~/.local/share/dlm/notes_sync.json
```
