# Digital Library Manager (DLM)

An open-source, command-line toolset for managing, reading, and annotating a personal digital library using the **Dewey Decimal Classification (DDC)** system.

![Digital Library Manager Interface](screenshot.png)

## 🚀 Features

*   **System-Wide CLI:** Just type `dlm` from anywhere to search your library.
*   **Smart Annotation Sync:** Auto-extracts Skim/Apple Books notes to Joplin.
*   **Auto-Sorting:** Organizes books in your library based on DDC subjects.
*   **Robust Configuration:** Supports multiple machines via a single config file.

---

## 🛠️ Installation & Setup

### 1. Prerequisites
*   **Python 3.9+**
*   **poetry** (`brew install poetry`)
*   **fzf** (`brew install fzf`)
*   **Skim** (`brew install --cask skim`)
*   **Joplin** (Running with Web Clipper enabled)

### 2. Install the Package
1.  Clone this repository.
2.  Install using poetry:
    ```bash
    poetry install
    ```
    *Optionally, install system-wide using `pipx install .` if you have `pipx`.*

### 3. Setup Your Library Root
Define where your books and metadata will live:
```bash
export DLM_LIBRARY_ROOT="$HOME/Library/CloudStorage/OneDrive-Personal/Documents/DigitalLibrary"
```

Initialize the structure:
```bash
poetry run dlm-init
```

### 4. Configuration
The `config.py` file is located in your **Library Root**. Edit it to add your Joplin API tokens mapped to your hostnames.

---

## 📖 Usage

| Command | Description |
| :--- | :--- |
| `dlm` | Launch the interactive search & read loop |
| `dlm-sort` | Sort books from `_Inbox` into DDC folders |
| `dlm-catalog` | Refresh the search index (`catalog.json`) |
| `dlm-init` | Initialize a new library structure |

---

## ☁️ Multi-Machine Sync Tips

*   **Sync Data, Not Code:** Keep the library folder in OneDrive/Dropbox. Keep the code in its own Git repo.
*   **Skim Sidecars:** Enable "Automatically save notes sidecar file" in Skim Preferences to sync PDF notes.

---

*License: MIT*
