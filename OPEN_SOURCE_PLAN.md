# Plan: Open Sourcing "Dewey-CLI"

This document outlines the steps required to decouple the code (the engine) from the personal library data (the fuel) to make this project public on GitHub.

## Phase 1: Sanitize & Configure
**Goal:** Ensure no secrets or hardcoded paths exist in the codebase.

1.  **Isolate Configuration:**
    *   Create `config.py.example` with placeholder values (tokens, URLs).
    *   Ensure the real `config.py` is ignored by Git.
2.  **Path Audit:**
    *   Replace all absolute paths (e.g., `/Users/karlschudt`) with `Path.home()` or `Path(__file__).parent`.
3.  **Machine Anonymization:**
    *   The `lib` launcher and `config.py` already use `hostname` for portability. Ensure these logic blocks remain generic.

## Phase 2: The Firewall (.gitignore)
**Goal:** Prevent book files, databases, and logs from being tracked by Git.

Create a `.gitignore` file with the following:

```gitignore
# Python Artifacts
__pycache__/
*.pyc
.venv/
.venv_*
.env

# Configuration
config.py

# Library Content (DDC Folders)
[0-9][0-9][0-9]_*/
Personal/
My_Research/
MCI/
_Inbox/

# User-specific Book Metadata
*.skim
*.txt

# Generated Database & Indexes
catalog.json
reading_progress.json
notes_sync.json
TOC.md
.fzf_preview.py
.fzf_preview.sh

# System Files
.DS_Store
```

## Phase 3: Setup & Dependencies
**Goal:** Make it easy for others to install.

1.  **Requirements File:**
    *   Document `requests` as the core dependency.
2.  **Initialization Script:**
    *   Create `init_library.py` to generate the empty DDC folder structure (000-900) and an initial `config.py` from the template.

## Phase 4: Documentation (README)
**Goal:** Generalize for public consumption.

1.  **Multi-Machine Support**: Highlight the ability to sync via cloud storage (OneDrive/Dropbox) while maintaining separate environments and tokens.
2.  **Skim Integration**: Explicitly document the "Save Sidecar" preference for PDF note portability.

## Phase 5: Release
1.  **License:** Add an `LICENSE` (MIT recommended).
2.  **Security Check:** Perform a final search for any hardcoded personal identifiers or credentials.
