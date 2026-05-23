# Digital Library Manager (DLM)

A cross-platform, command-line toolset for managing, reading, and annotating a personal digital library using the **Dewey Decimal Classification (DDC)** system.

Now featuring an **AI Reading Assistant** that answers questions about selected text in real-time (powered by Google Gemini via OAuth or API key).

![Digital Library Manager Interface](screenshot.png)

## Features

*   **System-Wide CLI:** Type `dlm` from anywhere to fuzzy-search your library.
*   **AI Reading Assistant:** Select text in your reader, copy it, then run `dlm ask "what does this mean?"` — DLM sends the selection to Gemini and prints the answer.
*   **Smart Annotation Sync:** Auto-extracts highlights from Skim (macOS PDF), Sioyek (Linux/macOS PDF), and Foliate (Linux EPUB) to Joplin, with intelligent dedup.
*   **Auto-Sorting:** Automatically organizes `_Inbox` files into DDC subject folders.
*   **Code/Data Separation:** Your library lives wherever you want (local, OneDrive, Dropbox); the code lives here.
*   **Cross-Platform:** Runs on macOS and Linux.

---

## Installation & Setup

### Prerequisites

#### macOS
```bash
brew install pipx fzf poppler exiftool
# Recommended (optional):
#   Skim (PDF reader):      brew install --cask skim
#   Joplin (note sync):     brew install --cask joplin
```

#### Linux (Debian / Ubuntu)
```bash
sudo apt install pipx fzf poppler-utils libimage-exiftool-perl xclip
# Recommended (optional):
#   sioyek  (PDF reader):   sudo apt install sioyek
#   Foliate (EPUB reader):  sudo apt install foliate
#   Joplin (note sync):     install script at https://joplinapp.org/help/install
```

#### Linux (Arch)
```bash
sudo pacman -S python-pipx fzf poppler perl-image-exiftool xclip
# Recommended (optional):
#   sioyek  (PDF reader):  AUR — e.g. yay -S sioyek
#   Foliate (EPUB reader): sudo pacman -S foliate
#   Joplin (note sync):    AUR — e.g. yay -S joplin-desktop
```

#### Common (all platforms)
```bash
git clone https://github.com/utrumsit/dlm.git
cd dlm
pipx install -e .
```

This installs the following commands system-wide:

| Command | Description |
| :--- | :--- |
| `dlm` | Fuzzy-search your library and open books |
| `dlm-catalog` | Rescan all folders and rebuild `catalog.json`. Run after adding files. |
| `dlm-sort` | Scan `_Inbox/`, look up ISBNs/titles, and move files to correct DDC folders. |
| `dlm-init` | Scaffold the DDC directory structure and a starter config. |
| `dlm-toc` | Generate a `TOC.md` markdown file listing your entire collection. |
| `dlm-auth` | Authenticate with Google via OAuth for the AI Reading Assistant. |
| `dlm-config` | View, check, or edit config (`show`, `check`, `set`, `migrate`). |
| `dlm-doctor` | Diagnose your installation (checks all tools, readers, services). |
| `dlm-metafix` | Scan and fix metadata for existing books (title, author, ISBN). |

### First-Run Setup

1.  **Set your library root** (add to `~/.zshrc` or `~/.bashrc`):
    ```bash
    export DLM_LIBRARY_ROOT="/path/to/your/DigitalLibrary"
    ```
    Then reload: `source ~/.zshrc`

2.  **Scaffold the folder structure** (first time only):
    ```bash
    dlm-init
    ```

3.  **Configure DLM:**
    ```bash
    dlm-config check    # shows defaults, offers to write config.toml
    ```
    Then edit `~/.config/dlm/config.toml`:
    *   **Joplin:** Add your Web Clipper token.
    *   **Gemini AI** (choose one):
        *   **OAuth (recommended):** Add `llm.gemini.client_id` and `client_secret`, then run `dlm-auth`.
        *   **API key:** Set `llm.gemini.api_key` or the `GOOGLE_API_KEY` env var.
    *   **Readers:** Set `readers.pdf` / `readers.epub` if you want to override platform defaults.

    **Upgrading from config.py?** Run `dlm-config migrate` to auto-convert.

4.  **Build the catalog:**
    ```bash
    dlm-catalog
    ```

5.  **Verify your setup:**
    ```bash
    dlm-doctor
    ```

---

## Usage

### Search & Read
```bash
dlm
```
*   Type to fuzzy-search by title, author, subject, or filename.
*   Press **Enter** to open in your configured reader (Skim, Sioyek, Foliate, etc.).
*   Use `--ddc 780` to filter by DDC category, `--type pdf` for file type.

### AI Reading Assistant

Select text in your reader (Ctrl/Cmd+C), then ask a question:

```bash
dlm ask "explain this in simple terms"
```

Context sources (in priority order):
*   `--file PATH` — read context from a file
*   `cat notes.txt | dlm ask "summarize"` — piped stdin
*   Clipboard — whatever you last copied

You can also use it inside Reading Mode after opening a book:
```text
(dlm) > ask What is the main argument here?
```

### Sync Notes
In the reading prompt, sync highlights to Joplin:
```text
(dlm) > notes
```
Pulls highlights from your reader and appends them to a Joplin notebook. Only **new** highlights are synced (tracked per book).

### Retroactive Metadata Fixing
Scan and fix metadata for existing books:
```bash
dlm-metafix --dry-run       # safe preview
dlm-metafix --yes           # apply all
```

### Configuration Reference
```bash
dlm config show    # all keys with values and sources (env / file / default)
dlm config check   # diff against schema, offer to fill missing keys
dlm config set joplin.token abc123    # set a value by dotted path
dlm config migrate # convert legacy config.py → config.toml
```
Full key reference: see `config.toml.example`.

---

## Multi-Machine Sync

*   **Sync Data, Not Code:** Keep your library folder in OneDrive/Dropbox (or sync with rclone). Keep this code repo separate.
*   **Config is Per-Machine:** Each machine has its own `~/.config/dlm/config.toml` with machine-specific tokens and paths. Never sync this file.
*   **rclone (recommended over OneDrive app):** OneDrive's filesystem driver often shows files as "local" but can't actually read them. Use rclone to sync to a real local folder:
    ```bash
    rclone sync onedrive:Documents/DigitalLibrary /path/to/local/DigitalLibrary
    ```
    Set `DLM_LIBRARY_ROOT` to the local path.
*   **Skim Sidecars (macOS):** In Skim Preferences, enable **"Automatically save notes sidecar file"** so `.skim` annotation files sync across machines.

---

## Project Structure

```
dlm/
├── src/dlm/
│   ├── auth/            # Google OAuth2 flow for Gemini
│   │   └── __init__.py
│   ├── llm/             # LLM backend abstraction (v1: Gemini only)
│   │   ├── base.py      # LLMBackend abstract class
│   │   ├── gemini.py    # Gemini implementation
│   │   └── __init__.py  # get_backend() dispatcher
│   ├── readers/         # Reader abstraction (PDF + EPUB)
│   │   ├── base.py      # Reader abstract class + Highlight dataclass
│   │   ├── skim.py      # Skim (macOS PDF)
│   │   ├── apple_books.py  # Apple Books (macOS EPUB)
│   │   ├── sioyek.py    # Sioyek (Linux/macOS PDF)
│   │   ├── foliate.py   # Foliate (Linux EPUB)
│   │   └── __init__.py  # get_reader() dispatcher
│   ├── catalog.py       # Library scanner, metadata extraction
│   ├── cli.py           # Main CLI entry point and reading mode
│   ├── config_cli.py    # dlm-config subcommands
│   ├── config_schema.py # TOML config dataclass schema
│   ├── data.py          # Catalog and progress file I/O
│   ├── doctor.py        # dlm-doctor diagnostic command
│   ├── extractor.py     # Thin wrappers for reader annotations
│   ├── fzf.py           # fzf interactive search interface
│   ├── init.py          # Library scaffolding
│   ├── joplin.py        # Joplin Web Clipper integration
│   ├── lookup.py        # Metadata lookup (ISBN, OpenLibrary, Google Books)
│   ├── metafix.py       # Retroactive metadata fixer
│   ├── opener.py        # File opening (delegates to readers/)
│   ├── settings.py      # Config loading (TOML + legacy Python)
│   ├── sort.py          # Inbox auto-sorting
│   ├── sync_state.py    # Joplin highlight sync tracking
│   └── toc.py           # Table of contents generator
├── config.toml.example  # TOML config template (recommended)
├── config.py.example    # Python config template (deprecated, auto-migrates)
├── pyproject.toml       # Dependencies and entry points
└── README.md
```

---

*License: MIT*
