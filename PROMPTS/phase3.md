# Task: Phase 3 — `dlm doctor` diagnostic command

## Goal
Add `dlm doctor` command that diagnoses the local install. Each check returns (name, status, detail, fix_hint). Output is a colored table.

## Create

### src/dlm/doctor.py
A list of named check functions, each returning `(status, detail, fix)` where status ∈ {"ok", "warn", "fail"}.

Required checks:
1. **platform** — print uname and detected platform; status always ok
2. **library_root** — `LIBRARY_ROOT` exists and is readable; fail if not
3. **catalog** — `catalog.json` exists in library root; warn if missing → "run dlm-catalog"
4. **fzf** — `shutil.which("fzf")` returns a path
5. **pdftotext** — `shutil.which("pdftotext")` (from poppler)
6. **exiftool** — `shutil.which("exiftool")`
7. **pdf_reader** — from config, look up which reader; verify the reader's `is_available()` returns True
8. **epub_reader** — same
9. **joplin** — GET {joplin.api_url}/ping with token; warn if not 200
10. **gemini** — either GEMINI api_key is set OR cached OAuth tokens exist at the standard location
11. **clipboard** — verify pyperclip can read clipboard without error (or warn if xclip/wl-paste missing on Linux)

## Modify
- pyproject.toml: add `pyperclip = "^1.8"` dep. Add entry point `dlm-doctor = "dlm.doctor:main"`.

## Output format
```
DLM Doctor
==========
 [OK]   Platform                Linux 6.x
 [OK]   Library root            /home/karl/DigitalLibrary
 [WARN] Catalog                 catalog.json missing
        → fix: poetry run dlm-catalog
 [OK]   fzf                     /usr/bin/fzf
 ...
Summary: 8 OK, 2 warnings, 1 failure
```

Use ANSI color codes (green for OK, yellow for WARN, red for FAIL). Detect TTY and disable colors if stdout is not a terminal.

## Constraints
- No external dep beyond pyperclip + requests (already a dep)
- Each check has a 5-second timeout (especially the network ones)
- Don't crash on individual check failure — capture exceptions and report as fail

## Verify
```
poetry run dlm-doctor
# expected: a colored summary table
```
