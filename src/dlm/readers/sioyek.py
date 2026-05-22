"""
Sioyek reader implementation for PDFs on Linux/macOS.

Reads highlights from Sioyek's SQLite database (shared.db) and
launches the sioyek binary for opening PDFs.
"""

import hashlib
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Optional, List

from .base import Reader, Highlight


def _compute_sioyek_doc_hash(path: Path) -> Optional[str]:
    """Compute the MD5 hash Sioyek uses to identify a PDF.

    Sioyek stores `document_path` in shared.db as the MD5 of the file
    contents, not the filesystem path. Annotations follow content, not
    location — moving or renaming a PDF preserves its highlights.
    """
    try:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


class SioyekReader(Reader):
    """Reader for PDF files using Sioyek on Linux and macOS."""

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
        """Check if sioyek binary is on PATH."""
        return shutil.which(self.binary) is not None

    def open(self, path: Path, page: Optional[int] = None) -> bool:
        """Launch Sioyek with the given PDF.

        Sioyek can be started with `--new-instance` or `--reuse-window`.
        Page navigation uses --execute-command goto_page_with_label.
        """
        try:
            cmd = [self.binary, str(path)]
            subprocess.Popen(cmd)

            if page is not None:
                # Best-effort: try to navigate to the page in the running instance.
                # This is a separate subprocess call since sioyek doesn't always
                # support remote commands for page jumping.
                try:
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
                except Exception:
                    # Page navigation is best-effort; don't fail the open
                    pass

            return True
        except FileNotFoundError:
            print(f"Failed to open with Sioyek: '{self.binary}' not found on PATH")
            return False
        except Exception as e:
            print(f"Failed to open Sioyek: {e}")
            return False

    def extract_annotations(self, path: Path) -> Optional[List[Highlight]]:
        """Read highlights from Sioyek's shared.db for the given file.

        Sioyek schema:
            highlights (id, document_path, desc, type, begin_x, begin_y, end_x, end_y)
            bookmarks  (id, document_path, desc, offset_y)

        Note: `document_path` is the MD5 hash of the file content, not a
        filesystem path. We compute the hash and query by it.

        Returns a list of Highlight objects, or None if DB / file not found.
        """
        if not self.shared_db.exists():
            return []

        doc_hash = _compute_sioyek_doc_hash(path)
        if doc_hash is None:
            return None

        try:
            # Open in read-only mode to avoid lock contention with a running sioyek
            con = sqlite3.connect(f"file:{self.shared_db}?mode=ro", uri=True)
            cur = con.cursor()

            cur.execute(
                "SELECT id, desc, type FROM highlights WHERE document_path = ?",
                (doc_hash,),
            )

            highlights = []
            for row in cur.fetchall():
                hl_id, desc, hl_type = row
                highlights.append(
                    Highlight(
                        uuid=str(hl_id),  # int → str for sync_state.json keys
                        text=desc or "",
                        color=hl_type,     # single-char category/colour ('a', 'b', …)
                        page=None,         # not stored; would need PDF inspection
                        modified=None,     # no timestamp column
                    )
                )

            con.close()
            return highlights

        except sqlite3.OperationalError as e:
            print(f"Sioyek annotation extraction failed (DB may be locked): {e}")
            return None
        except Exception as e:
            print(f"Sioyek annotation extraction failed: {e}")
            return None
