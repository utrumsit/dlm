import importlib.util
import os
import sys
from pathlib import Path

# 1. Determine Library Root
LIBRARY_ROOT = Path(os.environ.get("DLM_LIBRARY_ROOT", Path.cwd())).resolve()

# 2. Path to the user's real config file
USER_CONFIG_PATH = LIBRARY_ROOT / "config.py"

# Placeholders for default values (if config.py is missing)
JOPLIN_TOKEN = ""
JOPLIN_API_URL = "http://localhost:41184"
JOPLIN_NOTEBOOK_NAME = "Digital Library Notes"
SKIM_APP_PATH = "/Applications/Skim.app"

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
    except (PermissionError, OSError) as e:
        print(f"\n\033[91mError loading configuration file: {USER_CONFIG_PATH}\033[0m")
        print(f"\033[93mCause: {e}\033[0m")
        print("Tip: This often happens with files in OneDrive/iCloud that are not downloaded locally.")
        print("     Try: 1. Open the folder in Finder.")
        print("          2. Right-click 'config.py' and select 'Always Keep on This Device'.")
        print("          3. Ensure your terminal has 'Full Disk Access' in System Settings.\n")
        # Proceed with defaults (functionality may be limited)
else:
    # Print a warning if we're not just running a help command
    if "--help" not in sys.argv and "-h" not in sys.argv:
        print(f"Warning: Configuration file not found at {USER_CONFIG_PATH}")
        print("Please run 'dlm-init' to set up your library root.")

CATALOG_FILE = LIBRARY_ROOT / "catalog.json"
PROGRESS_FILE = LIBRARY_ROOT / "reading_progress.json"
