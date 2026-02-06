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
        if system == "Darwin":
            _open_macos(full_path, file_type, entry)
        elif system == "Windows":
            subprocess.run(["start", str(full_path)], shell=True)
        else:
            subprocess.run(["xdg-open", str(full_path)])

        print(f"Opening: {entry.get('title', full_path.name)}")

        # Update reading progress
        _update_progress(file_id, set_page)

        return True
    except Exception as e:
        print(f"Error opening file: {e}")
        return False


def _open_macos(full_path, file_type, entry):
    """macOS-specific file opening logic."""
    if file_type == "pdf":
        _open_pdf_skim(full_path)
    elif file_type in ["epub", "mobi", "azw3", "azw"]:
        _open_ebook(full_path, entry)
    else:
        subprocess.run(["open", str(full_path)])


def _open_pdf_skim(full_path):
    """Open PDF with Skim via AppleScript (falls back to system default)."""
    skim_path = Path("/Applications/Skim.app/Contents/MacOS/Skim")
    if skim_path.exists():
        subprocess.Popen(
            [
                "osascript",
                "-e", 'tell application "Skim"',
                "-e", "activate",
                "-e", f'open POSIX file "{full_path}"',
                "-e", "end tell",
            ]
        )
    else:
        subprocess.run(["open", str(full_path)])


def _open_ebook(full_path, entry):
    """Open ebook with Apple Books."""
    print(f"Opening: {entry.get('title', full_path.name)} (Apple Books)")
    subprocess.run(["open", "-a", "Books", str(full_path)])


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
