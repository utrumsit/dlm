#!/usr/bin/env python3
"""
Auto-Sort Books using Open Library API (Intelligent Version)
Scans _Inbox, looks up DDC, and moves files to the correct library folder.
Learns new subcategories from user input.
"""

import json
import os
import re
import shutil
import time
from pathlib import Path

import requests

LIBRARY_ROOT = Path(os.environ.get("DLM_LIBRARY_ROOT", Path(__file__).parent)).resolve()
INBOX_DIR = LIBRARY_ROOT / "_Inbox"
CONFIG_FILE = LIBRARY_ROOT / "sorting_config.json"


def load_config():
    """Load sorting rules from JSON"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"ddc_map": {}, "subcategory_map": {}}


def save_config(config):
    """Save sorting rules to JSON"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, sort_keys=True)


def clean_filename(filename):
    """Convert filename to search query"""
    name = Path(filename).stem
    name = name.replace("_", " ").replace("-", " ").replace(".", " ")
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"\[.*?\]", "", name)
    return name.strip()


def get_ddc_from_open_library(query):
    """Search Open Library for DDC"""
    try:
        url = "https://openlibrary.org/search.json"
        params = {"q": query, "fields": "ddc,title,author_name", "limit": 1}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("numFound", 0) > 0:
                doc = data["docs"][0]
                ddc_list = doc.get("ddc", [])
                title = doc.get("title", "Unknown")
                if ddc_list:
                    return ddc_list[0], title
    except Exception as e:
        print(f"  Error querying API: {e}")

    return None, None


def determine_destination(ddc, config, filename=None, title=None):
    """Find the best folder, prompting user for new subcategories if specific DDC found"""
    if not ddc:
        return None

    ddc_str = str(ddc).split(".")[0]
    if len(ddc_str) < 3:
        ddc_str = ddc_str.zfill(3)

    subcategory_map = config.get("subcategory_map", {})
    ddc_map = config.get("ddc_map", {})

    # 1. Try specific subcategory match
    # Sort keys by length descending to match longest prefix first
    for prefix, folder in sorted(
        subcategory_map.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if ddc_str.startswith(prefix):
            return LIBRARY_ROOT / folder

    # 2. Try top-level century match
    hundreds = ddc_str[0]
    broad_folder = None
    if hundreds in ddc_map:
        broad_folder = LIBRARY_ROOT / ddc_map[hundreds]

    # INTELLIGENT PROMPT LOGIC
    # If we have a broad match (or even no match) but a specific DDC, ask the user
    # Don't ask if the DDC is just "800" or "000" (too generic)
    if ddc_str[-2:] != "00":
        print(f"\n  Found specific DDC: {ddc} ({title})")
        if broad_folder:
            print(f"  Current plan: Move to broad category '{broad_folder.name}'")
        else:
            print("  Current plan: No category found (stay in Inbox)")

        choice = (
            input(
                f"  Would you like to define a new subcategory for DDC {ddc_str}? (y/N): "
            )
            .strip()
            .lower()
        )

        if choice == "y":
            # Suggest a prefix (e.g., 841 -> 840, 84 -> 84)
            # Try to round down to nearest ten
            prefix_suggestion = ddc_str[:2]

            print(
                f"  (Tip: Enter prefix '{prefix_suggestion}' for all {prefix_suggestion}0s, or '{ddc_str}' for just this)"
            )
            prefix = (
                input(f"  Enter DDC prefix to match (default {ddc_str}): ").strip()
                or ddc_str
            )

            # Suggest parent folder
            parent_suggestion = (
                broad_folder.name if broad_folder else "New_Parent_Folder"
            )
            folder_name = input(
                "  Enter subfolder name (e.g. '840_French_Literature'): "
            ).strip()

            if prefix and folder_name:
                # Construct full path relative to Library Root
                if broad_folder:
                    # e.g. 800_Literature/840_French_Literature
                    rel_path = f"{broad_folder.name}/{folder_name}"
                else:
                    # Top level
                    rel_path = folder_name

                # Update Config
                config["subcategory_map"][prefix] = rel_path
                save_config(config)
                print(f"  \u2713 Saved rule: DDC {prefix}* -> {rel_path}")

                return LIBRARY_ROOT / rel_path

    # Fallback to broad folder if no new rule defined
    return broad_folder


def sort_books():
    print(f"Scanning {INBOX_DIR}...")
    if not INBOX_DIR.exists():
        print("_Inbox not found.")
        return

    files = [
        f for f in INBOX_DIR.iterdir() if f.is_file() and not f.name.startswith(".")
    ]

    if not files:
        print("Inbox is empty.")
        return

    print(f"Found {len(files)} files.")

    config = load_config()

    for file in files:
        print(f"\nProcessing: {file.name}")
        query = clean_filename(file.name)
        print(f"  Searching Open Library for: '{query}'...")

        ddc, title = get_ddc_from_open_library(query)

        if ddc:
            dest_folder = determine_destination(ddc, config, file.name, title)

            if dest_folder:
                # Create folder if it doesn't exist
                if not dest_folder.exists():
                    print(f"  -> Creating directory: {dest_folder}")
                    dest_folder.mkdir(parents=True, exist_ok=True)

                dest_path = dest_folder / file.name
                print(f"  -> Moving to: {dest_folder.relative_to(LIBRARY_ROOT)}/")
                shutil.move(str(file), str(dest_path))
            else:
                print(f"  -> Could not map DDC {ddc} to a folder. Left in Inbox.")
        else:
            print("  -> No DDC found in Open Library.")

        time.sleep(1)


if __name__ == "__main__":
    sort_books()
