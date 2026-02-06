"""
Shared data access for catalog and reading progress.
Single source of truth — other modules import from here.
"""

import json

from .settings import CATALOG_FILE, PROGRESS_FILE


def load_catalog():
    """Load the catalog.json file"""
    with open(CATALOG_FILE, "r") as f:
        data = json.load(f)
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
