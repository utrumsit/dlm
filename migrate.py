#!/usr/bin/env python3
"""Standalone DLM XDG migration script. Safe, idempotent, preserves originals."""

import os
import shutil
from pathlib import Path

print("DLM XDG Migration Tool\n")

home = Path.home()

# Config migration
old_config = home / ".dlm" / "config.json"
new_config_dir = Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))) / "dlm"
new_config = new_config_dir / "config.py"  # Note: different format, user must edit

if old_config.exists() and not new_config.exists():
    new_config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old_config, new_config_dir / "config.json")
    print(f"✓ Config copied: {old_config} → {new_config_dir / 'config.json'}")
    print("Note: Rename to config.py and edit for Python format.")
else:
    print("Config OK or already migrated.")

# Data migration
old_data = home / ".dlm" / "data"
xdg_data = Path(os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))) / "dlm"

if old_data.exists() and old_data.is_dir():
    xdg_data.mkdir(parents=True, exist_ok=True)
    shutil.copytree(old_data, xdg_data, dirs_exist_ok=True)
    print(f"✓ Data migrated: {old_data} → {xdg_data}")
else:
    print("Data OK or no old data found.")

print("\nMigration complete! Old files preserved. Run 'dlm' to test.")
print("Tip: Set DLM_LIBRARY_ROOT if your books are not in current dir.")
