"""
Foliate reader for EPUBs on Linux.

Reads highlights from Foliate's per-book JSON annotation files.
Foliate stores its data at:
  ~/.local/share/com.github.johnfactotum.Foliate/
  ├── library/uri-store.json        (maps identifier → filesystem path)
  └── <identifier>.json             (per-book metadata + annotations)
"""

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

    # Basename fallback (file was moved or opened from a different path)
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
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


class FoliateReader(Reader):
    """Reader for EPUB files using Foliate on Linux."""

    name = "foliate"
    supports = ["epub"]

    def __init__(
        self,
        binary: str = "foliate",
        library_dir: str = "~/.local/share/com.github.johnfactotum.Foliate",
    ):
        self.binary = binary
        # library_dir is the parent directory containing:
        #   library/uri-store.json  (index of known books)
        #   <identifier>.json       (per-book annotations)
        self.library_dir = Path(library_dir).expanduser()

    def is_available(self) -> bool:
        """Check if foliate binary is on PATH."""
        return shutil.which(self.binary) is not None

    def open(self, path: Path, page: Optional[int] = None) -> bool:
        """Launch Foliate with the given EPUB."""
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
        """Read highlights from Foliate's per-book annotation file.

        Uses a two-step lookup:
          1. Read uri-store.json to map filesystem path → EPUB identifier
          2. Read <identifier>.json for annotations
        """
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
            # Book not known to Foliate (never opened) — return empty list
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
                continue  # skip malformed entries

            note = ann.get("note") or None
            modified = _parse_foliate_timestamp(
                ann.get("modified") or ann.get("created") or ""
            )

            highlights.append(
                Highlight(
                    uuid=value,         # epubcfi string (unique within book)
                    text=ann.get("text", "") or "",
                    note=note,
                    page=None,          # epubcfi is not a page number
                    color=ann.get("color"),
                    modified=modified,
                )
            )

        return highlights
