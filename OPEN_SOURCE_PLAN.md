# Plan: Open Sourcing "Dewey-CLI"

This document outlines the steps required to decouple the code (the engine) from the personal library data (the fuel) to make this project public on GitHub.

## Phase 1: Sanitize & Configure ✅
**Goal:** Ensure no secrets or hardcoded paths exist in the codebase.

1.  **Isolate Configuration:** ✅
    *   `config.toml.example` with placeholder values (TOML format, recommended).
    *   `config.py.example` (deprecated, auto-migrates to TOML).
    *   Real config is local per-machine at `~/.config/dlm/config.toml`.
2.  **Path Audit:** ✅
    *   All paths use `Path.home()`, `LIBRARY_ROOT`, or XDG dirs.
3.  **Machine Anonymization:** ✅
    *   Config is per-machine (no hostname dict needed).

## Phase 2: The Firewall (.gitignore) ✅
**Goal:** Prevent book files, databases, and logs from being tracked by Git.

Create a `.gitignore` file. Library data, config, and generated files are excluded.

## Phase 3: Setup & Dependencies ✅
**Goal:** Make it easy for others to install.

1.  **pipx install:** ✅ `pipx install -e .` installs all entry points system-wide.
2.  **Initialization Script:** ✅ `dlm-init` scaffolds DDC folders and starter config.

## Phase 4: Documentation (README) ✅
**Goal:** Generalize for public consumption.

1.  **Cross-Platform:** ✅ macOS + Linux install instructions.
2.  **Multi-Machine Support:** ✅ Config is per-machine, library is separate.
3.  **Reader Integration:** ✅ Skim, Sioyek, Foliate, Apple Books documented.
4.  **AI Reading Assistant:** ✅ Clipboard-based `dlm ask` flow.

## Phase 5: Release ✅
1.  **License:** ✅ MIT
2.  **Security Check:** ✅ No hardcoded credentials in codebase.

## Phase 6: Cross-Platform Linux Support ✅
**Goal:** Full Linux support with native readers.

1.  **Sioyek (PDF):** ✅ `readers/sioyek.py` — reads highlights from `shared.db`
2.  **Foliate (EPUB):** ✅ `readers/foliate.py` — reads highlights from per-book JSON
3.  **Config migration:** ✅ TOML config replaces Python config, `dlm config migrate`
4.  **Diagnostic tool:** ✅ `dlm-doctor` checks all dependencies
5.  **Clipboard ask:** ✅ `dlm ask` reads from clipboard (cross-platform via pyperclip)
6.  **LLM abstraction:** ✅ `llm/` package with pluggable backends (v1: Gemini)
