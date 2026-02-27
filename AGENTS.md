# AGENTS.md - Digital Library Manager (DLM)

## ⚠️ Multi-Machine Directory
This code directory is synced via **Syncthing** across three machines. Any agent reading this file may be on any of them. Detect the current host with `hostname -s` or `platform.node().split('.')[0]` before making machine-specific assumptions.

| Hostname | Machine | Skim Path | Notes |
|----------|---------|-----------|-------|
| `Karls-MacBook-Pro` | MacBook Pro | `/Applications/Skim.app` | |
| `Karls-Mac-mini` | Mac mini | `/Applications/Skim.app` | |
| `JOSEPHs-iMac` | M1 iMac | `/Volumes/frodo/Applications/Skim.app` | Homebrew cask apps install to `/Volumes/frodo/` |

### What Syncs (and What Doesn't)
- **Synced (Syncthing):** All code in `src/dlm/`, `pyproject.toml`, `poetry.lock`, `AGENTS.md`, `.stignore`, `README.md`
- **NOT synced (`.stignore`):** `.venv*/`, `__pycache__/`, `dist/`, `build/`, `.DS_Store`, editor configs
- **NOT synced (local per-machine):** `~/.config/dlm/config.py`, Poetry virtualenvs (in `~/Library/Caches/pypoetry/virtualenvs/`)
- **Separate sync (OneDrive via rclone):** Library data at `DLM_LIBRARY_ROOT` — books, `catalog.json`, `reading_progress.json`

### Setup on a New/Refreshed Machine
1. Syncthing delivers the code automatically
2. Create local config: `mkdir -p ~/.config/dlm && cp config.py.example ~/.config/dlm/config.py` — then edit with machine-specific values (Joplin token, Skim path, Google credentials)
3. Set `DLM_LIBRARY_ROOT` in your shell profile (points to the OneDrive-synced library)
4. `poetry install` (creates a venv in Poetry's cache, not in-project)
5. Verify: `poetry run dlm --help`

## What This Is
A CLI toolset for managing a personal digital library using Dewey Decimal Classification (DDC). Search via fzf, open PDFs in Skim / EPUBs in Apple Books, extract annotations, and sync notes to Joplin.

## Architecture: Code vs Data
**Critical concept:** The code repo and the library data are separate. The code lives here (synced by Syncthing). The actual books, catalog, and config live at `DLM_LIBRARY_ROOT` (synced separately via OneDrive/rclone).

- **Code (this directory):** `src/dlm/` — the Python package
- **Data (`DLM_LIBRARY_ROOT`):** DDC folders (`000_Computer_Science/`, etc.), `catalog.json`, `reading_progress.json`, `_Inbox/`
- **Config (`~/.config/dlm/config.py`):** Local per-machine. Joplin tokens, Skim path, Google API credentials. Never synced.

Never hardcode paths to the library. Always use `LIBRARY_ROOT` from `settings.py`.

## Module Map
| Module | Purpose |
|--------|---------|
| `cli.py` | Main entry point (`dlm`). Search, open files, export notes to Joplin |
| `fzf.py` | Interactive fzf-based search with preview panel |
| `opener.py` | Unified file opener — Skim for PDFs, Apple Books for EPUBs, system default for others. Progress tracking. |
| `data.py` | Shared data access — `load_catalog()`, `load_progress()`, `save_progress()` |
| `catalog.py` | Scans library folders, extracts PDF/EPUB metadata, builds `catalog.json` |
| `sort.py` | Auto-sorts `_Inbox/` files using Open Library DDC lookup |
| `settings.py` | Loads config: `~/.config/dlm/config.py` first, falls back to `DLM_LIBRARY_ROOT/config.py` (legacy). Defines `LIBRARY_ROOT` and all settings. |
| `extractor.py` | Extracts annotations from Skim (PDF) and Apple Books (EPUB) |
| `joplin.py` | Joplin Web Clipper API client with smart note merging |
| `toc.py` | Generates `TOC.md` from library structure |
| `init.py` | Scaffolds a new library with DDC folders |
| `context.py` | Reading context extraction (Skim active page scraping) |
| `llm.py` | Gemini API client for reading assistant |
| `auth.py` | Google OAuth2 flow for Gemini (alternative to API key) |

## Entry Points (pyproject.toml)
| Command | Module |
|---------|--------|
| `dlm` | `cli:main` |
| `dlm ask "question"` | `cli:main` (subcommand) |
| `dlm-catalog` | `catalog:main` |
| `dlm-sort` | `sort:main` |
| `dlm-toc` | `toc:main` |
| `dlm-init` | `init:main` |
| `dlm-auth` | `auth:auth_command` |

## Package Manager
**Poetry.** Virtualenvs live in Poetry's cache (`~/Library/Caches/pypoetry/virtualenvs/`), NOT in-project. This avoids Syncthing conflicts between machines.

- `poetry install` — set up on a new machine
- `poetry run dlm` — run without activating venv
- `poetry shell` — activate venv interactively

## Configuration (`~/.config/dlm/config.py`)
This file is **local per machine** — never synced. Settings loaded by `settings.py`:

| Setting | Purpose | Machine-specific? |
|---------|---------|-------------------|
| `JOPLIN_TOKEN` | Web Clipper API token (keyed by hostname) | Yes |
| `JOPLIN_API_URL` | Joplin API endpoint (default `http://localhost:41184`) | No |
| `JOPLIN_NOTEBOOK_NAME` | Target notebook for note export | No |
| `SKIM_APP_PATH` | Path to Skim.app (varies by machine — see table above) | Yes |
| `GOOGLE_API_KEY` | Gemini API key (or use env var) | No |
| `GOOGLE_CLIENT_ID` | OAuth client ID (for `dlm-auth`) | No |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret (for `dlm-auth`) | No |

## DDC Folder Convention
Top-level folders follow `NNN_Name` pattern matching Dewey centuries:
```
000_Computer_Science, 100_Philosophy, 200_Religion, 300_Social_Sciences,
400_Language, 500_Science, 600_Technology, 700_Arts, 800_Literature, 900_History
```
Subcategories nest inside: e.g., `700_Arts/780_Music/781.65_Jazz/`

New categories must be added to **both** `CATEGORY_INFO` (top-level) or `DDC_SUBCATEGORIES` (nested) in `catalog.py`, **and** to `init.py` if they should be created on first run.

## Known Issues / Tech Debt
- No graceful handling when `catalog.json` doesn't exist (crashes; should suggest running `dlm-catalog`)
- No test suite beyond `test_lookup.py` (manual one-off)
- `JOSEPHs-iMac` Joplin token not yet configured

## Testing
No test suite yet. `test_lookup.py` is a manual one-off script for Open Library API testing.

## Environment Requirements
- macOS (Darwin) — uses Skim, Apple Books, AppleScript
- Python 3.9+
- `fzf`, `pdfinfo` (from poppler) on PATH
- Joplin running with Web Clipper enabled (for note sync)
- Syncthing for code sync between machines
