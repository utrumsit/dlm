"""
Unified file opener for all entry points.
Opens PDFs in Skim, EPUBs in Apple Books, everything else with system default.
Updates reading progress on every open.
"""

import platform
import subprocess
from datetime import datetime
from pathlib import Path

from .data import load_progress, save_progress
from .readers import get_reader
from .settings import LIBRARY_ROOT


def open_file(entry, set_page=None):
    """Open a file with the best available reader.

    Args:
        entry: catalog entry dict with file_path, id, title, file_type
        set_page: optional page number to save immediately

    Returns:
        True if file was opened successfully
    """
    file_path = entry["file_path"]
    full_path = LIBRARY_ROOT / file_path
    file_id = entry.get("id")
    file_type = entry.get("file_type", "").lower()

    if not full_path.exists():
        print(f"Error: File not found at {full_path}")
        return False

    # Show reading progress if we have it
    progress_data = load_progress()
    if file_id in progress_data and "page" in progress_data[file_id]:
        last_page = int(progress_data[file_id]["page"])
        print(f"Last read at page {last_page}")

    system = platform.system()

    try:
        # Try the appropriate reader for this file type
        reader = get_reader(file_type)
        reader.open(full_path)
        print(f"Opening: {entry.get('title', full_path.name)}")
    except NotImplementedError:
        # Fall back to system default opener
        if system == "Darwin":
            subprocess.run(["open", str(full_path)])
        elif system == "Windows":
            subprocess.run(["start", str(full_path)], shell=True)
        else:
            subprocess.run(["xdg-open", str(full_path)])
        print(f"Opening: {entry.get('title', full_path.name)}")
    except Exception as e:
        print(f"Error opening file: {e}")
        return False

    # Update reading progress
    _update_progress(file_id, set_page)

    return True


def _update_progress(file_id, set_page=None):
    """Update reading progress timestamp and optional page number."""
    if not file_id:
        return

    progress_data = load_progress()
    if file_id not in progress_data:
        progress_data[file_id] = {}

    progress_data[file_id]["last_opened"] = datetime.now().strftime("%Y-%m-%d")

    if set_page is not None and isinstance(set_page, int):
        progress_data[file_id]["page"] = set_page

    save_progress(progress_data)