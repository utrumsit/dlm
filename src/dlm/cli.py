#!/usr/bin/env python3
"""
Enhanced Digital Library Search Tool
Features: fuzzy matching, DDC search, reading progress tracking
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from .data import load_catalog, load_progress, save_progress
from .settings import LIBRARY_ROOT
from .extractor import extract_apple_books_notes, extract_skim_notes
from .fzf import run_fzf_search
from .joplin import JoplinClient
from .opener import open_file as _open_file


def fuzzy_match(query, text, threshold=0.6):
    """Calculate similarity ratio between query and text"""
    query_lower = query.lower()
    text_lower = text.lower()

    # Exact substring match gets bonus
    if query_lower in text_lower:
        return 1.0

    # Otherwise use sequence matcher
    return SequenceMatcher(None, query_lower, text_lower).ratio()


def search_catalog(query, field=None, file_type=None, ddc=None, fuzzy=True):
    """
    Search the catalog for matching entries
    query: search term
    field: specific field to search (title, author, subjects, category) or None for all
    file_type: filter by file type (pdf, epub, etc.)
    ddc: search by DDC number (exact or prefix match)
    fuzzy: enable fuzzy matching for typos
    """
    catalog = load_catalog()

    # If no search criteria are provided, return the whole catalog
    if not query and not field and not file_type and not ddc:
        return catalog

    results = []

    query_lower = query.lower() if query else ""

    for entry in catalog:
        match = False
        score = 0.0

        # Filter by file type first
        if file_type and entry.get("file_type", "").lower() != file_type.lower():
            continue

        # If no other criteria, it's a match because it passed the file_type filter
        if not ddc and not query:
            match = True
            score = 1.0

        # DDC search
        elif ddc:
            entry_ddc = entry.get("ddc", "")
            if entry_ddc and str(entry_ddc).startswith(str(ddc)):
                match = True
                score = 1.0

        # Text search
        elif query:
            if field is None:
                # Search all fields
                title_score = fuzzy_match(query, entry.get("title", ""))
                author_score = fuzzy_match(query, entry.get("author", ""))
                subject_scores = [
                    fuzzy_match(query, s) for s in entry.get("subjects", [])
                ]
                category_score = fuzzy_match(query, entry.get("category", ""))

                max_score = max(
                    [title_score, author_score, category_score] + subject_scores
                )

                if fuzzy:
                    if max_score >= 0.6:
                        match = True
                        score = max_score
                else:
                    if max_score == 1.0:  # Exact match only
                        match = True
                        score = max_score

            elif field == "title":
                score = fuzzy_match(query, entry.get("title", ""))
                match = score >= (0.6 if fuzzy else 1.0)
            elif field == "author":
                score = fuzzy_match(query, entry.get("author", ""))
                match = score >= (0.6 if fuzzy else 1.0)
            elif field == "subject":
                scores = [fuzzy_match(query, s) for s in entry.get("subjects", [])]
                score = max(scores) if scores else 0
                match = score >= (0.6 if fuzzy else 1.0)
            elif field == "category":
                score = fuzzy_match(query, entry.get("category", ""))
                match = score >= (0.6 if fuzzy else 1.0)

        if match:
            entry["_score"] = score
            results.append(entry)

    # Sort by score (highest first)
    results.sort(key=lambda x: x.get("_score", 0), reverse=True)

    return results


def display_results(results, show_progress=True):
    """Display search results in a numbered list"""
    if not results:
        print("No results found.")
        return None

    progress_data = load_progress() if show_progress else {}
    print(f"\nFound {len(results)} result(s):\n")

    for i, entry in enumerate(results, 1):
        author_str = f" by {entry['author']}" if entry.get("author") else ""
        ddc_str = f" [DDC: {entry['ddc']}]" if entry.get("ddc") else ""
        subjects_str = ", ".join(entry.get("subjects", [])[:3])  # Show first 3 subjects

        # Check reading progress
        file_id = entry.get("id")
        progress_str = ""
        if file_id in progress_data:
            prog = progress_data[file_id]
            if "page" in prog:
                progress_str = f" 📖 Last read: p.{prog['page']}"
            if "last_opened" in prog:
                progress_str += f" ({prog['last_opened']})"

        print(f"{i}. {entry['title']}{author_str}{ddc_str}")
        print(f"   Subjects: {subjects_str}")
        print(f"   Location: {entry['file_path']}{progress_str}")
        print()

    return results


def open_file(entry, set_page=None):
    """Open a file and optionally export notes to Joplin afterward.
    Delegates actual file opening to opener.py.
    """
    if not _open_file(entry, set_page=set_page):
        return False

    # After reading, offer to export notes to Joplin
    try:
        input("Press Enter after you have finished reading and making notes...")
        export_notes_to_joplin(entry)
    except KeyboardInterrupt:
        print("\nSkipping note export.")

    return True


def export_notes_to_joplin(entry):
    """Extract notes and export them to Joplin."""
    file_path = entry["file_path"]
    full_path = LIBRARY_ROOT / file_path
    file_type = entry.get("file_type", "").lower()
    title = entry.get("title", "Notes")
    author = entry.get("author", "")

    # Create author tag
    author_tags = []
    if author:
        names = author.split(" ")
        if len(names) > 1:
            # Assume last name is the last part, first name is the rest
            last_name = names[-1]
            first_name_parts = names[:-1]
            # Handle multi-word first names
            first_name = "-".join(first_name_parts)
            author_tags.append(f"{last_name.lower()}-{first_name.lower()}")
        else:
            author_tags.append(author.lower())

    notes = None
    if file_type == "pdf":
        skim_notes = extract_skim_notes(full_path)
        if skim_notes:
            # Construct biblio info from entry
            biblio_str = ""
            if entry.get("author"):
                biblio_str += f"**Author:** {entry['author']}\n"
            if entry.get("ddc"):
                biblio_str += f"**DDC:** {entry['ddc']}\n"
            if entry.get("subjects"):
                biblio_str += f"**Subjects:** {', '.join(entry['subjects'])}\n"

            notes = f"# Notes for {title}\n\n{biblio_str}\n---\n\n{skim_notes}"
    elif file_type in ["epub", "mobi", "azw3", "azw"]:
        data = extract_apple_books_notes(title)
        if data and data["notes"]:
            biblio_info = data.get("bibliographical_info", {})
            apple_notes = data.get("notes", [])

            # Format bibliographical info
            biblio_str = ""
            if biblio_info:
                biblio_str += f"**Author:** {biblio_info.get('author', 'N/A')}\n"
                biblio_str += f"**Genre:** {biblio_info.get('genre', 'N/A')}\n"
                biblio_str += f"**Language:** {biblio_info.get('language', 'N/A')}\n"
                biblio_str += (
                    f"**Page Count:** {biblio_info.get('page_count', 'N/A')}\n"
                )
                if biblio_info.get("release_date"):
                    release_date = datetime(2001, 1, 1) + datetime.timedelta(
                        seconds=biblio_info["release_date"]
                    )
                    biblio_str += (
                        f"**Release Date:** {release_date.strftime('%Y-%m-%d')}\n"
                    )

                if biblio_info.get("description"):
                    biblio_str += f"\n---\n\n> {biblio_info['description']}\n\n---\n\n"

            formatted_notes = [f"# Notes for {title}\n\n{biblio_str}"]
            for note in apple_notes:
                if note.get("highlight"):
                    formatted_notes.append(f"> {note['highlight']}")
                if note.get("note"):
                    formatted_notes.append(f"\n**Note:** {note['note']}\n")
            notes = "\n".join(formatted_notes)

    if notes:
        print("Found notes. Exporting to Joplin...")
        joplin = JoplinClient()
        if joplin.notebook_id:
            joplin.create_or_update_note(title, notes, tags=author_tags, append=True)
        else:
            print("Could not find or create Joplin notebook. Please check your config.")
    else:
        print("No new notes found to export.")


def print_usage():
    """Print usage information"""
    print(
        """
Enhanced Digital Library Search Tool

Usage:
  python search_enhanced.py <query>                    Search all fields (fuzzy)
  python search_enhanced.py --title <query>            Search titles only
  python search_enhanced.py --author <query>           Search authors only
  python search_enhanced.py --subject <query>          Search subjects only
  python search_enhanced.py --category <query>         Search categories only
  python search_enhanced.py --ddc <number>             Search by DDC number (e.g., 780, 006.3)
  python search_enhanced.py --type <ext> <query>       Filter by file type (pdf, epub)
  python search_enhanced.py --set-page <n> <query>     Set/save page for the selected file immediately
  python search_enhanced.py --exact <query>            Disable fuzzy matching (exact only)

DDC Quick Reference:
  000 - Computer Science     400 - Language          700 - Arts
  100 - Philosophy           500 - Science           780 - Music  
  200 - Religion             600 - Technology        790 - Recreation

Examples:
  python search_enhanced.py beethoven
  python search_enhanced.py --ddc 780           # All music
  python search_enhanced.py --ddc 006.3         # AI/ML only
  python search_enhanced.py --type pdf homer
  python search_enhanced.py --subject "byzantine liturgy"
  python search_enhanced.py --exact "Machine Learning"

After searching, enter a number to open that file, or 'q' to quit.
"""
    )


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print_usage()
        return

    # Parse arguments
    field = None
    query = None
    file_type = None
    ddc = None
    fuzzy = True

    set_page = None
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == "--title":
            field = "title"
            i += 1
        elif arg == "--author":
            field = "author"
            i += 1
        elif arg == "--subject":
            field = "subject"
            i += 1
        elif arg == "--category":
            field = "category"
            i += 1
        elif arg == "--ddc":
            if i + 1 < len(sys.argv):
                ddc = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --ddc requires a number")
                return
        elif arg == "--type":
            if i + 1 < len(sys.argv):
                file_type = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --type requires a file extension")
                return
        elif arg == "--set-page":
            if i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
                set_page = int(sys.argv[i + 1])
                i += 2
            else:
                print("Error: --set-page requires an integer page number")
                return
        elif arg == "--exact":
            fuzzy = False
            i += 1
        else:
            # Rest is the query
            query = " ".join(sys.argv[i:])
            break

    # If specific arguments are used, run once
    if set_page is not None or query:
        results = search_catalog(query, field, file_type, ddc, fuzzy)
        if not results:
            print("No results found.")
            return

        progress_data = load_progress()
        selected_entry = run_fzf_search(results, progress_data)
        if selected_entry:
            open_file(selected_entry, set_page=set_page)
        return

    # Interactive Loop Mode
    while True:
        results = search_catalog(None, field, file_type, ddc, fuzzy)

        if not results:
            print("No results found.")
            break

        progress_data = load_progress()
        selected_entry = run_fzf_search(results, progress_data)

        if selected_entry:
            open_file(selected_entry)
            print("\nReturning to library...")
            import time

            time.sleep(1)
        else:
            print("Goodbye!")
            break


if __name__ == "__main__":
    main()
