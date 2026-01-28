# Digital Library

A personal collection of digital books and documents organized using the **Dewey Decimal Classification (DDC)** system, featuring an advanced, command-line management and reading interface.

## 🚀 Quick Start

The primary tool is `./lib`, which provides interactive search, reading tracking, and note management. 

> **Note:** You do **not** need to manually activate the virtual environment to use `./lib`; it handles it automatically.

```bash
./lib                    # Interactive search (fzf) for all books
```

### Key Features
*   **Unified Interface:** Search, open, and manage notes from one command.
*   **Fuzzy Search:** Instant, type-ahead search powered by `fzf`.
*   **Smart Reading:**
    *   **PDFs:** Opens in **Skim**. Remembers your last page automatically.
    *   **EPUBs:** Opens in **Apple Books**.
*   **Note Synchronization:**
    *   Extracts highlights and notes from Skim (PDF) and Apple Books (EPUB).
    *   Exports them to **Joplin** with full bibliographical metadata (Author, DDC, Subjects).
    *   Prevents duplicates and respects your edits.

---

## 📖 Usage

### Interactive Search (Recommended)
Simply run `./lib` without arguments to launch the interactive browser.
*   **Type** to filter books by title, author, or DDC.
*   **Arrow Keys** to navigate.
*   **Enter** to open the selected book and start/resume reading.

### Command-Line Filtering
You can also filter directly from the command line:

```bash
./lib --ddc 780          # Browse only Music (780)
./lib --type pdf         # Browse only PDFs
./lib --type epub        # Browse only EPUBs
./lib "plato"            # Search for "plato" immediately
```

### Reading & Notes Workflow
1.  **Select a book** using `./lib`.
2.  **Read & Annotate**:
    *   **PDF (Skim):** Use Highlighting (⌘⇧H) and Notes (⌘⇧N). Skim remembers your page.
    *   **EPUB (Apple Books):** Use the native highlight and note tools.
3.  **Finish Session**:
    *   Close the reader (or switch back to the terminal).
    *   Press **Enter** in the terminal window.
    *   The script will scan for new notes, extract them, and sync them to a Joplin note (e.g., "The Line" -> "The Line" note in "Digital Library Notes").

---

## 📚 Library Management

### How to Add Books

**Method 1: Manual Placement (Standard)**
1.  **Place the file** (PDF, EPUB) into the appropriate DDC directory (e.g., `000_Computer_Science/005_Programming/`).
2.  **Update the Catalog**: `./catalog`

**Method 2: Auto-Sort (Intelligent)**
1.  **Drop files** into the `_Inbox/` folder.
2.  **Run Sort**:
    ```bash
    ./sort
    ```
    The script looks up the DDC number via the Open Library API.
    *   **Automated**: If it matches an existing rule, the book is moved immediately.
    *   **Learning**: If a specific DDC is found but no subfolder exists, it will **prompt you** to define a new subcategory (e.g., `841` -> `840_French_Poetry`).
    *   **Persistent**: New rules are saved to `sorting_config.json` and applied automatically next time.
3.  **Update Catalog**: `./catalog`

### File Organization
The library follows the Dewey Decimal Classification (DDC):
*   `000_Computer_Science/`
*   `100_Philosophy/`
*   `200_Religion/`
*   ...and so on.

### Static Table of Contents (`TOC.md`)
The `TOC.md` file provides a static, browseable list of all books. While `./lib` is better for searching, `TOC.md` is useful for browsing the directory structure via a file manager or mobile app (e.g., OneDrive).

---

## ⚙️ Setup & Dependencies

### Requirements
*   **Python 3**
*   **fzf**: Command-line fuzzy finder (`brew install fzf`)
*   **Skim**: PDF Reader (`brew install --cask skim`)
*   **Joplin**: Note-taking app (running with Web Clipper enabled)

### Portable Setup (Multi-Machine Sync)
If you use this library across multiple machines (e.g., via OneDrive, Dropbox, or iCloud), follow these steps to ensure your notes and environments sync correctly:

1.  **Enable Skim Sidecars**: To sync PDF highlights across machines, Skim must save notes to a sidecar file rather than just extended attributes.
    *   **GUI Method**: Go to **Skim Preferences > General** and check **"Automatically save notes sidecar file"**.
    *   **CLI Method**: `defaults write net.sourceforge.skim-app.skim SKAutoSaveNotes -bool YES`
2.  **Machine-Specific Tokens**: Update `config.py` with the unique Joplin Web Clipper tokens for each of your machines. The system will automatically detect which one to use based on your hostname.
3.  **Automatic Environments**: The `./lib` launcher automatically creates and manages machine-specific virtual environments (`.venv_hostname`) to avoid conflicts in cloud-synced folders.

### Troubleshooting
*   **Missing Notes?** Ensure you have saved the PDF in Skim at least once on the source machine to generate the `.skim` sidecar file.
*   **Duplicate Notes in Joplin?** The script features a smart merge logic that compares existing Joplin content with new extractions to prevent duplicates while preserving notes from different machines.

---

*Last Updated: January 2026*