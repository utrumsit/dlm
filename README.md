# Digital Library Manager (DLM)

An open-source, command-line toolset for managing, reading, and annotating a personal digital library using the **Dewey Decimal Classification (DDC)** system.

Now featuring an **AI Reading Assistant** that answers questions about the page you are reading in real-time.

![Digital Library Manager Interface](screenshot.png)

## 🚀 Features

*   **System-Wide CLI:** Type `dlm` from anywhere to fuzzy-search your library.
*   **AI Reading Assistant:** Ask "What does this mean?" about your current page (powered by Google Gemini).
*   **Smart Annotation Sync:** Auto-extracts highlights from Skim (PDF) and Apple Books (EPUB) to Joplin.
*   **Auto-Sorting:** Automatically organizes `_Inbox` files into DDC subject folders.
*   **Code/Data Separation:** Your library lives in the cloud (OneDrive/Dropbox); the code lives here.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
*   **macOS** (Required for Skim/AppleScript features)
*   **Python 3.9+**
*   **pipx** (`brew install pipx`) - *Recommended for installing Python tools*
*   **fzf** (`brew install fzf`)
*   **Skim** (`brew install --cask skim`) - *The best PDF reader for macOS*
*   **Joplin** (Running with Web Clipper enabled)

### 2. Install DLM
We recommend installing via `pipx` so the `dlm` command is available everywhere:

```bash
git clone https://github.com/utrumsit/dlm.git
cd dlm
pipx install -e .
```

### 3. Setup Your Library Root
Create a folder for your library (e.g., in OneDrive/Dropbox) and tell DLM where it is.
Add this to your shell profile (`~/.zshrc` or `~/.bash_profile`):

```bash
export DLM_LIBRARY_ROOT="$HOME/Library/CloudStorage/OneDrive-Personal/Documents/DigitalLibrary"
```

Then reload your shell:
```bash
source ~/.zshrc
```

### 4. Initialize & Configure
1.  **Scaffold the folders:**
    ```bash
    dlm-init
    ```
    This creates the `000_...`, `100_...` folders and a `config.py` in your library root.

2.  **Create your local config** (recommended over editing the library root copy):
    ```bash
    mkdir -p ~/.config/dlm
    cp config.py.example ~/.config/dlm/config.py
    ```
    Then edit `~/.config/dlm/config.py`:
    *   Add your **Joplin Web Clipper Token** (Settings → Web Clipper → Advanced Options).
    *   Set up **Google Gemini** for the AI Reading Assistant (choose one):
        *   **OAuth (recommended):** Add your `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` ([create at GCP Console](https://console.cloud.google.com/apis/credentials) — enable "Generative Language API", create Desktop OAuth client), then run `dlm-auth`.
        *   **API key:** Set `GOOGLE_API_KEY` (get one at [Google AI Studio](https://aistudio.google.com/app/apikey)).
    *   Set `SKIM_APP_PATH` if Skim is not at `/Applications/Skim.app`.

    **Config lookup order:** `~/.config/dlm/config.py` (local, preferred) → `$DLM_LIBRARY_ROOT/config.py` (legacy fallback).

    The local path is recommended because API keys and tokens stay on the machine — no risk of syncing secrets to the cloud, and no timeouts from OneDrive/iCloud "Files On-Demand".

---

## 📖 Usage

### Search & Read
Run the main command:
```bash
dlm
```
*   Type to fuzzy search (Title, Author, Subject).
*   Press **Enter** to open the book in Skim (PDF) or Books (EPUB).

### 🤖 AI Reading Assistant
Once a book is open, `dlm` enters **Reading Mode**. You will see a prompt in your terminal:

```text
--- Reading Session: [Book Title] ---
(dlm) > ask Explain this theorem like I'm 5
```
It scrapes the text from the **active Skim page**, sends it to Gemini, and prints the explanation.

### Sync Notes
In the same reading prompt (or via `dlm` search later), you can sync your highlights:
```text
(dlm) > notes
```
This pulls highlights from the PDF and appends them to a note in Joplin.

### Managing the Library
| Command | Description |
| :--- | :--- |
| `dlm-sort` | Scan `_Inbox/`, look up ISBNs/titles, and move files to correct DDC folders. |
| `dlm-catalog` | Rescan all folders and rebuild `catalog.json`. Run this after adding files manually. |
| `dlm-toc` | Generate a `TOC.md` markdown file listing your entire collection. |
| `dlm-auth` | Authenticate with Google via OAuth for the AI Reading Assistant. |

---

## ☁️ Multi-Machine Sync Tips

*   **Sync Data, Not Code:** Keep the library folder in OneDrive/Dropbox. Keep this code repo separate.
*   **Local Config:** Use `~/.config/dlm/config.py` on each machine with that machine's Joplin token and API keys. No hostname dict needed — each machine has its own file.
*   **rclone (recommended):** If OneDrive's macOS app gives you trouble (cloud-only files, timeouts), use `rclone` to sync to a local folder:
    ```bash
    brew install rclone
    rclone config   # one-time setup — authorize with Microsoft
    rclone sync onedrive:Documents/DigitalLibrary /path/to/local/DigitalLibrary
    ```
    Set `DLM_LIBRARY_ROOT` to the local path. Use a cron job or launchd plist to sync periodically.
*   **Skim Sidecars:** Enable "Automatically save notes sidecar file" in Skim Preferences to sync PDF highlights across devices.

---

*License: MIT*
