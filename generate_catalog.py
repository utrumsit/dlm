#!/usr/bin/env python3
"""
Generate catalog.json from the DigitalLibrary directory structure
This script scans the library and creates catalog entries for all files
"""

import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

LIBRARY_ROOT = Path(os.environ.get('DLM_LIBRARY_ROOT', Path(__file__).parent)).resolve()
CATALOG_FILE = LIBRARY_ROOT / "catalog.json"

# DDC Category mappings
CATEGORY_INFO = {
    "000_Computer_Science": {
        "name": "Computer Science & Information",
        "ddc": "000",
        "default_subjects": ["Computer Science", "Technology"]
    },
    "100_Philosophy": {
        "name": "Philosophy",
        "ddc": "100",
        "default_subjects": ["Philosophy"]
    },
    "200_Religion": {
        "name": "Religion",
        "ddc": "200",
        "default_subjects": ["Religion", "Theology"]
    },
    "400_Language": {
        "name": "Language",
        "ddc": "400",
        "default_subjects": ["Language", "Classical Languages"]
    },
    "500_Science": {
        "name": "Natural Sciences & Mathematics",
        "ddc": "500",
        "default_subjects": ["Science"]
    },
    "600_Technology": {
        "name": "Technology & Applied Sciences",
        "ddc": "600",
        "default_subjects": ["Technology", "Applied Sciences"]
    },
    "700_Arts": {
        "name": "Arts",
        "ddc": "700",
        "default_subjects": ["Arts"]
    },
    "780_Music": {
        "name": "Music",
        "ddc": "780",
        "default_subjects": ["Music"]
    },
    "790_Recreation": {
        "name": "Recreation & Sports",
        "ddc": "790",
        "default_subjects": ["Recreation", "Sports"]
    },
    "Personal": {
        "name": "Personal",
        "ddc": None,
        "default_subjects": ["Personal"]
    },
    "My_Research": {
        "name": "My Research",
        "ddc": None,
        "default_subjects": ["Research", "Academic Work"]
    }
}

# DDC subcategory mappings
DDC_SUBCATEGORIES = {
    "005_Programming": {"ddc": "005", "subjects": ["Programming", "Software Development"]},
    "006_Artificial_Intelligence": {"ddc": "006.3", "subjects": ["Artificial Intelligence", "Machine Learning", "AI"]},
    "220_Scripture": {"ddc": "220", "subjects": ["Scripture", "Bible"]},
    "264_Liturgy": {"ddc": "264", "subjects": ["Liturgy", "Worship"]},
    "270_Patristics": {"ddc": "270", "subjects": ["Patristics", "Church Fathers", "Church History"]},
    "470_Latin": {"ddc": "470", "subjects": ["Latin", "Classical Latin"]},
    "480_Greek": {"ddc": "480", "subjects": ["Greek", "Ancient Greek", "Classical Greek"]},
    "510_Mathematics": {"ddc": "510", "subjects": ["Mathematics", "Math"]},
    "530_Physics": {"ddc": "530", "subjects": ["Physics"]},
    "570_Biology": {"ddc": "570", "subjects": ["Biology", "Life Sciences"]},
    "610_Medicine": {"ddc": "610", "subjects": ["Medicine", "Health"]},
    "630_Agriculture_Homesteading": {"ddc": "630", "subjects": ["Agriculture", "Homesteading", "Farming"]},
    "640_Home_Economics": {"ddc": "640", "subjects": ["Home Economics", "Self-Sufficiency", "DIY"]},
    "740_Drawing": {"ddc": "740", "subjects": ["Drawing", "Visual Arts"]},
    "781.65_Jazz": {"ddc": "781.65", "subjects": ["Jazz", "Jazz Music"]},
    "782_Vocal_Music": {"ddc": "782", "subjects": ["Vocal Music", "Choral Music"]},
    "784_Orchestral": {"ddc": "784", "subjects": ["Orchestral Music", "Orchestra"]},
    "787_Stringed_Instruments": {"ddc": "787", "subjects": ["Stringed Instruments"]},
    "796_Athletics": {"ddc": "796", "subjects": ["Athletics", "Sports", "Physical Training"]},
}

def extract_pdf_metadata(filepath):
    """Extract title and author from PDF metadata using pdfinfo"""
    try:
        result = subprocess.run(
            ['pdfinfo', str(filepath)],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            title = None
            author = None
            for line in result.stdout.split('\n'):
                if line.startswith('Title:'):
                    title = line.split(':', 1)[1].strip()
                elif line.startswith('Author:'):
                    author = line.split(':', 1)[1].strip()
            return title, author
    except Exception:
        pass
    return None, None

def extract_epub_metadata(filepath):
    """Extract title and author from EPUB metadata"""
    try:
        with zipfile.ZipFile(filepath, 'r') as epub:
            # Try to read content.opf
            for name in epub.namelist():
                if 'content.opf' in name.lower() or name.endswith('.opf'):
                    opf_content = epub.read(name)
                    root = ET.fromstring(opf_content)
                    
                    # Find title and author in metadata
                    ns = {'dc': 'http://purl.org/dc/elements/1.1/'}
                    title_elem = root.find('.//dc:title', ns)
                    author_elem = root.find('.//dc:creator', ns)
                    
                    title = title_elem.text if title_elem is not None else None
                    author = author_elem.text if author_elem is not None else None
                    
                    return title, author
    except Exception:
        pass
    return None, None

def extract_author_from_filename(filename):
    """Try to extract author from filename patterns like 'Author - Title.pdf'"""
    # Pattern: "LastName, FirstName - Title" or "Author - Title"
    match = re.match(r'^([^-]+?)\s*-\s*(.+)\.(pdf|epub)$', filename)
    if match:
        potential_author = match.group(1).strip()
        # Check if it looks like an author (not too long, not all caps unless short)
        if len(potential_author) < 50 and not potential_author.isupper():
            return potential_author
    return ""

def clean_title(filename):
    """Clean up filename to make a readable title"""
    # Remove extension
    title = re.sub(r'\.(pdf|epub|md|html|txt)$', '', filename, flags=re.IGNORECASE)

    # Remove author if present (pattern: "Author - Title")
    title = re.sub(r'^[^-]+?\s*-\s*', '', title)

    # Replace underscores and hyphens with spaces
    title = title.replace('_', ' ').replace('-', ' ')
    
    # Add spaces before capitals in camelCase/PascalCase (but not acronyms)
    # e.g., "machinelearning" -> "machine learning"
    title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)
    
    # Remove common suffixes like (e-ink), (1), etc
    title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
    
    # Clean up multiple spaces
    title = re.sub(r'\s+', ' ', title)
    
    # Capitalize first letter of each word for readability
    title = title.title()

    return title.strip()

def extract_ddc_from_path(category_path):
    """Extract DDC number from path components"""
    parts = Path(category_path).parts
    ddc_numbers = []
    
    for part in parts:
        # Check if this directory matches a known DDC subcategory
        if part in DDC_SUBCATEGORIES:
            ddc_numbers.append(DDC_SUBCATEGORIES[part]["ddc"])
    
    return ddc_numbers

def get_subcategory_subjects(category_path):
    """Get subjects based on subcategory and DDC classification"""
    subjects = []
    parts = Path(category_path).parts

    # Add DDC-based subjects from known subcategories
    for part in parts:
        if part in DDC_SUBCATEGORIES:
            subjects.extend(DDC_SUBCATEGORIES[part]["subjects"])
    
    # Add specific named subdirectories
    if "Byzantine_Liturgy" in parts:
        subjects.extend(["Byzantine Liturgy"])
    if "ByzantineChant" in parts or "Chant" in parts:
        subjects.extend(["Byzantine Chant", "Chant"])
    if "VocalScores" in parts:
        subjects.append("Vocal Scores")
    if "Guitar" in parts:
        subjects.append("Guitar")
    if "Ukulele" in parts:
        subjects.append("Ukulele")
    if "Strength_Training" in parts:
        subjects.extend(["Strength Training", "Powerlifting", "Weight Training"])
    if "Survival_Skills" in parts:
        subjects.extend(["Survival", "Bushcraft", "Outdoor Skills"])

    return subjects

def generate_catalog():
    """Scan library and generate catalog entries"""
    catalog = []
    counter = 1

    # Scan each category
    for category_dir in sorted(LIBRARY_ROOT.iterdir()):
        if not category_dir.is_dir():
            continue
        if category_dir.name.startswith('.') or category_dir.name == 'MCI':
            continue

        category_name = category_dir.name
        if category_name not in CATEGORY_INFO:
            continue

        # Walk through the category directory
        for root, dirs, files in os.walk(category_dir):
            for filename in sorted(files):
                # Skip non-document files
                if not (filename.endswith('.pdf') or filename.endswith('.epub') or
                       filename.endswith('.md') or filename.endswith('.html') or
                       filename.endswith('.txt')):
                    continue

                file_path = Path(root) / filename
                relative_path = file_path.relative_to(LIBRARY_ROOT)

                # Generate ID
                category_short = category_name.split('_')[0]
                entry_id = f"{category_short}{counter:03d}"
                counter += 1

                # Extract title and author from file metadata first
                file_suffix = file_path.suffix.lower()  # With dot for comparison
                file_ext = file_suffix.lstrip('.')       # Without dot for storage
                meta_title = None
                meta_author = None
                
                if file_suffix == '.pdf':
                    meta_title, meta_author = extract_pdf_metadata(file_path)
                elif file_suffix == '.epub':
                    meta_title, meta_author = extract_epub_metadata(file_path)
                
                # Use metadata if available, otherwise clean filename
                title = meta_title if meta_title and len(meta_title) > 3 else clean_title(filename)
                author = meta_author if meta_author else extract_author_from_filename(filename)

                # Determine subjects and DDC
                cat_info = CATEGORY_INFO[category_name]
                subjects = list(cat_info["default_subjects"])
                subjects.extend(get_subcategory_subjects(relative_path))
                # Remove duplicates while preserving order
                subjects = list(dict.fromkeys(subjects))
                
                # Extract DDC numbers from path
                ddc_numbers = extract_ddc_from_path(relative_path)
                # Add main category DDC if exists
                if cat_info["ddc"]:
                    main_ddc = cat_info["ddc"]
                    # Use most specific DDC (last in list) or main category
                    ddc = ddc_numbers[-1] if ddc_numbers else main_ddc
                else:
                    ddc = ddc_numbers[-1] if ddc_numbers else None

                # Create entry
                entry = {
                    "id": entry_id,
                    "title": title,
                    "author": author,
                    "subjects": subjects,
                    "ddc": ddc,
                    "category": str(relative_path.parent),
                    "file_path": str(relative_path),
                    "file_type": file_ext
                }

                catalog.append(entry)

    return {"catalog": catalog}

def main():
    print("Generating catalog from library structure...")
    catalog_data = generate_catalog()

    print(f"Found {len(catalog_data['catalog'])} items")

    # Write catalog
    with open(CATALOG_FILE, 'w') as f:
        json.dump(catalog_data, f, indent=2)

    print(f"Catalog written to {CATALOG_FILE}")
    print("\nSample entries:")
    for entry in catalog_data['catalog'][:5]:
        print(f"  {entry['id']}: {entry['title']} - {entry['file_path']}")

if __name__ == '__main__':
    main()
