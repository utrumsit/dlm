import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .catalog import extract_pdf_metadata, extract_epub_metadata, generate_catalog
from .lookup import (
    lookup_metadata,
    lookup_openlibrary_title,
    lookup_google_books_title,
    lookup_openlibrary_isbn
)
from .settings import LIBRARY_ROOT, CATALOG_FILE

def is_bad_metadata(title, author, filepath):
    """
    Determine if metadata is 'bad' and needs fixing.
    """
    stem = filepath.stem
    
    # If title is missing or looks like a filename
    if not title or "_" in title or title.lower().endswith((".pdf", ".epub")):
        return True
    
    # If author is missing or looks like junk
    author_is_bad = not author or author.lower() in ["unknown", "anonymous", "none", "n/a", "unknown author"]
    if not author_is_bad and (re.match(r"^[A-Z0-9]{32}$", author) or len(author) > 100):
        author_is_bad = True
        
    if author_is_bad:
        return True
    
    # If title is exactly the stem (case insensitive) but we already have a good author, 
    # it might be okay, but usually we want a cleaner title than a filename.
    # However, to avoid loops, if it doesn't have filename junk like underscores, we can accept it.
    
    return False

def write_pdf_metadata(filepath, title, author):
    """Write metadata to PDF using exiftool."""
    try:
        cmd = [
            "exiftool",
            f"-Title={title}",
            f"-Author={author}",
            "-overwrite_original",
            str(filepath)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Error writing PDF metadata: {e}")
        return False

def write_epub_metadata(filepath, title, author):
    """Write metadata to EPUB by patching the OPF file."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Extract the whole EPUB to a temp directory
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Find the .opf file
        opf_path = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".opf"):
                    opf_path = Path(root) / file
                    break
            if opf_path:
                break
        
        if not opf_path:
            return False
        
        # Parse XML
        ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
        ET.register_namespace('opf', 'http://www.idpf.org/2007/opf')
        
        tree = ET.parse(opf_path)
        root = tree.getroot()
        
        ns = {
            'dc': 'http://purl.org/dc/elements/1.1/',
            'opf': 'http://www.idpf.org/2007/opf'
        }
        
        # Update title
        title_elem = root.find(".//dc:title", ns)
        if title_elem is not None:
            title_elem.text = title
        else:
            # Add it if missing
            metadata = root.find(".//metadata", ns)
            if metadata is not None:
                new_title = ET.SubElement(metadata, "{http://purl.org/dc/elements/1.1/}title")
                new_title.text = title

        # Update creator (author)
        creator_elem = root.find(".//dc:creator", ns)
        if creator_elem is not None:
            creator_elem.text = author
        else:
            # Add it if missing
            metadata = root.find(".//metadata", ns)
            if metadata is not None:
                new_creator = ET.SubElement(metadata, "{http://purl.org/dc/elements/1.1/}creator")
                new_creator.text = author
        
        tree.write(opf_path, encoding="utf-8", xml_declaration=True)
        
        # Zip it back up
        shutil.make_archive(str(filepath.with_suffix('')), 'zip', temp_dir)
        os.replace(str(filepath.with_suffix('.zip')), str(filepath))
        
        return True
    except Exception as e:
        print(f"Error writing EPUB metadata: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description="Retroactively fix metadata in the library.")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying them.")
    parser.add_argument("--folder", type=str, help="Run on a specific subfolder (relative to library root).")
    parser.add_argument("--yes", action="store_true", help="Apply all changes without prompting.")
    
    args = parser.parse_args()
    
    base_path = LIBRARY_ROOT
    if args.folder:
        base_path = LIBRARY_ROOT / args.folder
        if not base_path.exists():
            print(f"Folder not found: {base_path}")
            return

    print(f"Scanning {base_path}...")
    
    for root, dirs, files in os.walk(base_path):
        # Skip certain directories
        if "_Inbox" in root or ".git" in root or ".pi" in root:
            continue
            
        for filename in files:
            if not (filename.endswith(".pdf") or filename.endswith(".epub")):
                continue
                
            filepath = Path(root) / filename
            
            # Extract current metadata
            if filename.endswith(".pdf"):
                curr_title, curr_author = extract_pdf_metadata(filepath)
            else:
                curr_title, curr_author = extract_epub_metadata(filepath)
                
            if is_bad_metadata(curr_title, curr_author, filepath):
                print(f"\n[Bad Metadata] {filepath.relative_to(LIBRARY_ROOT)}")
                print(f"  Current: '{curr_title}' by '{curr_author}'")
                
                # Lookup
                result = lookup_metadata(filepath)
                new_title = None
                new_author = None
                
                if result:
                    new_title = result.get("title")
                    new_author = result.get("author")
                
                if args.dry_run:
                    if result:
                        print(f"  Found:   '{new_title}' by '{new_author}' ({result.get('source')})")
                    else:
                        print("  \u2717 No metadata found via online lookup.")
                    continue
                        
                apply = False
                if args.yes and result:
                    apply = True
                else:
                    while True:
                        if result:
                            print(f"  Found:   '{new_title}' by '{new_author}' ({result.get('source')})")
                            choice = input("  Apply? [Y/n/m(anual)/q(uery)/i(sbn)/s(kip all)]: ").strip().lower()
                        else:
                            print("  \u2717 No metadata found.")
                            choice = input("  Choice: [m(anual)/q(uery)/i(sbn)/n(ext)/s(kip all)]: ").strip().lower()

                        if choice == 'y' or choice == '':
                            if result:
                                apply = True
                                break
                            else:
                                print("    Please choose an action.")
                        elif choice == 'n':
                            apply = False
                            break
                        elif choice == 'm':
                            new_title = input(f"    New title [{new_title or curr_title}]: ").strip() or (new_title or curr_title)
                            new_author = input(f"    New author [{new_author or curr_author}]: ").strip() or (new_author or curr_author)
                            apply = True
                            break
                        elif choice == 'q':
                            query = input("    New search query: ").strip()
                            if query:
                                result = lookup_openlibrary_title(query)
                                if not result:
                                    result = lookup_google_books_title(query)
                                if result:
                                    new_title = result.get("title")
                                    new_author = result.get("author")
                                else:
                                    print("    \u2717 No results for that query.")
                        elif choice == 'i':
                            isbn = input("    Enter ISBN: ").strip().replace("-", "").replace(" ", "")
                            if isbn:
                                result = lookup_openlibrary_isbn(isbn)
                                if result:
                                    new_title = result.get("title")
                                    new_author = result.get("author")
                                else:
                                    print("    \u2717 No results for that ISBN.")
                        elif choice == 's':
                            print("Exiting...")
                            return
                        else:
                            print("    Invalid choice.")
                
                if apply and new_title and new_author:
                    success = False
                    if filename.endswith(".pdf"):
                        success = write_pdf_metadata(filepath, new_title, new_author)
                    else:
                        success = write_epub_metadata(filepath, new_title, new_author)
                    
                    if success:
                        print("  \u2713 Updated.")
                    else:
                        print("  \u2717 Failed to update.")

    print("\nRegenerating catalog...")
    catalog_data = generate_catalog()
    with open(CATALOG_FILE, "w") as f:
        json.dump(catalog_data, f, indent=2)
    print(f"Catalog updated: {CATALOG_FILE}")

if __name__ == "__main__":
    main()
