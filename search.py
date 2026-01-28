#!/usr/bin/env python3
"""
Digital Library Search Tool
Search and open files from the catalog
"""

import json
import sys
import subprocess
import os
import platform
from pathlib import Path

CATALOG_FILE = Path(__file__).parent / "catalog.json"
LIBRARY_ROOT = Path(os.environ.get('DLM_LIBRARY_ROOT', Path(__file__).parent)).resolve()


def load_catalog():
    """Load the catalog.json file"""
    with open(CATALOG_FILE, 'r') as f:
        data = json.load(f)
    return data['catalog']


def search_catalog(query, field=None):
    """
    Search the catalog for matching entries
    query: search term
    field: specific field to search (title, author, subjects, category) or None for all
    """
    catalog = load_catalog()
    results = []

    query_lower = query.lower()

    for entry in catalog:
        match = False

        if field is None:
            # Search all fields
            if query_lower in entry.get('title', '').lower():
                match = True
            elif query_lower in entry.get('author', '').lower():
                match = True
            elif any(query_lower in subject.lower() for subject in entry.get('subjects', [])):
                match = True
            elif query_lower in entry.get('category', '').lower():
                match = True
        elif field == 'title':
            if query_lower in entry.get('title', '').lower():
                match = True
        elif field == 'author':
            if query_lower in entry.get('author', '').lower():
                match = True
        elif field == 'subject':
            if any(query_lower in subject.lower() for subject in entry.get('subjects', [])):
                match = True
        elif field == 'category':
            if query_lower in entry.get('category', '').lower():
                match = True

        if match:
            results.append(entry)

    return results


def display_results(results):
    """Display search results in a numbered list"""
    if not results:
        print("No results found.")
        return None

    print(f"\nFound {len(results)} result(s):\n")

    for i, entry in enumerate(results, 1):
        author_str = f" by {entry['author']}" if entry.get('author') else ""
        subjects_str = ", ".join(entry.get('subjects', []))

        print(f"{i}. {entry['title']}{author_str}")
        print(f"   Subjects: {subjects_str}")
        print(f"   Location: {entry['file_path']}")
        print()

    return results


def open_file(file_path):
    """Open a file with the system default application"""
    full_path = LIBRARY_ROOT / file_path

    if not full_path.exists():
        print(f"Error: File not found at {full_path}")
        return False

    system = platform.system()

    try:
        if system == 'Darwin':  # macOS
            if full_path.suffix.lower() in ['.epub', '.mobi', '.azw3', '.azw']:
                subprocess.Popen(['/Applications/KOReader.app/Contents/MacOS/koreader', str(full_path)])
            else:
                subprocess.run(['open', str(full_path)])
        elif system == 'Windows':
            subprocess.run(['start', str(full_path)], shell=True)
        else:  # Linux and others
            subprocess.run(['xdg-open', str(full_path)])

        print(f"Opening: {full_path.name}")
        return True
    except Exception as e:
        print(f"Error opening file: {e}")
        return False


def print_usage():
    """Print usage information"""
    print("""
Digital Library Search Tool

Usage:
  python search.py <query>                 Search all fields
  python search.py --title <query>         Search titles only
  python search.py --author <query>        Search authors only
  python search.py --subject <query>       Search subjects only
  python search.py --category <query>      Search categories only

Examples:
  python search.py beethoven
  python search.py --subject "byzantine liturgy"
  python search.py --author homer
  python search.py --title "real book"

After searching, you can enter a number to open that file, or 'q' to quit.
""")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print_usage()
        return

    # Parse arguments
    field = None
    query = None

    if sys.argv[1].startswith('--'):
        if len(sys.argv) < 3:
            print("Error: Missing query after field specifier")
            print_usage()
            return

        field_map = {
            '--title': 'title',
            '--author': 'author',
            '--subject': 'subject',
            '--category': 'category'
        }

        field = field_map.get(sys.argv[1])
        if not field:
            print(f"Error: Unknown field {sys.argv[1]}")
            print_usage()
            return

        query = ' '.join(sys.argv[2:])
    else:
        query = ' '.join(sys.argv[1:])

    # Search
    results = search_catalog(query, field)
    displayed = display_results(results)

    if not displayed:
        return

    # Interactive selection
    while True:
        try:
            choice = input("Enter number to open file (or 'q' to quit): ").strip()

            if choice.lower() == 'q':
                break

            try:
                num = int(choice)
                if 1 <= num <= len(results):
                    open_file(results[num - 1]['file_path'])
                    break
                else:
                    print(f"Please enter a number between 1 and {len(results)}")
            except ValueError:
                print("Please enter a valid number or 'q' to quit")

        except KeyboardInterrupt:
            print("\nQuitting...")
            break


if __name__ == '__main__':
    main()
