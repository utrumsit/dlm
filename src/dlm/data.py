"""
Shared data access for catalog and reading progress.
Single source of truth — other modules import from here.
"""

import json
import sys

from .settings import CATALOG_FILE, PROGRESS_FILE


def load_catalog():
    """Load the catalog.json file. Exits with helpful message if missing."""
    if not CATALOG_FILE.exists():
        print(f"Error: Catalog not found at {CATALOG_FILE}")
        print("Run 'dlm-catalog' to build it first.")
        sys.exit(1)

    with open(CATALOG_FILE, "r") as f:
        data = json.load(f)

    if not data.get("catalog"):
        print("Warning: Catalog is empty. Add books to your library folders and run 'dlm-catalog'.")
        return []

    return data["catalog"]


def load_progress():
    """Load reading progress data"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(progress_data):
    """Save reading progress data"""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress_data, f, indent=2)
