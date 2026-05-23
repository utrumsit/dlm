# AGENTS.md - Digital Library Manager (DLM)

## Multi-Machine Directory
This code directory is synced via **Syncthing** across multiple machines (macOS + Linux). Any agent reading this file may be on any of them. Detect the current host with `hostname -s` or `platform.node().split('.')[0]` before making machine-specific assumptions.

**Machine-specific notes:** if `AGENTS.local.md` exists alongside this file, read it for host-by-host details (reader paths, per-machine quirks). That file is gitignored but Syncthing-replicated.

### What Syncs (and What Doesn't)
- **Synced (Syncthing):** All code in `src/dlm/`, `pyproject.toml`, `poetry.lock`, `AGENTS.md`, `.stignore`, `README.md`
- **NOT synced (`.stignore`):** `.venv*/`, `__pycache__/`, `dist/`, `build/`, `.DS_Store`, editor configs
- **NOT synced (local per-machine):** `~/.config/dlm/config.toml`, Poetry virtualenvs
- **Separate sync (OneDrive via rclone):** Library data at `DLM_LIBRARY_ROOT` — books, `catalog.json`, `reading_progress.json`

### Setup on a New/Refreshed Machine
1. Syncthing delivers the code automatically
2. Create local config: `mkdir -p ~/.config/dlm && cp config.toml.example ~/.config/dlm/config.toml` — then edit with machine-specific values
3. (Optional) If a legacy `config.py` exists, run `dlm-config migrate` to auto-convert to TOML
4. Set `DLM_LIBRARY_ROOT` in your shell profile
5. `pipx install -e .` or `poetry install`
6. Verify: `dlm-doctor`

## What This Is
A cross-platform CLI toolset for managing a personal digital library using Dewey Decimal Classification (DDC). Search via fzf, open PDFs in Skim (macOS) or Sioyek (Linux), EPUBs in Apple Books (macOS) or Foliate (Linux), extract annotations, and sync notes to Joplin.

## Architecture: Code vs Data
**Critical concept:** The code repo and the library data are separate. The code lives here (synced by Syncthing). The actual books, catalog, and config live at `DLM_LIBRARY_ROOT` (synced separately via OneDrive/rclone).

- **Code (this directory):** `src/dlm/` — the Python package
- **Data (`DLM_LIBRARY_ROOT`):** DDC folders (`000_Computer_Science/`, etc.), `catalog.json`, `reading_progress.json`, `_Inbox/`
- **Config (`~/.config/dlm/config.toml`):** Local per-machine. Joplin tokens, reader paths, Google API credentials. Never synced.

Never hardcode paths to the library. Always use `LIBRARY_ROOT` from `settings.py`.

## Architecture: Key Abstractions

### Readers (`src/dlm/readers/`)
Platform-agnostic reader abstraction. Each reader implements `Reader` (abstract base class):
- `open(path, page)` — launch the reader app with the file
- `extract_annotations(path)` → `list[Highlight]` — extract highlights/notes
- `is_available()` — check if the reader binary exists

`get_reader(file_type)` dispatches based on config + platform:
- PDF: SkimReader (macOS) / SioyekReader (Linux)
- EPUB: AppleBooksReader (macOS) / FoliateReader (Linux)
- Config override: `readers.pdf = "sioyek"` etc.

### LLM Backends (`src/dlm/llm/`)
Pluggable LLM backend abstraction. Each backend implements `LLMBackend`:
- `ask(context, question)` → `str` — send a question about context text

`get_backend()` dispatches based on `llm.backend` config (default: "gemini").
v1 ships only `GeminiBackend`. Other backends can be added later.

### Config (`settings.py` + `config_schema.py`)
TOML config at `~/.config/dlm/config.toml`. Schema defined as dataclasses in `config_schema.py`. Settings exported as module-level names via `__getattr__` for backward compatibility. Legacy `config.py` auto-migrates on first run.

## Module Map
| Module | Purpose |
|--------|---------|
| `cli.py` | Main entry point (`dlm`). Search, open, reading mode, `ask` subcommand |
| `config_cli.py` | `dlm config` subcommands: show, check, set, migrate |
| `config_schema.py` | TOML config dataclass schema + dotted-path navigation |
| `settings.py` | Config loading (TOML first, legacy Python fallback), env overrides |
| `doctor.py` | `dlm-doctor` diagnostic command (11 checks) |
| `fzf.py` | Interactive fzf-based search with preview panel |
| `opener.py` | Unified file opener — delegates to `readers/` package |
| `readers/` | Reader abstraction (Skim, Apple Books, Sioyek, Foliate) |
| `llm/` | LLM backend abstraction (v1: Gemini only) |
| `auth/` | Google OAuth2 flow for Gemini |
| `data.py` | Shared data access — `load_catalog()`, `load_progress()`, `save_progress()` |
| `catalog.py` | Scans library folders, extracts PDF/EPUB metadata, builds `catalog.json` |
| `sort.py` | Auto-sorts `_Inbox/` files using Open Library DDC lookup |
| `extractor.py` | Thin wrappers delegating to reader classes |
| `sync_state.py` | Tracks which highlight IDs have been synced to Joplin |
| `joplin.py` | Joplin Web Clipper API client with smart note merging |
| `toc.py` | Generates `TOC.md` from library structure |
| `init.py` | Scaffolds a new library with DDC folders |
| `lookup.py` | Shared metadata lookup (ISBN, OpenLibrary, Google Books) |
| `metafix.py` | Retroactive metadata fixer CLI |

## Entry Points (pyproject.toml)
| Command | Module |
|---------|--------|
| `dlm` | `cli:main` |
| `dlm ask "question"` | `cli:main` (subcommand, clipboard/file/stdin) |
| `dlm-catalog` | `catalog:main` |
| `dlm-sort` | `sort:main` |
| `dlm-toc` | `toc:main` |
| `dlm-init` | `init:main` |
| `dlm-auth` | `auth:auth_command` |
| `dlm-config` | `config_cli:main` |
| `dlm-doctor` | `doctor:main` |
| `dlm-metafix` | `metafix:main` |

## Package Manager
**Poetry** (or pipx for end-users). Virtualenvs live in Poetry's cache, NOT in-project. This avoids Syncthing conflicts between machines.

- `poetry install` — set up on a new machine
- `poetry run dlm` — run without activating venv
- `pipx install -e .` — end-user install (system-wide commands)

## Configuration (`~/.config/dlm/config.toml`)
This file is **local per machine** — never synced. TOML format with sections:

| Section | Key | Purpose |
|---------|-----|---------|
| `[joplin]` | `token`, `api_url`, `notebook_name` | Joplin Web Clipper |
| `[llm]` | `backend` | LLM backend (default: "gemini") |
| `[llm.gemini]` | `api_key`, `client_id`, `client_secret` | Google Gemini credentials |
| `[readers]` | `pdf`, `epub` | Reader override (empty = platform default) |
| `[skim]` | `app_path` | Skim.app bundle path (macOS) |
| `[sioyek]` | `binary`, `shared_db` | Sioyek binary and highlights DB |
| `[foliate]` | `binary`, `library_dir` | Foliate binary and library directory |

Legacy `config.py` users: run `dlm-config migrate` to auto-convert.

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
- Per-machine setup TODOs (e.g. unfilled tokens) live in `AGENTS.local.md`, not here

## Testing
No test suite yet. `test_lookup.py` is a manual one-off script for Open Library API testing.

## Environment Requirements
- **macOS (Darwin):** Skim, Apple Books, AppleScript for context extraction
- **Linux:** Sioyek (PDF), Foliate (EPUB), xclip/wl-clipboard
- **Both:** Python 3.9+, `fzf`, `pdfinfo` (poppler), Joplin (optional, for note sync)
- **Syncthing** for code sync between machines
