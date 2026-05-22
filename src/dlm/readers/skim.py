import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from ..settings import SKIM_APP_PATH
from .base import Reader


class SkimReader(Reader):
    """Reader for PDF files using Skim on macOS."""

    name = "skim"
    supports = ["pdf"]

    def open(self, path: Path, page: Optional[int] = None) -> bool:
        """Open a PDF with Skim via AppleScript."""
        if platform.system() != "Darwin":
            return False

        skim_path = Path(SKIM_APP_PATH) / "Contents" / "MacOS" / "Skim"
        if skim_path.exists():
            subprocess.Popen(
                [
                    "osascript",
                    "-e", f'tell application "{SKIM_APP_PATH}"',
                    "-e", "activate",
                    "-e", f'open POSIX file "{path}"',
                    "-e", "end tell",
                ]
            )
            return True
        else:
            # Fall back to system open
            subprocess.run(["open", str(path)])
            return True

    def extract_annotations(self, path: Path):
        """Extract notes from a PDF using Skim's skimnotes command-line tool."""
        if platform.system() != "Darwin":
            return None

        try:
            # Try config path first, then PATH
            skimnotes_path = (
                Path(SKIM_APP_PATH) / "Contents" / "SharedSupport" / "skimnotes"
            )
            if not skimnotes_path.exists():
                skimnotes_path = shutil.which("skimnotes")
            if not skimnotes_path:
                print("skimnotes tool not found.")
                return None
            skimnotes_path = str(skimnotes_path)

            # 1. Try to get from extended attributes first
            result = subprocess.run(
                [skimnotes_path, "get", "-format", "text", str(path), "-"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout

            # 2. If empty, check for a .skim sidecar file
            sidecar_path = Path(path).with_suffix(".skim")
            if sidecar_path.exists():
                print(f"Found sidecar notes file: {sidecar_path.name}")
                result = subprocess.run(
                    [skimnotes_path, "get", "-format", "text", str(sidecar_path), "-"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return result.stdout

            return None
        except Exception as e:
            print(f"An error occurred while extracting Skim notes: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Skim is available on this system."""
        if platform.system() != "Darwin":
            return False
        skim_path = Path(SKIM_APP_PATH) / "Contents" / "MacOS" / "Skim"
        return skim_path.exists() or shutil.which("open") is not None