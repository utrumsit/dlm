# Digital Library Manager (DLM)

An open-source, command-line toolset for managing, reading, and annotating a personal digital library using the **Dewey Decimal Classification (DDC)** system.

It bridges the gap between your filesystem (PDFs/EPUBs), your reading tools (Skim/Apple Books), and your knowledge base (Joplin).

## 🚀 Features

*   **Fuzzy Search:** Instant access to your collection via `./lib` (powered by `fzf`).
*   **Smart Annotation Sync:**
    *   **PDFs:** Opens in **Skim**. Highlights/notes are auto-extracted to Joplin.
    *   **EPUBs:** Opens in **Apple Books**. Highlights/notes are auto-extracted to Joplin.
*   **Auto-Sorting:** Drop books in `_Inbox`, run `./sort`, and let the tool organize them by DDC subject (fetched from Open Library).
*   **Portable Architecture:** Keep your code in one place (e.g., `~/bin/dlm`) and your library in the cloud (e.g., OneDrive/Dropbox). Machine-specific configs prevent sync conflicts.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
*   **Python 3**
*   **fzf** (`brew install fzf`)
*   **Skim** (`brew install --cask skim`)
*   **Joplin** (Running with Web Clipper enabled)

### 2. Setup Your Library

**Option A: Self-Contained (Code & Books Together)**
Good for simple, single-machine setups.

1.  Clone this repository.
2.  Initialize the folder structure:
    ```bash
    python3 init_library.py
    ```
3.  This creates the DDC folders (`000_...` to `900_...`), `_Inbox`, and `config.py`.

**Option B: Split Setup (Recommended for Cloud Sync)**
Keep this code separate from your heavy book files (useful for OneDrive/Dropbox users).

1.  Clone this repository to a stable location (e.g., `~/dev/dlm`).
2.  Create your library folder (e.g., `~/OneDrive/Library`).
3.  Initialize it:
    ```bash
    export DLM_LIBRARY_ROOT="$HOME/OneDrive/Library"
    python3 /path/to/dlm/init_library.py
    ```

### 3. Configuration
1.  Open `config.py` (in your library folder).
2.  Get your Joplin Web Clipper token (Joplin -> Settings -> Web Clipper).
3.  Add it to the `JOPLIN_TOKENS` dictionary, mapped to your hostname (run `hostname -s` to check).

---

## 📖 Usage

**Note:** The tools automatically manage their own Python virtual environments. You don't need to manually activate anything.

If you are using **Option B (Split Setup)**, you must define the root before running commands (or add an alias to your shell profile):
```bash
export DLM_LIBRARY_ROOT="$HOME/OneDrive/Library"
```

### Search & Read
```bash
./lib                    # Interactive search
./lib --ddc 780          # Browse Music
./lib --recent           # Continue reading recent books
```

### Manage
1.  **Add Books:** Drop files into `_Inbox`.
2.  **Sort:**
    ```bash
    ./sort      # Auto-identifies and moves books to DDC folders
    ```
3.  **Index:**
    ```bash
    ./catalog   # Updates the search index (catalog.json)
    ```

---

## ☁️ Multi-Machine Sync Tips

1.  **Skim Sidecars:** To sync PDF highlights across machines, enable "Automatically save notes sidecar file" in **Skim Preferences > General**.
2.  **Machine-Specific Config:** The `config.py` file supports multiple hostnames, so you can commit/sync it safely without leaking secrets or breaking paths on other devices.

---

*License: MIT*
