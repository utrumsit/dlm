#!/usr/bin/env python3
"""
Interactive Library Search with fzf and Skim
Features: real-time fuzzy search, metadata preview, automatic page tracking
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .data import load_catalog, load_progress, save_progress
from .opener import open_file
from .settings import CATALOG_FILE, LIBRARY_ROOT, PROGRESS_FILE


def filter_catalog(catalog, ddc=None, file_type=None, recent=False, in_progress=False):
    """Filter catalog based on criteria"""
    filtered = catalog

    # DDC filter
    if ddc:
        filtered = [
            e for e in filtered if e.get("ddc") and str(e["ddc"]).startswith(str(ddc))
        ]

    # File type filter
    if file_type:
        filtered = [
            e for e in filtered if e.get("file_type", "").lower() == file_type.lower()
        ]

    # Recent filter
    if recent:
        progress_data = load_progress()
        filtered = [e for e in filtered if e.get("id") in progress_data]
        # Sort by last opened
        filtered.sort(
            key=lambda x: progress_data.get(x["id"], {}).get("last_opened", ""),
            reverse=True,
        )

    # In progress filter
    if in_progress:
        progress_data = load_progress()
        filtered = [
            e
            for e in filtered
            if e.get("id") in progress_data and "page" in progress_data[e["id"]]
        ]

    return filtered


def format_entry_for_fzf(entry, progress_data):
    """Format catalog entry for fzf display"""
    title = entry.get("title", "Unknown")[:70]
    author = entry.get("author", "")[:30] if entry.get("author") else ""
    ddc = entry.get("ddc", "---")
    file_type = entry.get("file_type", "pdf").upper()

    # Format: TITLE (AUTHOR) [DDC] TYPE
    # Keep it simple and readable
    if author:
        return f"{title} ({author}) [{ddc}] {file_type}"
    else:
        return f"{title} [{ddc}] {file_type}"


def create_preview_script():
    """Create a preview script for fzf"""
    preview_script = LIBRARY_ROOT / ".fzf_preview.py"

    # Create a Python script instead of bash for better reliability
    script_content = f"""#!/usr/bin/env python3
import json
import sys
import os
from pathlib import Path

# Paths must be resolved dynamically in the preview script too
LIBRARY_ROOT = Path(os.environ.get('DLM_LIBRARY_ROOT', os.getcwd())).resolve()
CATALOG_FILE = LIBRARY_ROOT / "catalog.json"
PROGRESS_FILE = LIBRARY_ROOT / "reading_progress.json"

if len(sys.argv) < 2:
    sys.exit(0)

entry_id = sys.argv[1]

try:
    # Load catalog and progress
    with open(CATALOG_FILE) as f:
        catalog = json.load(f)['catalog']
    
    progress = {{}}
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            progress = json.load(f)
    
    # Find entry
    entry = next((e for e in catalog if e['id'] == entry_id), None)
    if not entry:
        print("Entry not found")
        sys.exit(0)
    
    # Display metadata
    print(f"\033[1m{{entry['title']}}\033[0m")
    print()
    
    if entry.get('author'):
        print(f"Author: {{entry['author']}}")
    
    print(f"DDC: {{entry.get('ddc', 'N/A')}}")
    print(f"Type: {{entry.get('file_type', 'unknown').upper()}}")
    print()
    print(f"Subjects: {{', '.join(entry.get('subjects', [])[:5])}}")
    print()
    print(f"Location: {{entry['file_path']}}")
    
    # Show reading progress
    if entry_id in progress:
        if 'last_opened' in progress[entry_id]:
            print()
            print(f"Last opened: {{progress[entry_id]['last_opened']}}")
except Exception as e:
    print(f"Error: {{e}}")
"""

    with open(preview_script, "w") as f:
        f.write(script_content)

    preview_script.chmod(0o755)
    return preview_script


def run_fzf_search(entries, progress_data, preview=True):
    """Run fzf interactive search on catalog entries"""
    if not entries:
        print("No entries to search")
        return None

    # Format entries for fzf
    # Use format: ID<TAB>Display Text
    fzf_lines = []
    id_map = {}

    for entry in entries:
        fzf_line = format_entry_for_fzf(entry, progress_data)
        entry_id = entry.get("id")
        fzf_lines.append(f"{entry_id}\t{fzf_line}")
        id_map[entry_id] = entry

    # Create preview script if needed
    preview_script = None
    if preview:
        preview_script = create_preview_script()

    # Build fzf command with better UI
    fzf_cmd = [
        "fzf",
        "--ansi",
        "--delimiter=\t",
        "--with-nth=2..",  # Display only the text part (hide ID)
        # Don't restrict search with --nth, let it search everything
        "--prompt=📚 ",
        "--header=Type to search • ↑↓ navigate • Enter to open • Ctrl-C cancel",
        "--preview-window=right:45%:wrap",
        "--height=100%",
        "--layout=reverse",
        "--border=rounded",
        "--info=inline",
        "--tabstop=4",
    ]

    if preview and preview_script:
        fzf_cmd.extend(
            [
                "--preview",
                f"python3 {preview_script} {{1}}",  # Pass entry ID (first field) to preview
            ]
        )

    # Run fzf
    try:
        result = subprocess.run(
            fzf_cmd, input="\n".join(fzf_lines), text=True, capture_output=True
        )

        if result.returncode == 0 and result.stdout.strip():
            # Extract entry ID from selection (before TAB)
            selected = result.stdout.strip()
            entry_id = selected.split("\t")[0]
            return id_map.get(entry_id)

    except KeyboardInterrupt:
        print("\nCancelled")
    except FileNotFoundError:
        print("Error: fzf not found. Install with: brew install fzf")

    return None


def update_page_command(title_query, page):
    """Quick command to update page number for a book"""
    catalog = load_catalog()
    progress_data = load_progress()

    # Find matching book
    matches = [e for e in catalog if title_query.lower() in e.get("title", "").lower()]

    if not matches:
        print(f"No book found matching: {title_query}")
        return

    if len(matches) > 1:
        print(f"Multiple matches found for '{title_query}':")
        for i, entry in enumerate(matches[:5], 1):
            print(f"  {i}. {entry['title']}")
        print("\nBe more specific in your query.")
        return

    # Update the single match
    entry = matches[0]
    file_id = entry["id"]

    if file_id not in progress_data:
        progress_data[file_id] = {}

    progress_data[file_id]["page"] = page
    progress_data[file_id]["last_opened"] = datetime.now().strftime("%Y-%m-%d")
    save_progress(progress_data)

    print(f"✓ Updated '{entry['title']}' to page {page}")


def show_recent():
    """Show recently accessed books"""
    catalog = load_catalog()
    progress_data = load_progress()

    # Get books with progress, sort by last opened
    recent_entries = []
    for entry in catalog:
        file_id = entry.get("id")
        if file_id in progress_data:
            entry["_last_opened"] = progress_data[file_id].get("last_opened", "")
            recent_entries.append(entry)

    recent_entries.sort(key=lambda x: x.get("_last_opened", ""), reverse=True)

    return recent_entries[:50]  # Top 50 recent


def print_usage():
    """Print usage information"""
    print(
        """
📚 Interactive Library Search with fzf

Usage:
  ./lib                          Interactive search (all books)
  ./lib --ddc <number>           Filter by DDC category
  ./lib --type <ext>             Filter by file type (pdf, epub)
  ./lib --recent                 Show recently accessed books
  ./lib --in-progress            Show books with saved page numbers
  ./lib --update-page <title> <page>   Quick page update
  
Interactive Mode:
  - Type to search in real-time (fuzzy matching)
  - Use ↑↓ arrows to navigate
  - Press Enter to open selected book
  - Press Ctrl-C to cancel
  - Preview panel shows metadata and progress

Examples:
  ./lib                          # Browse all books
  ./lib --ddc 780                # Browse all music
  ./lib --recent                 # Recent reads
  ./lib --type pdf --ddc 006.3   # AI PDFs only
  ./lib --update-page "Plato" 42 # Set page without opening

Reading with Skim:
  - Skim remembers your page position automatically
  - Annotations are preserved in the PDF

DDC Quick Reference:
  000 - Computer Science    500 - Science       780 - Music
  100 - Philosophy          600 - Technology    790 - Recreation
  200 - Religion            700 - Arts
  400 - Language
"""
    )


def main():
    # Check for fzf
    if not shutil.which("fzf"):
        print("Error: fzf not found. Install with: brew install fzf")
        sys.exit(1)

    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print_usage()
        return

    # Handle --update-page command
    if len(sys.argv) >= 4 and sys.argv[1] == "--update-page":
        title = sys.argv[2]
        page = int(sys.argv[3])
        update_page_command(title, page)
        return

    # Parse filter arguments
    ddc = None
    file_type = None
    recent = False
    in_progress = False
    initial_query = None

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == "--ddc" and i + 1 < len(sys.argv):
            ddc = sys.argv[i + 1]
            i += 2
        elif arg == "--type" and i + 1 < len(sys.argv):
            file_type = sys.argv[i + 1]
            i += 2
        elif arg == "--recent":
            recent = True
            i += 1
        elif arg == "--in-progress":
            in_progress = True
            i += 1
        elif not arg.startswith("--"):
            # Non-flag argument - use as initial query for fzf
            initial_query = " ".join(sys.argv[i:])
            break
        else:
            i += 1

    # Load and filter catalog
    catalog = load_catalog()
    progress_data = load_progress()

    if recent:
        entries = show_recent()
        if not entries:
            print("No recently accessed books found.")
            return
    else:
        entries = filter_catalog(catalog, ddc, file_type, recent, in_progress)

    if not entries:
        print("No books found matching filters.")
        return

    # Show summary
    filter_desc = []
    if ddc:
        filter_desc.append(f"DDC {ddc}")
    if file_type:
        filter_desc.append(f"{file_type.upper()} files")
    if recent:
        filter_desc.append("recently accessed")
    if in_progress:
        filter_desc.append("in progress")

    if filter_desc:
        print(f"Searching: {', '.join(filter_desc)} ({len(entries)} books)")
    else:
        print(f"Searching: all books ({len(entries)} total)")

    # Run fzf
    selected = run_fzf_search(entries, progress_data)

    if selected:
        print(f"\n📖 Selected: {selected['title']}")
        open_file(selected)


if __name__ == "__main__":
    main()
