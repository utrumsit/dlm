import platform
import subprocess
from pathlib import Path
from typing import Optional

from .base import Reader, Highlight

# Import concrete readers
from .apple_books import AppleBooksReader
from .skim import SkimReader
from .sioyek import SioyekReader
from .foliate import FoliateReader


def get_reader(file_type: str) -> Reader:
    """Get the appropriate reader for a file type.

    Dispatches based on:
      1. Explicit config override (readers.pdf / readers.epub in config.toml)
      2. Platform defaults (Skim on macOS, Sioyek on Linux)

    Args:
        file_type: The file type (e.g., "pdf", "epub", "mobi")

    Returns:
        A Reader instance appropriate for the file type on this platform

    Raises:
        NotImplementedError: If no reader is configured for this file type
    """
    ft = file_type.lower()
    system = platform.system()

    # Load config values for explicit overrides
    from ..settings import (
        READERS_PDF, READERS_EPUB,
        SIOYEK_BINARY, SIOYEK_SHARED_DB,
        FOLIATE_BINARY, FOLIATE_LIBRARY_DIR,
    )

    if ft == "pdf":
        choice = (READERS_PDF or "").lower()
        if not choice:
            # Platform defaults
            choice = "skim" if system == "Darwin" else "sioyek"

        if choice == "skim":
            return SkimReader()
        if choice == "sioyek":
            return SioyekReader(binary=SIOYEK_BINARY, shared_db=SIOYEK_SHARED_DB)

        # Unknown explicit reader — fall back to platform default
        if system == "Darwin":
            return SkimReader()
        return SioyekReader(binary=SIOYEK_BINARY, shared_db=SIOYEK_SHARED_DB)

    # EPUB branch
    if ft in ("epub", "mobi", "azw3", "azw"):
        choice = (READERS_EPUB or "").lower()
        if not choice:
            choice = "apple_books" if system == "Darwin" else "foliate"

        if choice in ("apple_books", "apple-books"):
            return AppleBooksReader()
        if choice == "foliate":
            return FoliateReader(binary=FOLIATE_BINARY, library_dir=FOLIATE_LIBRARY_DIR)

        # Unknown explicit choice — fall back to platform default
        if system == "Darwin":
            return AppleBooksReader()
        return FoliateReader(binary=FOLIATE_BINARY, library_dir=FOLIATE_LIBRARY_DIR)

    raise NotImplementedError(f"No reader configured for {ft} on {system}")


def open_with_fallback(file_type: str, path: Path, page: Optional[int] = None) -> bool:
    """Try to open a file with its appropriate reader, falling back to system default.

    Args:
        file_type: The file type
        path: Path to the file
        page: Optional page number

    Returns:
        True if file was opened successfully
    """
    try:
        reader = get_reader(file_type)
        return reader.open(path, page)
    except NotImplementedError:
        # Fall back to system default opener
        if platform.system() == "Linux":
            subprocess.run(["xdg-open", str(path)])
            return True
        elif platform.system() == "Windows":
            subprocess.run(["start", str(path)], shell=True)
            return True
        else:
            return False


def get_highlights_from_reader(file_type: str, path: Path) -> Optional[list]:
    """Extract highlights from a file using the appropriate reader.

    Args:
        file_type: The file type
        path: Path to the file

    Returns:
        List of Highlight objects, or None if not supported
    """
    try:
        reader = get_reader(file_type)
        return reader.extract_annotations(path)
    except NotImplementedError:
        return None


# Re-export for convenience
__all__ = ["Reader", "Highlight", "get_reader", "open_with_fallback", "NotImplementedError"]
