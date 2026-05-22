# Task: Phase 7 — Packaging, install scripts, README rewrite

## Goal
Make DLM installable on Linux and Mac with clear, separated install instructions. Update README and AGENTS.md.

## Read first
- README.md
- AGENTS.md
- OPEN_SOURCE_PLAN.md
- pyproject.toml

## Modify

### pyproject.toml
- Bump version to 0.2.0
- Description: remove "macOS" reference, replace with "cross-platform CLI for managing a personal DDC-organized digital library"
- Confirm all entry points: dlm, dlm-catalog, dlm-sort, dlm-init, dlm-toc, dlm-auth, dlm-metafix, dlm-config, dlm-doctor

### README.md
Reorganize:
1. Top: brief intro (no platform restriction)
2. Features (unchanged)
3. Installation:
   - **macOS** section: brew install pipx fzf poppler exiftool; recommended Skim/Apple Books
   - **Linux (Debian/Ubuntu)** section: apt install pipx fzf poppler-utils libimage-exiftool-perl xclip; recommended sioyek foliate joplin-desktop
   - **Linux (Arch)** section: pacman -S python-pipx fzf poppler perl-image-exiftool xclip; AUR/repo for sioyek foliate
   - Common: `git clone …; cd dlm; pipx install -e .`
4. First-run setup:
   - Set `DLM_LIBRARY_ROOT`
   - Run `dlm-init` (scaffold), `dlm-config migrate` (if upgrading), `dlm-doctor` (verify)
   - Run `dlm-catalog`
5. Usage (mostly unchanged, but document `dlm ask` clipboard flow)
6. Configuration: short reference, point at `dlm config show` for the live source of truth
7. Multi-machine sync: keep current section, add a note that config.toml is per-machine

### AGENTS.md
- Replace the macOS-only hostname table with a generic per-machine notes table that includes Linux boxes too
- Document the readers/ abstraction (one paragraph)
- Document the llm/ abstraction
- Update "Environment Requirements" to list both Mac and Linux deps

### OPEN_SOURCE_PLAN.md
- Mark Linux support as done
- Update phases

## Constraints
- Do not delete the macOS install instructions — additive
- Verify all command examples actually exist as entry points
- Don't introduce new docs files — extend the existing ones

## Verify
```
# On Linux:
pipx install -e .
dlm-doctor
dlm-catalog
dlm <some book>
```
