# note_extractor.py

import glob
import platform
import sqlite3
import subprocess
from pathlib import Path

def extract_skim_notes(pdf_path):
    """Extract notes from a PDF using Skim's skimnotes command-line tool.
    Checks both extended attributes and .skim sidecar files.
    """
    if platform.system() != "Darwin":
        return None

    try:
        skimnotes_path = "/Applications/Skim.app/Contents/SharedSupport/skimnotes"
        if not Path(skimnotes_path).exists():
            print("skimnotes tool not found.")
            return None

        # 1. Try to get from extended attributes first
        result = subprocess.run(
            [skimnotes_path, "get", "-format", "text", str(pdf_path), "-"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout

        # 2. If empty, check for a .skim sidecar file
        sidecar_path = Path(pdf_path).with_suffix(".skim")
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


def extract_apple_books_notes(book_title):
    """Extract notes from the Apple Books database for a given book title."""
    if platform.system() != "Darwin":
        return None

    base_path_annotation = (
        Path.home()
        / "Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/"
    )
    db_files_annotation = glob.glob(str(base_path_annotation / "AEAnnotation*.sqlite"))

    base_path_library = (
        Path.home() / "Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/"
    )
    db_files_library = glob.glob(str(base_path_library / "BKLibrary-1-*.sqlite"))

    if not db_files_annotation or not db_files_library:
        print("Apple Books database(s) not found.")
        return None

    db_path_annotation = db_files_annotation[0]  # Use the first match
    db_path_library = db_files_library[0]  # Use the first match
    print(f"Found Apple Books annotation database at: {db_path_annotation}")
    print(f"Found Apple Books library database at: {db_path_library}")

    notes = []
    try:
        con_annotation = sqlite3.connect(f"file:{db_path_annotation}?mode=ro", uri=True)
        con_library = sqlite3.connect(f"file:{db_path_library}?mode=ro", uri=True)
        cur_annotation = con_annotation.cursor()
        cur_library = con_library.cursor()

        # Find the asset ID and bibliographical info for the given book title
        cur_library.execute(
            """
            SELECT ZASSETID, ZTITLE, ZAUTHOR, ZBOOKDESCRIPTION, ZGENRE, ZLANGUAGE, ZPAGECOUNT, ZRELEASEDATE 
            FROM ZBKLIBRARYASSET WHERE ZTITLE = ?
        """,
            (book_title,),
        )
        asset_info = cur_library.fetchone()

        if not asset_info:
            # Let's try a fuzzy match if the exact title fails
            cur_library.execute(
                """
                SELECT ZASSETID, ZTITLE, ZAUTHOR, ZBOOKDESCRIPTION, ZGENRE, ZLANGUAGE, ZPAGECOUNT, ZRELEASEDATE 
                FROM ZBKLIBRARYASSET WHERE ZTITLE LIKE ?
            """,
                (f"%{book_title}%",),
            )
            asset_info = cur_library.fetchone()

        if not asset_info:
            print(f"Book '{book_title}' not found in Apple Books database.")
            con_annotation.close()
            con_library.close()
            return None

        (
            asset_id,
            found_title,
            found_author,
            description,
            genre,
            language,
            page_count,
            release_date,
        ) = asset_info

        bibliographical_info = {
            "title": found_title,
            "author": found_author,
            "description": description,
            "genre": genre,
            "language": language,
            "page_count": page_count,
            "release_date": release_date,
        }

        # Query for annotations
        query = """
        SELECT
            ZANNOTATIONREPRESENTATIVETEXT,
            ZANNOTATIONSELECTEDTEXT,
            ZANNOTATIONNOTE,
            ZANNOTATIONMODIFICATIONDATE
        FROM ZAEANNOTATION
        WHERE ZANNOTATIONASSETID = ? AND ZANNOTATIONDELETED = 0
        ORDER BY ZANNOTATIONMODIFICATIONDATE
        """

        for row in cur_annotation.execute(query, (asset_id,)):
            representative_text, selected_text, note, modification_date = row
            text_to_use = selected_text or representative_text or ""
            note_text = note or ""
            if text_to_use or note_text:
                notes.append(
                    {
                        "highlight": text_to_use.strip(),
                        "note": note_text.strip(),
                        "modification_date": modification_date,
                    }
                )

        con_annotation.close()
        con_library.close()

        return {"bibliographical_info": bibliographical_info, "notes": notes}

    except sqlite3.OperationalError as e:
        print(f"Error accessing Apple Books database: {e}")
        print("Please ensure Apple Books is closed and try again.")
        return None
    except Exception as e:
        print(f"An error occurred while extracting Apple Books notes: {e}")
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
