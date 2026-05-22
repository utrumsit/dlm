"""
dlm doctor — diagnostic command.

Runs a battery of checks to verify the local DLM installation is functional.
Each check returns (status, detail, fix_hint) where status is ok/warn/fail.
"""

import json
import os
import platform
import shutil
import sys
from pathlib import Path

import requests

from .settings import (
    LIBRARY_ROOT,
    JOPLIN_API_URL,
    JOPLIN_NOTEBOOK_NAME,
    JOPLIN_TOKEN,
    GOOGLE_API_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
)

# ── ANSI colours ──────────────────────────────────────────────────────────

_USE_COLOR = sys.stdout.isatty()

def _c(code):
    return f"\033[{code}m" if _USE_COLOR else ""

C_OK   = _c("92m")  # green
C_WARN = _c("93m")  # yellow
C_FAIL = _c("91m")  # red
C_FIX  = _c("36m")  # cyan
C_DIM  = _c("37m")  # grey
C_RESET = _c("0m")


_STATUS_ICON = {
    "ok": f"{C_OK}[OK]{C_RESET}",
    "warn": f"{C_WARN}[WARN]{C_RESET}",
    "fail": f"{C_FAIL}[FAIL]{C_RESET}",
}

_STATUS_COUNT = {"ok": 0, "warn": 0, "fail": 0}


def _record(status):
    _STATUS_COUNT[status] += 1


def check(name, status, detail="", fix=""):
    """Record a check result and print it immediately."""
    _record(status)
    icon = _STATUS_ICON[status]
    print(f" {icon}  {name:<25} {detail}")
    if fix:
        print(f"         {C_FIX}→ fix: {fix}{C_RESET}")


# ── Individual checks ─────────────────────────────────────────────────────

def _check_platform():
    """Always ok — just report what we detected."""
    uname = platform.uname()
    detail = f"{uname.system} {uname.machine} (Python {platform.python_version()})"
    check("Platform", "ok", detail)


def _check_library_root():
    """LIBRARY_ROOT exists and is readable."""
    if not LIBRARY_ROOT.exists():
        check("Library root", "fail",
              str(LIBRARY_ROOT),
              f"Set DLM_LIBRARY_ROOT or create the directory")
        return
    if not os.access(str(LIBRARY_ROOT), os.R_OK):
        check("Library root", "fail",
              str(LIBRARY_ROOT),
              "Fix directory permissions")
        return
    check("Library root", "ok", str(LIBRARY_ROOT))


def _check_catalog():
    """catalog.json exists in library root."""
    catalog_path = LIBRARY_ROOT / "catalog.json"
    if not catalog_path.exists():
        check("Catalog", "warn", "catalog.json missing",
              "dlm-catalog")
        return
    try:
        with open(catalog_path) as f:
            data = json.load(f)
        count = len(data) if isinstance(data, list) else 0
        check("Catalog", "ok", f"{count} entries")
    except json.JSONDecodeError:
        check("Catalog", "fail", "catalog.json is invalid JSON",
              "dlm-catalog")


def _check_binary(name, hint=None):
    """Check if a binary is on PATH."""
    if hint is None:
        hint = f"Install {name}"
    path = shutil.which(name)
    if path:
        check(name, "ok", path)
    else:
        check(name, "fail", "not found", hint)


def _check_fzf():
    _check_binary("fzf", "Install fzf (e.g. brew install fzf / apt install fzf)")


def _check_pdftotext():
    _check_binary("pdftotext",
                  "Install poppler-utils (e.g. apt install poppler-utils)")


def _check_exiftool():
    _check_binary("exiftool",
                  "Install libimage-exiftool-perl (e.g. apt install libimage-exiftool-perl)")


def _check_pdf_reader():
    """Check that a PDF reader is available based on config + platform."""
    sys_name = platform.system()

    # Load config for reader override
    pdf_reader_override = _get_config_value("readers.pdf")

    if pdf_reader_override:
        # Explicit reader override in config
        if pdf_reader_override.lower() == "sioyek":
            path = shutil.which("sioyek")
            if path:
                check("PDF reader", "ok", f"sioyek ({path})")
            else:
                check("PDF reader", "fail", "sioyek not found on PATH",
                      "Install sioyek")
        elif pdf_reader_override.lower() == "skim":
            _check_skim_available()
        else:
            path = shutil.which(pdf_reader_override)
            if path:
                check("PDF reader", "ok", f"{pdf_reader_override} ({path})")
            else:
                check("PDF reader", "fail",
                      f"{pdf_reader_override} not found",
                      f"Install {pdf_reader_override} or remove readers.pdf from config")
    elif sys_name == "Darwin":
        _check_skim_available()
    elif sys_name == "Linux":
        path = shutil.which("sioyek")
        if path:
            check("PDF reader", "ok", f"sioyek ({path})")
        else:
            # Check for any fallback
            check("PDF reader", "warn", "No PDF reader configured",
                  "Install sioyek or set readers.pdf in config")
    else:
        check("PDF reader", "warn", f"Unknown platform ({sys_name})",
              "Set readers.pdf in config.toml")


def _check_skim_available():
    skim_path = _get_config_value("skim.app_path") or "/Applications/Skim.app"
    if Path(skim_path).exists():
        check("PDF reader", "ok", f"Skim ({skim_path})")
    else:
        check("PDF reader", "fail", f"Skim not found at {skim_path}",
              "Install Skim or set skim.app_path in config")


def _check_epub_reader():
    """Check that an EPUB reader is available based on config + platform."""
    sys_name = platform.system()

    epub_reader_override = _get_config_value("readers.epub")

    if epub_reader_override:
        if epub_reader_override.lower() == "foliate":
            path = shutil.which("foliate")
            if path:
                check("EPUB reader", "ok", f"foliate ({path})")
            else:
                check("EPUB reader", "fail", "foliate not found on PATH",
                      "Install foliate (Flatpak: com.github.johnfactotum.Foliate)")
        elif epub_reader_override.lower() in ("applebooks", "apple-books", "apple books"):
            check("EPUB reader", "ok", "Apple Books (macOS built-in)")
        else:
            path = shutil.which(epub_reader_override)
            if path:
                check("EPUB reader", "ok", f"{epub_reader_override} ({path})")
            else:
                check("EPUB reader", "fail",
                      f"{epub_reader_override} not found",
                      f"Install {epub_reader_override} or remove readers.epub from config")
    elif sys_name == "Darwin":
        check("EPUB reader", "ok", "Apple Books (macOS built-in)")
    elif sys_name == "Linux":
        path = shutil.which("foliate")
        if path:
            check("EPUB reader", "ok", f"foliate ({path})")
        else:
            # Also check flatpak
            fp = shutil.which("flatpak")
            if fp:
                check("EPUB reader", "warn",
                      "foliate not on PATH (flatpak available)",
                      "flatpak install com.github.johnfactotum.Foliate")
            else:
                check("EPUB reader", "warn", "No EPUB reader configured",
                      "Install foliate or set readers.epub in config")
    else:
        check("EPUB reader", "warn", f"Unknown platform ({sys_name})",
              "Set readers.epub in config.toml")


def _check_joplin():
    """Ping Joplin Web Clipper."""
    if not JOPLIN_TOKEN:
        check("Joplin", "warn", "No API token configured",
              "Set joplin.token in config.toml")
        return

    try:
        resp = requests.get(f"{JOPLIN_API_URL}/ping", timeout=5)
        if resp.status_code == 200:
            check("Joplin", "ok", f"{JOPLIN_API_URL}")
        else:
            check("Joplin", "fail", f"HTTP {resp.status_code}",
                  f"Check Joplin is running on {JOPLIN_API_URL}")
    except requests.exceptions.ConnectionError:
        check("Joplin", "warn", f"Cannot connect to {JOPLIN_API_URL}",
              "Start Joplin and enable Web Clipper")
    except requests.exceptions.Timeout:
        check("Joplin", "fail", "Connection timed out",
              "Check Joplin is running")
    except Exception as e:
        check("Joplin", "fail", str(e))


def _check_gemini():
    """Check Gemini credentials (API key or OAuth tokens)."""
    # 1. API key
    if GOOGLE_API_KEY:
        check("Gemini", "ok", "API key configured")
        return

    # 2. OAuth tokens
    token_path = Path.home() / ".config" / "dlm" / "oauth_token.json"
    if token_path.exists():
        try:
            with open(token_path) as f:
                data = json.load(f)
            has_token = bool(data.get("token"))
            has_refresh = bool(data.get("refresh_token"))
            if has_token or has_refresh:
                detail = "OAuth token stored"
                if has_refresh:
                    detail += " (with refresh)"
                check("Gemini", "ok", detail)
                return
        except (json.JSONDecodeError, OSError):
            pass

    # 3. Check if OAuth client credentials are at least configured (can re-auth)
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        check("Gemini", "warn", "OAuth credentials set but no token",
              "Run dlm-auth to authenticate")
        return

    # 4. Nothing
    check("Gemini", "warn", "No credentials configured",
          "Run dlm-auth or set llm.gemini.api_key in config")


def _check_clipboard():
    """Check that clipboard access works."""
    sys_name = platform.system()

    # Try pyperclip first
    try:
        import pyperclip
        # Try a read (may block or fail headless — catch it)
        pyperclip.__version__  # just verify importable
        check("Clipboard", "ok", f"pyperclip {pyperclip.__version__}")
        return
    except ImportError:
        pass
    except Exception as e:
        # pyperclip imported but runtime error (e.g. no display)
        pass

    # Fallback checks for Linux clipboard tools
    if sys_name == "Linux":
        xclip = shutil.which("xclip")
        wl_paste = shutil.which("wl-paste")
        if xclip:
            check("Clipboard", "warn", f"xclip available ({xclip}), pyperclip not installed",
                  "pip install pyperclip")
        elif wl_paste:
            check("Clipboard", "warn", f"wl-paste available, pyperclip not installed",
                  "pip install pyperclip")
        else:
            check("Clipboard", "fail", "No clipboard tool found",
                  "pip install pyperclip (requires xclip or wl-paste)")
    elif sys_name == "Darwin":
        check("Clipboard", "ok", "pbcopy/pbpaste (macOS built-in)")
    else:
        check("Clipboard", "warn", "Clipboard support unverified",
              "pip install pyperclip")


# ── Config helper ─────────────────────────────────────────────────────────

def _get_config_value(dotted_key):
    """Read a value from the TOML config without loading the full schema."""
    from .settings import DLM_CONFIG_DIR
    toml_path = DLM_CONFIG_DIR / "config.toml"
    if not toml_path.exists():
        return None

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return None

    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        return None

    parts = dotted_key.split(".")
    cur = data
    for part in parts:
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    val = cur if cur else None
    return val


# ── Main ──────────────────────────────────────────────────────────────────

CHECKS = [
    _check_platform,
    _check_library_root,
    _check_catalog,
    _check_fzf,
    _check_pdftotext,
    _check_exiftool,
    _check_pdf_reader,
    _check_epub_reader,
    _check_joplin,
    _check_gemini,
    _check_clipboard,
]


def main():
    """Entry point for `dlm-doctor`."""
    print(f"\nDLM Doctor")
    print(f"{'=' * 60}\n")

    for check_fn in CHECKS:
        try:
            check_fn()
        except Exception as e:
            # Never crash on individual check failure
            check(check_fn.__name__.replace("_check_", "", 1), "fail",
                  f"Error running check: {e}")

    ok = _STATUS_COUNT["ok"]
    warn = _STATUS_COUNT["warn"]
    fail = _STATUS_COUNT["fail"]
    total = ok + warn + fail

    print()
    print("-" * 60)
    status_parts = [f"{ok} OK", f"{warn} warnings"]
    if fail:
        status_parts.append(f"{fail} failures")
    print(f"Summary: {', '.join(status_parts)} out of {total} checks")

    if _USE_COLOR:
        if fail:
            print(f"{C_FAIL}Some checks failed. See above for fix hints.{C_RESET}")
        elif warn:
            print(f"{C_WARN}Some checks have warnings. See above for details.{C_RESET}")
        else:
            print(f"{C_OK}All checks passed! ✨{C_RESET}")

    print()
    # Exit with non-zero if any failures
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
