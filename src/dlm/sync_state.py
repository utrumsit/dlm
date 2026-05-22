"""
Track which highlight IDs have already been pushed to Joplin.

Uses a JSON file at DLM_DATA_DIR/notes_sync.json keyed by book ID,
with a sorted list of highlight UUID strings per book.
"""

import json
from pathlib import Path
from typing import Set, List

from .settings import DLM_DATA_DIR

SYNC_STATE_PATH = DLM_DATA_DIR / "notes_sync.json"


def load_synced_ids(book_id: str) -> Set[str]:
    """Load the set of highlight UUIDs already synced for a book."""
    if not SYNC_STATE_PATH.exists():
        return set()
    try:
        with open(SYNC_STATE_PATH) as f:
            data = json.load(f)
        return set(data.get(book_id, []))
    except (json.JSONDecodeError, OSError):
        return set()


def add_synced_ids(book_id: str, new_ids: List[str]):
    """Record that the given highlight UUIDs have been synced for a book."""
    data = {}
    if SYNC_STATE_PATH.exists():
        try:
            with open(SYNC_STATE_PATH) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = {}

    existing = set(data.get(book_id, []))
    existing.update(new_ids)
    data[book_id] = sorted(existing)

    SYNC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SYNC_STATE_PATH, "w") as f:
        json.dump(data, f, indent=2)
