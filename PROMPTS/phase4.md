# Task: Phase 4 — Sioyek reader implementation

## PREREQUISITE (paste before sending)
Run these on the target machine and paste the output into this prompt:

```
sqlite3 ~/.local/share/sioyek/shared.db ".schema highlights"
sqlite3 ~/.local/share/sioyek/shared.db ".schema bookmarks"
sqlite3 ~/.local/share/sioyek/shared.db ".schema document_hash"
sqlite3 ~/.local/share/sioyek/shared.db "SELECT * FROM highlights LIMIT 1;"
```

ACTUAL SCHEMA (paste here):
<paste output>

## Goal
Add `SioyekReader(Reader)` for PDFs. Implements `open()` and `extract_annotations()`. NO `current_page_text` — that path is replaced by clipboard `ask` in a later phase.

## Read first
- src/dlm/readers/base.py
- src/dlm/readers/skim.py (pattern to follow)
- src/dlm/readers/__init__.py
- src/dlm/settings.py (for sioyek config)

## Create

### src/dlm/readers/sioyek.py
```python
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Optional
from .base import Reader, Highlight

class SioyekReader(Reader):
    name = "sioyek"
    supports = ["pdf"]

    def __init__(self, binary: str = "sioyek", shared_db: str = "~/.local/share/sioyek/shared.db"):
        self.binary = binary
        self.shared_db = Path(shared_db).expanduser()

    def is_available(self) -> bool:
        return shutil.which(self.binary) is not None

    def open(self, path: Path, page: Optional[int] = None) -> bool:
        cmd = [self.binary, str(path)]
        # Sioyek supports --new-window and --execute-command for page nav
        # If a page is given, append: --new-window --execute-command "goto_page_with_label" --execute-command-data <page>
        # (verify exact flag against `sioyek --help` on your system)
        try:
            subprocess.Popen(cmd)
            if page:
                # goto_page sent to the same instance
                subprocess.run([self.binary, "--execute-command", "goto_page_with_label", "--execute-command-data", str(page)], timeout=5)
            return True
        except Exception as e:
            print(f"Failed to open Sioyek: {e}")
            return False

    def extract_annotations(self, path: Path):
        # Use the ACTUAL schema from the prerequisite above
        if not self.shared_db.exists():
            return None
        try:
            con = sqlite3.connect(f"file:{self.shared_db}?mode=ro", uri=True)
            cur = con.cursor()
            # TEMPLATE — adapt to actual schema:
            # Sioyek stores document_path as relative; you may need to also try abs/basename
            cur.execute("""
                SELECT uuid, desc, type, creation_time
                FROM highlights
                WHERE document_path = ? OR document_path LIKE ?
            """, (str(path), f"%{path.name}"))
            highlights = []
            for row in cur.fetchall():
                uuid, text, color_type, ctime = row
                highlights.append(Highlight(
                    uuid=uuid,
                    text=text or "",
                    color=color_type,
                    modified=None,  # parse ctime if available
                ))
            con.close()
            return highlights
        except Exception as e:
            print(f"Sioyek extraction failed: {e}")
            return None
```

## Modify

### src/dlm/readers/__init__.py
Update `get_reader()`:
```python
def get_reader(file_type: str) -> Reader:
    from .skim import SkimReader
    from .apple_books import AppleBooksReader
    from .sioyek import SioyekReader
    from ..settings import READERS_PDF, SIOYEK_BINARY, SIOYEK_SHARED_DB, SKIM_APP_PATH
    
    ft = file_type.lower()
    if ft == "pdf":
        choice = READERS_PDF or ("skim" if platform.system() == "Darwin" else "sioyek")
        if choice == "skim":
            return SkimReader()
        if choice == "sioyek":
            return SioyekReader(binary=SIOYEK_BINARY, shared_db=SIOYEK_SHARED_DB)
    # epub branch unchanged for now
    ...
```

### src/dlm/settings.py
Export `READERS_PDF`, `SIOYEK_BINARY`, `SIOYEK_SHARED_DB` from the loaded config.

## Intelligent Joplin merge
Create `src/dlm/sync_state.py` with helpers to load/save `~/.local/share/dlm/notes_sync.json` mapping `book_id → set(highlight_uuid)`. When extracting highlights for Joplin export (in cli.py's `export_notes_to_joplin`), filter out already-synced UUIDs before sending. After successful Joplin upload, add the new UUIDs to the set and save.

Update cli.py's `export_notes_to_joplin` accordingly — but ONLY for the new code path (when extract_annotations returns a list of Highlight). The old Mac string-based path can stay as-is for this phase.

## Verify
```
sioyek ~/DigitalLibrary/500_Science/some.pdf  # add a highlight, close
poetry run dlm <that book>  # opens in sioyek
# In reading prompt: type "notes" — should sync only new highlights to Joplin
# Run "notes" again immediately — should report "no new highlights to sync"
```
