from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Highlight:
    uuid: str
    text: str
    note: Optional[str] = None
    page: Optional[int] = None
    modified: Optional[datetime] = None
    color: Optional[str] = None


class Reader(ABC):
    name: str = ""
    supports: list = []

    @abstractmethod
    def open(self, path: Path, page: Optional[int] = None) -> bool:
        """Open a file with the reader.

        Args:
            path: Path to the file to open
            page: Optional page number to navigate to

        Returns:
            True if file was opened successfully
        """
        ...

    def extract_annotations(self, path: Path):
        """Extract annotations from a file.

        Args:
            path: Path to the file

        Returns:
            Reader-specific annotation data (or None if not supported)
        """
        return None

    def is_available(self) -> bool:
        """Check if the reader is available on this system.

        Returns:
            True if the reader can be used
        """
        return True