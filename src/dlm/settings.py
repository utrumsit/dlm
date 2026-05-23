"""
DLM Settings — loads configuration from TOML (or legacy Python) and
exposes module-level variables for backward compatibility with all callers.

Config priority:
  1. ~/.config/dlm/config.toml  (new TOML format)
  2. ~/.config/dlm/config.py    (legacy, auto-migrate on first run)
  3. LIBRARY_ROOT/config.py     (legacy fallback at library root)
  4. Defaults + environment variables

$GOOGLE_API_KEY env var always overrides config files.
"""

import os
import sys
from pathlib import Path

# ── Library Root (unchanged) ──────────────────────────────────────────────
LIBRARY_ROOT = Path(os.environ.get("DLM_LIBRARY_ROOT", Path.cwd())).resolve()

# ── XDG paths ─────────────────────────────────────────────────────────────
XDG_CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
DLM_DATA_DIR = XDG_DATA_HOME / "dlm"
DLM_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Allow override
if os.environ.get("DLM_DATA_DIR"):
    DLM_DATA_DIR = Path(os.environ.get("DLM_DATA_DIR")).resolve()
    DLM_DATA_DIR.mkdir(parents=True, exist_ok=True)
else:
    # Auto-migrate old ~/.dlm/data
    old_data_dir = Path.home() / ".dlm" / "data"
    if old_data_dir.exists() and old_data_dir.is_dir():
        print(f"Migrating data from {old_data_dir} to {DLM_DATA_DIR}")
        import shutil
        shutil.copytree(old_data_dir, DLM_DATA_DIR, dirs_exist_ok=True)
        print("Migration complete. Old data preserved.")

# ── Config file paths ─────────────────────────────────────────────────────
DLM_CONFIG_DIR = XDG_CONFIG_HOME / "dlm"
LOCAL_TOML_PATH = DLM_CONFIG_DIR / "config.toml"
LOCAL_PY_PATH = DLM_CONFIG_DIR / "config.py"
LIBRARY_PY_PATH = LIBRARY_ROOT / "config.py"  # legacy location

# ── TOML loader (stdlib tomllib on 3.11+, tomli fallback) ─────────────────
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # will fall back to defaults


def _load_toml_config(path: Path):
    """Load config from a TOML file, returning parsed dict or empty dict."""
    if tomllib is None or not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


# ── Mutable config store ──────────────────────────────────────────────────
# Using a dict avoids Python 3.14+ restrictions on `global` reassignment.
# Module-level names below read from this dict for backward compatibility.

_config_store = {
    "JOPLIN_TOKEN": "",
    "JOPLIN_API_URL": "http://localhost:41184",
    "JOPLIN_NOTEBOOK_NAME": "Digital Library Notes",
    "SKIM_APP_PATH": "/Applications/Skim.app",
    "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", ""),
    "GOOGLE_CLIENT_ID": "",
    "GOOGLE_CLIENT_SECRET": "",
    "READERS_PDF": "",
    "READERS_EPUB": "",
    "SIOYEK_BINARY": "sioyek",
    "SIOYEK_SHARED_DB": "~/.local/share/sioyek/shared.db",
    "FOLIATE_BINARY": "foliate",
    "FOLIATE_LIBRARY_DIR": "~/.local/share/com.github.johnfactotum.Foliate",
    "LLM_BACKEND": "gemini",
}


def _apply_toml_to_store(toml_data: dict):
    """Apply TOML-parsed values to the config store dict."""
    joplin = toml_data.get("joplin", {})
    if joplin.get("token"):
        _config_store["JOPLIN_TOKEN"] = joplin["token"]
    if joplin.get("api_url"):
        _config_store["JOPLIN_API_URL"] = joplin["api_url"]
    if joplin.get("notebook_name"):
        _config_store["JOPLIN_NOTEBOOK_NAME"] = joplin["notebook_name"]

    skim = toml_data.get("skim", {})
    if skim.get("app_path"):
        _config_store["SKIM_APP_PATH"] = skim["app_path"]

    readers = toml_data.get("readers", {})
    if readers.get("pdf"):
        _config_store["READERS_PDF"] = readers["pdf"]
    if readers.get("epub"):
        _config_store["READERS_EPUB"] = readers["epub"]

    sioyek = toml_data.get("sioyek", {})
    if sioyek.get("binary"):
        _config_store["SIOYEK_BINARY"] = sioyek["binary"]
    if sioyek.get("shared_db"):
        _config_store["SIOYEK_SHARED_DB"] = sioyek["shared_db"]

    foliate = toml_data.get("foliate", {})
    if foliate.get("binary"):
        _config_store["FOLIATE_BINARY"] = foliate["binary"]
    if foliate.get("library_dir"):
        _config_store["FOLIATE_LIBRARY_DIR"] = foliate["library_dir"]

    llm = toml_data.get("llm", {})
    if llm.get("backend"):
        _config_store["LLM_BACKEND"] = llm["backend"]

    gemini = llm.get("gemini", {})
    if gemini.get("api_key"):
        _config_store["GOOGLE_API_KEY"] = gemini["api_key"]
    if gemini.get("client_id"):
        _config_store["GOOGLE_CLIENT_ID"] = gemini["client_id"]
    if gemini.get("client_secret"):
        _config_store["GOOGLE_CLIENT_SECRET"] = gemini["client_secret"]


def _apply_py_config(mod):
    """
    Apply values from a legacy config.py module to the config store.
    Same logic as the old settings.py (unchanged behaviour).
    """
    if hasattr(mod, "JOPLIN_TOKEN"):
        _config_store["JOPLIN_TOKEN"] = mod.JOPLIN_TOKEN
    if hasattr(mod, "JOPLIN_API_URL"):
        _config_store["JOPLIN_API_URL"] = mod.JOPLIN_API_URL
    if hasattr(mod, "JOPLIN_NOTEBOOK_NAME"):
        _config_store["JOPLIN_NOTEBOOK_NAME"] = mod.JOPLIN_NOTEBOOK_NAME
    if hasattr(mod, "SKIM_APP_PATH"):
        _config_store["SKIM_APP_PATH"] = mod.SKIM_APP_PATH
    if hasattr(mod, "GOOGLE_API_KEY") and mod.GOOGLE_API_KEY:
        _config_store["GOOGLE_API_KEY"] = mod.GOOGLE_API_KEY
    if hasattr(mod, "GOOGLE_CLIENT_ID") and mod.GOOGLE_CLIENT_ID:
        _config_store["GOOGLE_CLIENT_ID"] = mod.GOOGLE_CLIENT_ID
    if hasattr(mod, "GOOGLE_CLIENT_SECRET") and mod.GOOGLE_CLIENT_SECRET:
        _config_store["GOOGLE_CLIENT_SECRET"] = mod.GOOGLE_CLIENT_SECRET


# ── Module-level exports (backward-compatible names) ──────────────────────
# These are read via __getattr__ from the config store for lazy access.

def __getattr__(name):
    if name in _config_store:
        return _config_store[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ── Auto-migrate config.py → config.toml (if needed) ──────────────────────
_PY_TO_DOTTED = {
    "JOPLIN_TOKEN": "joplin.token",
    "JOPLIN_API_URL": "joplin.api_url",
    "JOPLIN_NOTEBOOK_NAME": "joplin.notebook_name",
    "SKIM_APP_PATH": "skim.app_path",
    "GOOGLE_API_KEY": "llm.gemini.api_key",
    "GOOGLE_CLIENT_ID": "llm.gemini.client_id",
    "GOOGLE_CLIENT_SECRET": "llm.gemini.client_secret",
}

# tomli_w for migration (best-effort, no crash if missing)
try:
    import tomli_w
except ImportError:
    tomli_w = None


def _load_py_config(path: Path):
    """Dynamically import a legacy config.py file."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("user_config", path)
    if spec is None:
        raise ValueError(f"Cannot load config from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["user_config"] = mod
    spec.loader.exec_module(mod)
    return mod


def _auto_migrate_py_to_toml(py_path: Path) -> bool:
    """
    Attempt to auto-migrate a legacy config.py → config.toml.
    Returns True if migration happened, False otherwise.
    """
    if not py_path.exists() or LOCAL_TOML_PATH.exists():
        return False
    if tomli_w is None:
        return False

    DLM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    try:
        mod = _load_py_config(py_path)
    except Exception as e:
        print(f"\n\033[93mWarning: Could not auto-migrate config.py: {e}\033[0m")
        return False

    try:
        from .config_schema import Config
    except ImportError:
        return False

    cfg = Config()
    migrated_any = False
    for py_name, dotted in _PY_TO_DOTTED.items():
        if hasattr(mod, py_name) and getattr(mod, py_name):
            Config.set_by_dotted(cfg, dotted, getattr(mod, py_name))
            migrated_any = True

    if migrated_any:
        toml_data = cfg.to_dict()
        with open(LOCAL_TOML_PATH, "w") as f:
            f.write(tomli_w.dumps(toml_data))

        # Backup the original
        bak = py_path.with_suffix(".py.bak")
        py_path.rename(bak)

        print(f"\n\033[93mAuto-migrated {py_path} → {LOCAL_TOML_PATH}\033[0m")
        print(f"  Original backed up to {bak}\033[0m\n")
        return True

    return False


# ── Main config loading logic ─────────────────────────────────────────────
def load_config():
    """Load configuration (called at import time)."""
    # Step 1: Check for TOML config
    if LOCAL_TOML_PATH.exists():
        toml_data = _load_toml_config(LOCAL_TOML_PATH)
        _apply_toml_to_store(toml_data)
        # Env override for GOOGLE_API_KEY
        env_key = os.environ.get("GOOGLE_API_KEY", "")
        if env_key:
            _config_store["GOOGLE_API_KEY"] = env_key
        return

    # Step 2: Check for local config.py → auto-migrate
    if LOCAL_PY_PATH.exists():
        if _auto_migrate_py_to_toml(LOCAL_PY_PATH):
            # Reload from the newly created TOML
            toml_data = _load_toml_config(LOCAL_TOML_PATH)
            _apply_toml_to_store(toml_data)
            env_key = os.environ.get("GOOGLE_API_KEY", "")
            if env_key:
                _config_store["GOOGLE_API_KEY"] = env_key
            return

    # Step 3: Fallback to legacy library-root config.py
    if LIBRARY_PY_PATH.exists():
        try:
            mod = _load_py_config(LIBRARY_PY_PATH)
            _apply_py_config(mod)
        except (PermissionError, OSError) as e:
            print(f"\n\033[91mError loading configuration file: {LIBRARY_PY_PATH}\033[0m")
            print(f"\033[93mCause: {e}\033[0m")
            print("Tip: Create a local config instead:")
            print(f"       mkdir -p ~/.config/dlm && cp config.toml.example ~/.config/dlm/config.toml")
        # Env override
        env_key = os.environ.get("GOOGLE_API_KEY", "")
        if env_key:
            _config_store["GOOGLE_API_KEY"] = env_key
        return

    # Step 4: No config file — defaults + env vars (already in store)
    env_key = os.environ.get("GOOGLE_API_KEY", "")
    if env_key:
        _config_store["GOOGLE_API_KEY"] = env_key


# Run config loading at import time
load_config()

# ── Direct module-level accessors ─────────────────────────────────────────
# For modules that do `from .settings import JOPLIN_TOKEN`, we need the name
# to be resolvable at import time. __getattr__ handles this, but let's also
# make the names directly accessible for IDE/type-checker friendliness.
# (On Python 3.7+ __getattr__ at module level handles missing attrs.)


# ── Derived paths ─────────────────────────────────────────────────────────
CATALOG_FILE = LIBRARY_ROOT / "catalog.json"
PROGRESS_FILE = LIBRARY_ROOT / "reading_progress.json"

# Data files in XDG_DATA_HOME
DLM_LOGS = DLM_DATA_DIR / "logs"
DLM_CACHE = DLM_DATA_DIR / "cache"
