#!/usr/bin/env python3
"""
Generate TOC.md from the DigitalLibrary directory structure
"""

import os
from pathlib import Path
from urllib.parse import quote

LIBRARY_ROOT = Path(os.environ.get("DLM_LIBRARY_ROOT", Path(__file__).parent)).resolve()
TOC_FILE = LIBRARY_ROOT / "TOC.md"


def get_display_name(path):
    """Get a nice display name for a file"""
    name = path.stem
    # Clean up common patterns
    name = name.replace("_", " ")
    return name


def extract_ddc(dirname):
    """Extract DDC number from directory name"""
    parts = dirname.split("_")
    if parts[0].replace(".", "").isdigit():
        return parts[0]
    return None


def generate_toc():
    """Generate TOC markdown with DDC numbers"""
    lines = ["# Digital Library - Table of Contents\n"]
    lines.append("\n*Organized using Dewey Decimal Classification (DDC)*\n")

    # Get all top-level category directories (excluding Personal, My_Research, MCI)
    categories = sorted(
        [
            d
            for d in LIBRARY_ROOT.iterdir()
            if d.is_dir()
            and not d.name.startswith(".")
            and d.name not in ["MCI", "Personal", "My_Research"]
        ]
    )

    for category_dir in categories:
        category_name = category_dir.name
        display_name = category_name.replace("_", " ")
        ddc = extract_ddc(category_name)

        # Add DDC number to heading for easy grep
        if ddc:
            lines.append(f"\n## [{ddc}] {display_name}\n")
        else:
            lines.append(f"\n## {display_name}\n")

        # Check if there are subdirectories
        subdirs = sorted([d for d in category_dir.iterdir() if d.is_dir()])

        if subdirs:
            # Has subcategories
            for subdir in subdirs:
                subdir_name = subdir.name.replace("_", " ")
                lines.append(f"\n### {subdir_name}\n")

                # List files in subdirectory
                files = sorted(
                    [
                        f
                        for f in subdir.iterdir()
                        if f.is_file() and not f.name.startswith(".")
                    ]
                )
                for file_path in files:
                    relative = file_path.relative_to(LIBRARY_ROOT)
                    # URL encode the path for the link
                    encoded_path = str(relative).replace(" ", "%20")
                    lines.append(f"- [{file_path.name}]({encoded_path})\n")
        else:
            # No subcategories, list files directly
            files = sorted(
                [
                    f
                    for f in category_dir.iterdir()
                    if f.is_file() and not f.name.startswith(".")
                ]
            )
            for file_path in files:
                relative = file_path.relative_to(LIBRARY_ROOT)
                encoded_path = str(relative).replace(" ", "%20")
                lines.append(f"- [{file_path.name}]({encoded_path})\n")

    # Add Personal, My_Research, and MCI at the end
    for special_dir in ["Personal", "My_Research"]:
        special_path = LIBRARY_ROOT / special_dir
        if special_path.exists() and special_path.is_dir():
            lines.append(f"\n## {special_dir.replace('_', ' ')}\n")
            files = sorted(
                [
                    f
                    for f in special_path.iterdir()
                    if f.is_file() and not f.name.startswith(".")
                ]
            )
            for file_path in files:
                relative = file_path.relative_to(LIBRARY_ROOT)
                encoded_path = str(relative).replace(" ", "%20")
                lines.append(f"- [{file_path.name}]({encoded_path})\n")

    lines.append("\n## MCI (Untouched)\n")
    lines.append("*Metropolitan Cantor Institute materials - kept separate*\n")

    return "".join(lines)


def main():
    print("Generating TOC.md from library structure...")
    toc_content = generate_toc()

    with open(TOC_FILE, "w") as f:
        f.write(toc_content)

    print(f"TOC written to {TOC_FILE}")

    # Count entries
    file_count = toc_content.count("- [")
    print(f"Total files listed: {file_count}")


if __name__ == "__main__":
    main()
