import re
import subprocess
import time
from pathlib import Path

import requests
import wordninja

def clean_filename_for_query(filename):
    """
    Improve filename cleaning for better search results.
    - Split run-together words: completepeanuts -> complete peanuts (via wordninja)
    - Handle common series patterns
    - Strip common junk: -bw, _v2, libgen.li, hashes
    - Handle 'Author - Title' pattern
    """
    # Remove extension
    stem = Path(filename).stem
    
    # Strip common junk
    junk_patterns = [
        r"-bw", r"_v2", r"libgen\.li", 
        r"CR![A-Z0-9]+", # libgen hashes
        r"\(.*?\)", r"\[.*?\]" # Content in parens/brackets
    ]
    for pattern in junk_patterns:
        stem = re.sub(pattern, "", stem, flags=re.IGNORECASE)
    
    # Handle 'Author - Title' or 'Author - Title - Year'
    # If there's an author prefix, prioritize it but keep the rest
    if " - " in stem:
        parts = stem.split(" - ")
        if len(parts) >= 2:
            stem = f"{parts[0]} {parts[1]}"
    
    # Use wordninja to split run-together lowercase words
    # Replace separators with spaces before splitting to help wordninja
    stem = stem.replace("_", " ").replace("-", " ").replace(".", " ")
    words = wordninja.split(stem)
    stem = " ".join(words)
    
    # Known series patterns (e.g., completepeanuts1953-1954)
    # wordninja usually handles this but we'll ensure year is separated
    stem = re.sub(r"([a-zA-Z]+)(\d{4})", r"\1 \2", stem)
    
    # Clean up multiple spaces
    stem = re.sub(r"\s+", " ", stem).strip()
    
    return stem

def extract_isbn_from_pdf(filepath):
    """Run pdftotext on first few pages and grep for ISBN."""
    if not filepath.suffix.lower() == ".pdf":
        return None
    
    try:
        # Just check first 5 pages for ISBN (usually on copyright page)
        result = subprocess.run(
            ["pdftotext", "-l", "5", str(filepath), "-"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            text = result.stdout
            # ISBN-13 pattern: 978 or 979 followed by 10 digits (often with hyphens)
            isbn13_matches = re.findall(r"(?:ISBN(?:-13)?:?\s*)?(97[89][-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d)", text, re.IGNORECASE)
            if isbn13_matches:
                # Clean up the first match
                return re.sub(r"[-\s]", "", isbn13_matches[0])
            
            # ISBN-10 pattern: 10 digits (last can be X)
            isbn10_matches = re.findall(r"(?:ISBN(?:-10)?:?\s*)?(\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*\d[-\s]*[0-9X])", text, re.IGNORECASE)
            if isbn10_matches:
                isbn = re.sub(r"[-\s]", "", isbn10_matches[0])
                if len(isbn) == 10:
                    return isbn
    except Exception:
        pass
    return None

def lookup_openlibrary_isbn(isbn):
    """Lookup metadata on OpenLibrary by ISBN."""
    try:
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            key = f"ISBN:{isbn}"
            if key in data:
                book = data[key]
                authors = [a["name"] for a in book.get("authors", [])]
                return {
                    "title": book.get("title"),
                    "author": ", ".join(authors) if authors else None,
                    "publisher": ", ".join([p["name"] for p in book.get("publishers", [])]) if book.get("publishers") else None,
                    "year": book.get("publish_date"),
                    "isbn": isbn,
                    "source": "openlibrary_isbn",
                    "subjects": [s["name"] for s in book.get("subjects", [])] if book.get("subjects") else []
                }
    except Exception:
        pass
    return None

def lookup_openlibrary_title(query):
    """Lookup metadata on OpenLibrary by title search."""
    try:
        url = "https://openlibrary.org/search.json"
        params = {"q": query, "limit": 5}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("docs"):
                # Pick the first one for now (best match)
                book = data["docs"][0]
                authors = book.get("author_name", [])
                isbns = book.get("isbn", [])
                return {
                    "title": book.get("title"),
                    "author": ", ".join(authors) if authors else None,
                    "publisher": ", ".join(book.get("publisher", [])) if book.get("publisher") else None,
                    "year": str(book.get("first_publish_year", "")),
                    "isbn": isbns[0] if isbns else None,
                    "source": "openlibrary_title",
                    "subjects": book.get("subject", []),
                    "ddc": book.get("ddc", [None])[0] if book.get("ddc") else None
                }
    except Exception:
        pass
    return None

def lookup_google_books_title(query):
    """Lookup metadata on Google Books by title search."""
    try:
        url = "https://www.googleapis.com/books/v1/volumes"
        params = {"q": query, "maxResults": 3}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                book_info = data["items"][0]["volumeInfo"]
                authors = book_info.get("authors", [])
                publish_date = book_info.get("publishedDate", "")
                year = publish_date[:4] if len(publish_date) >= 4 else None
                
                isbns = book_info.get("industryIdentifiers", [])
                isbn = None
                for id_obj in isbns:
                    if id_obj["type"] == "ISBN_13":
                        isbn = id_obj["identifier"]
                        break
                    if id_obj["type"] == "ISBN_10":
                        isbn = id_obj["identifier"]
                
                return {
                    "title": book_info.get("title"),
                    "author": ", ".join(authors) if authors else None,
                    "publisher": book_info.get("publisher"),
                    "year": year,
                    "isbn": isbn,
                    "source": "google_books",
                    "subjects": book_info.get("categories", [])
                }
    except Exception:
        pass
    return None

def lookup_metadata(filepath):
    """Cascade lookup function for metadata."""
    filepath = Path(filepath)
    
    # 1. Extract ISBN from PDF text
    isbn = extract_isbn_from_pdf(filepath)
    if isbn:
        result = lookup_openlibrary_isbn(isbn)
        if result and result.get("title"):
            return result
        time.sleep(0.5)
    
    query = clean_filename_for_query(filepath.name)
    
    # 2. OpenLibrary by title
    result = lookup_openlibrary_title(query)
    if result and result.get("title"):
        return result
    time.sleep(0.5)
    
    # 3. Google Books by title
    result = lookup_google_books_title(query)
    if result and result.get("title"):
        return result
    
    return None
