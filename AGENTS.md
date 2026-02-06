# AGENTS.md - Digital Library Manager (DLM)

## What This Is
A CLI toolset for managing a personal digital library using Dewey Decimal Classification (DDC). Search via fzf, open PDFs in Skim / EPUBs in Apple Books, extract annotations, and sync notes to Joplin.

## Architecture: Code vs Data
**Critical concept:** The code repo and the library data are separate. The code lives here in git. The actual books, catalog, and config live at `DLM_LIBRARY_ROOT` (typically a cloud-synced folder like OneDrive).

- **Code (this repo):** `src/dlm/` — the Python package
- **Data (`DLM_LIBRARY_ROOT`):** DDC folders (`000_Computer_Science/`, etc.), `catalog.json`, `reading_progress.json`, `config.py`, `_Inbox/`

Never hardcode paths to the library. Always use `LIBRARY_ROOT` from `settings.py`.

## Module Map
| Module | Purpose |
|--------|---------|
| `cli.py` | Main entry point (`dlm`). Search, open files, export notes to Joplin |
| `fzf.py` | Interactive fzf-based search with preview panel |
| `opener.py` | **Unified file opener** — Skim for PDFs, Apple Books for EPUBs, system default for others. Progress tracking. |
| `data.py` | Shared data access — `load_catalog()`, `load_progress()`, `save_progress()` |
| `catalog.py` | Scans library folders, extracts PDF/EPUB metadata, builds `catalog.json` |
| `sort.py` | Auto-sorts `_Inbox/` files using Open Library DDC lookup |
| `settings.py` | Loads config dynamically from `DLM_LIBRARY_ROOT/config.py`, defines paths |
| `extractor.py` | Extracts annotations from Skim (PDF) and Apple Books (EPUB) |
| `joplin.py` | Joplin Web Clipper API client with smart note merging |
| `toc.py` | Generates `TOC.md` from library structure |
| `init.py` | Scaffolds a new library with DDC folders |

## Entry Points (pyproject.toml)
| Command | Module |
|---------|--------|
| `dlm` | `cli:main` |
| `dlm-catalog` | `catalog:main` |
| `dlm-sort` | `sort:main` |
| `dlm-toc` | `toc:main` |
| `dlm-init` | `init:main` |

## Package Manager
**Poetry.** Use `poetry install` to set up, `poetry run dlm` to run without activating venv.

## Multi-Machine Setup
- `config.py` lives in the library root (synced via cloud), not in the code repo
- Joplin tokens are keyed by hostname: `platform.node().split('.')[0]`
- Virtual environments use `.venv_<hostname>` naming to avoid cloud sync conflicts

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

## Testing
No test suite yet. `test_lookup.py` is a manual one-off script for Open Library API testing.

## Environment Requirements
- macOS (Darwin) — uses Skim, Apple Books, AppleScript
- Python 3.9+
- `fzf`, `pdfinfo` (from poppler) on PATH
- Joplin running with Web Clipper enabled (for note sync)
