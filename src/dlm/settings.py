import importlib.util
import os
import sys
from pathlib import Path

# 1. Determine Library Root
LIBRARY_ROOT = Path(os.environ.get("DLM_LIBRARY_ROOT", Path.cwd())).resolve()

# 2. Find config file: local first, then library root (legacy)
LOCAL_CONFIG_PATH = Path.home() / ".config" / "dlm" / "config.py"
LIBRARY_CONFIG_PATH = LIBRARY_ROOT / "config.py"

if LOCAL_CONFIG_PATH.exists():
    USER_CONFIG_PATH = LOCAL_CONFIG_PATH
else:
    USER_CONFIG_PATH = LIBRARY_CONFIG_PATH

# Placeholders for default values (if config.py is missing)
JOPLIN_TOKEN = ""
JOPLIN_API_URL = "http://localhost:41184"
JOPLIN_NOTEBOOK_NAME = "Digital Library Notes"
SKIM_APP_PATH = "/Applications/Skim.app"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CLIENT_ID = ""
GOOGLE_CLIENT_SECRET = ""

# 3. Dynamically load the user's config.py
if USER_CONFIG_PATH.exists():
    try:
        spec = importlib.util.spec_from_file_location("user_config", USER_CONFIG_PATH)
        user_config = importlib.util.module_from_spec(spec)
        # Add to sys.modules so imports inside the user config work
        sys.modules["user_config"] = user_config
        spec.loader.exec_module(user_config)
        
        # Export values to this module's namespace
        if hasattr(user_config, "JOPLIN_TOKEN"):
            JOPLIN_TOKEN = user_config.JOPLIN_TOKEN
        if hasattr(user_config, "JOPLIN_API_URL"):
            JOPLIN_API_URL = user_config.JOPLIN_API_URL
        if hasattr(user_config, "JOPLIN_NOTEBOOK_NAME"):
            JOPLIN_NOTEBOOK_NAME = user_config.JOPLIN_NOTEBOOK_NAME
        if hasattr(user_config, "SKIM_APP_PATH"):
            SKIM_APP_PATH = user_config.SKIM_APP_PATH
        if hasattr(user_config, "GOOGLE_API_KEY") and user_config.GOOGLE_API_KEY:
            GOOGLE_API_KEY = user_config.GOOGLE_API_KEY
        if hasattr(user_config, "GOOGLE_CLIENT_ID") and user_config.GOOGLE_CLIENT_ID:
            GOOGLE_CLIENT_ID = user_config.GOOGLE_CLIENT_ID
        if hasattr(user_config, "GOOGLE_CLIENT_SECRET") and user_config.GOOGLE_CLIENT_SECRET:
            GOOGLE_CLIENT_SECRET = user_config.GOOGLE_CLIENT_SECRET
    except (PermissionError, OSError) as e:
        print(f"\n\033[91mError loading configuration file: {USER_CONFIG_PATH}\033[0m")
        print(f"\033[93mCause: {e}\033[0m")
        if USER_CONFIG_PATH == LIBRARY_CONFIG_PATH:
            print("Tip: This often happens with files in OneDrive/iCloud that are not downloaded locally.")
            print("     Fix: Create a local config instead (never syncs, never times out):")
            print(f"       mkdir -p ~/.config/dlm && cp {LIBRARY_CONFIG_PATH} ~/.config/dlm/config.py")
        # Proceed with defaults (functionality may be limited)
else:
    # Print a warning if we're not just running a help command
    if "--help" not in sys.argv and "-h" not in sys.argv:
        print(f"Warning: No config file found.")
        print(f"  Searched: {LOCAL_CONFIG_PATH}")
        print(f"           {LIBRARY_CONFIG_PATH}")
        print(f"  Create one: mkdir -p ~/.config/dlm && cp config.py.example ~/.config/dlm/config.py")

CATALOG_FILE = LIBRARY_ROOT / "catalog.json"
PROGRESS_FILE = LIBRARY_ROOT / "reading_progress.json"
