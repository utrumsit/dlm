import os
import shutil
import sys
from pathlib import Path


def init_library():
    # Scaffolds the library structure.
    # 1. Determine Library Root
    env_root = os.environ.get("DLM_LIBRARY_ROOT")
    if env_root:
        base_path = Path(env_root).resolve()
        print(f"Initializing library in DLM_LIBRARY_ROOT: {base_path}")
    else:
        # Default to current directory if not set
        base_path = Path.cwd()
        print(f"Initializing library in Current Directory: {base_path}")

    if not base_path.exists():
        print(f"Error: Directory {base_path} does not exist.")
        sys.exit(1)

    # 2. Create DDC Folders
    ddc_categories = {
        "000": "Computer_Science",
        "100": "Philosophy",
        "200": "Religion",
        "300": "Social_Sciences",
        "400": "Language",
        "500": "Science",
        "600": "Technology",
        "700": "Arts",
        "800": "Literature",
        "900": "History",
    }

    for code, name in ddc_categories.items():
        folder_name = f"{code}_{name}"
        folder_path = base_path / folder_name
        if not folder_path.exists():
            print(f"Creating {folder_name}/...")
            folder_path.mkdir()

    # 3. Create Inbox
    inbox = base_path / "_Inbox"
    if not inbox.exists():
        print("Creating _Inbox/...")
        inbox.mkdir()

    # 4. Init Config
    # Check if we are running from the source dir (where the template is)
    source_dir = Path(__file__).parent
    config_example = source_dir / "config.py.example"
    config_real = base_path / "config.py"

    if config_example.exists() and not config_real.exists():
        print("Creating config.py from template...")
        shutil.copy(config_example, config_real)
        print("IMPORTANT: Please edit config.py with your Joplin tokens.")
    elif config_real.exists():
        print("config.py already exists. Skipping.")
    else:
        print(
            "Warning: config.py.example not found in source dir. Skipping config creation."
        )


if __name__ == "__main__":
    init_library()
