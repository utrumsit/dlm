# note_extractor.py
"""Annotation extraction utilities.

This module provides thin wrappers that delegate to the reader classes.
"""

from pathlib import Path

from .readers import get_reader


def extract_skim_notes(pdf_path):
    """Extract notes from a PDF using Skim's skimnotes command-line tool.

    This is a thin wrapper that delegates to SkimReader.extract_annotations().

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted notes as text string, or None if not available
    """
    try:
        reader = get_reader("pdf")
        return reader.extract_annotations(Path(pdf_path))
    except NotImplementedError:
        return None


def extract_apple_books_notes(book_title):
    """Extract notes from the Apple Books database for a given book title.

    This is a thin wrapper that delegates to AppleBooksReader.extract_annotations_by_title().

    Args:
        book_title: Title of the book to look up

    Returns:
        Dict with bibliographical_info and notes, or None if not available
    """
    try:
        reader = get_reader("epub")
        return reader.extract_annotations_by_title(book_title)
    except NotImplementedError:
        return None


if __name__ == "__main__":
    # Example usage

    # PDF_FILE = Path('path/to/your/document.pdf')
    # if PDF_FILE.exists():
    #     skim_notes = extract_skim_notes(PDF_FILE)
    #     if skim_notes:
    #         print("--- Skim Notes ---")
    #         print(skim_notes)

    # APPLE_BOOKS_TITLE = "Your Book Title Here"
    # apple_notes = extract_apple_books_notes(APPLE_BOOKS_TITLE)
    # if apple_notes:
    #     print(f"\n--- Apple Books Notes for '{APPLE_BOOKS_TITLE}' ---")
    #     for note in apple_notes:
    #         print(f"Highlight: {note['highlight']}")
    #         print(f"Note: {note['note']}\n")
    pass