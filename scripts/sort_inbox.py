#!/usr/bin/env python3
"""Drive dlm-sort for a Humble-style inbox drop.

Newer O'Reilly/Humble PDFs are missing from Open Library or match the wrong
book. This driver:

1. Reads title/author from the PDF itself (exiftool, then title-page text)
2. Guesses a DDC number from the title + filename using this library's folders
3. Writes that native metadata with exiftool
4. Runs dlm-sort and refuses Open Library overwrites
5. Regenerates the catalog

Usage:
    Drop PDFs in DigitalLibrary/_Inbox, then:

        dlm-sort-inbox
        dlm-sort-inbox --dry-run
        dlm-sort-inbox --move-from ~/Downloads --since today
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pty
import re
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

_DEFAULT_LIBRARY = Path.home() / (
    "Library/CloudStorage/OneDrive-Personal/Documents/DigitalLibrary"
)
LIBRARY_ROOT = Path(
    os.environ.get("DLM_LIBRARY_ROOT", _DEFAULT_LIBRARY)
).expanduser().resolve()
INBOX = LIBRARY_ROOT / "_Inbox"
LOG_PATH = Path("/tmp/dlm_sort_inbox.log")

# DDC 23 numbers that map onto sorting_config.json:
#   005* -> 000_Computer_Science/005_Programming
#   006* -> 000_Computer_Science/006_Artificial_Intelligence
DDC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("006.31", ("machine learning", "deep learning", "neural network",
                "pytorch", "tensorflow", "scikit", "sklearn")),
    ("006.3", ("artificial intelligence", "generative ai", "large language",
               " llm ", "chatgpt", "openai", "langchain", "transformer",
               "causal inference", "causal")),
    ("006.312", ("data analysis", "data wrangling", "data quality",
                 "data science", "polars", "pandas")),
    ("005.54", ("excel", "spreadsheet")),
    ("005.1", ("test-driven", "test driven", " tdd ", "software testing")),
    ("005.133", ("python", "rust", "javascript", "typescript", "golang",
                 "programming", "devops", "command-line", "command line")),
]

SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in",
               "of", "on", "or", "the", "to", "with"}


def log(msg: str) -> None:
    line = msg if msg.endswith("\n") else msg + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line)


def run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def pdf_info(path: Path) -> dict[str, str]:
    result = run([
        "exiftool", "-s3", "-Title", "-Author", "-Creator", "-PageCount",
        str(path),
    ])
    keys = ["Title", "Author", "Creator", "PageCount"]
    values = (result.stdout or "").splitlines()
    info = dict(zip(keys, values + [""] * len(keys)))
    return {k: (info.get(k) or "").strip() for k in keys}


def metadata_is_bad(title: str, author: str, path: Path) -> bool:
    stem = path.stem.lower()
    t = (title or "").strip()
    a = (author or "").strip().lower()
    if not t or "_" in t or t.lower().endswith((".pdf", ".epub")):
        return True
    if t.lower().replace(" ", "") == stem.replace("-", "").replace("_", ""):
        # Filename-as-title is weak but acceptable if we also have an author.
        if not a or a in {"unknown", "anonymous", "none", "n/a"}:
            return True
    if not a or a in {"unknown", "anonymous", "none", "n/a"}:
        return True
    if re.fullmatch(r"[a-z0-9]{32}", a) or len(a) > 120:
        return True
    return False


def filename_to_title(stem: str) -> str:
    name = stem.replace("_", " ").replace("-", " ")
    name = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", name)
    name = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", name)
    try:
        import wordninja
        name = " ".join(wordninja.split(name))
    except Exception:
        name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)
    name = re.sub(
        r"\b(\d+)\s*(st|nd|rd|th)\s*edition\b",
        r"\1\2 Edition",
        name,
        flags=re.I,
    )
    name = re.sub(r"\s+", " ", name).strip()
    words = name.split()
    titled = []
    for i, w in enumerate(words):
        low = w.lower()
        if re.fullmatch(r"\d+(st|nd|rd|th)", low):
            titled.append(low)
        elif i != 0 and low in SMALL_WORDS:
            titled.append(low)
        else:
            titled.append(w[:1].upper() + w[1:] if w else w)
    return " ".join(titled)


def extract_author_from_text(text: str) -> str:
    """Best-effort author line from an O'Reilly-style title page."""
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and len(ln) < 120]
    joined = "\n".join(lines)
    m = re.search(
        r"\bby\s+([A-Z][^\n]{3,80}?)(?:\n|Copyright|$)",
        joined,
        re.S,
    )
    if m:
        return cleanup_author(m.group(1))
    # "Name & Name" or "Name, Name and Name" near the top
    for ln in lines[:40]:
        if re.search(r"\b(and|&)\b", ln) and re.match(r"^[A-Z][a-z]+ ", ln):
            if not re.search(r"\b(Python|Rust|Data|Guide|Cookbook|Edition)\b", ln):
                return cleanup_author(ln)
    return ""


def cleanup_author(raw: str) -> str:
    raw = raw.replace("&", ",").replace(" and ", ", ")
    raw = re.sub(r"\s+", " ", raw).strip(" ,")
    raw = re.sub(r",\s*,", ",", raw)
    return raw


def title_page_text(path: Path) -> str:
    result = run(["pdftotext", "-l", "4", str(path), "-"])
    return result.stdout or ""


def guess_ddc(title: str, filename: str) -> str:
    blob = f" {title} {filename} ".lower()
    blob = re.sub(r"[^a-z0-9]+", " ", blob)
    blob = f" {blob} "
    for ddc, needles in DDC_RULES:
        if any(n in blob for n in needles):
            return ddc
    return "005"


def prepare_file(path: Path) -> dict:
    info = pdf_info(path)
    title, author = info["Title"], info["Author"]
    text = title_page_text(path)
    if metadata_is_bad(title, author, path):
        guessed_title = filename_to_title(path.stem)
        guessed_author = extract_author_from_text(text) or info.get("Creator", "")
        if metadata_is_bad(guessed_title, guessed_author, path):
            # Title from filename is still useful even without author.
            title = guessed_title
            author = guessed_author
        else:
            title, author = guessed_title, guessed_author
        run([
            "exiftool", "-overwrite_original",
            f"-Title={title}",
            f"-Author={author}",
            str(path),
        ])
        source = "pdf/filename"
    else:
        source = "existing pdf metadata"
    ddc = guess_ddc(title, path.name)
    return {
        "file": path.name,
        "title": title,
        "author": author,
        "ddc": ddc,
        "source": source,
    }


def move_from(source: Path, since: str | None) -> list[Path]:
    source = source.expanduser()
    files = [p for p in source.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
    if since:
        if since == "today":
            cutoff = dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            cutoff = dt.datetime.strptime(since, "%Y-%m-%d")
        cutoff_ts = cutoff.timestamp()
        files = [p for p in files if p.stat().st_mtime >= cutoff_ts]
    INBOX.mkdir(parents=True, exist_ok=True)
    moved = []
    for p in files:
        dest = INBOX / p.name
        shutil.move(str(p), str(dest))
        moved.append(dest)
        log(f"moved {p.name} -> _Inbox")
    return moved


def drive_sort(ddc_by_file: dict[str, str]) -> int:
    pid, fd = pty.fork()
    if pid == 0:
        os.environ["PYTHONUNBUFFERED"] = "1"
        os.execvp("dlm-sort", ["dlm-sort"])

    os.set_blocking(fd, False)
    buf = ""
    current = None
    answered_upto = 0
    start = time.time()
    deadline = start + 30 * 60
    last_output = time.time()
    child_exited = False

    try:
        while True:
            now = time.time()
            if now > deadline:
                log("ERROR: overall timeout")
                os.kill(pid, 15)
                return 1
            if now - last_output > 180:
                log("ERROR: 3 minutes of silence")
                os.kill(pid, 15)
                return 1

            r, _, _ = select.select([fd], [], [], 0.5)
            chunk = b""
            if r:
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    chunk = b""
                if not chunk:
                    child_exited = True
                else:
                    last_output = time.time()
                    text = chunk.decode("utf-8", errors="replace")
                    sys.stdout.write(text)
                    sys.stdout.flush()
                    with LOG_PATH.open("a", encoding="utf-8") as f:
                        f.write(text)
                    buf += text

            for m in re.finditer(r"(?m)^Processing:\s+(\S+)", buf[answered_upto:]):
                current = m.group(1)

            pending = buf[answered_upto:]
            reply = None
            if re.search(r"Write metadata to file\? \[Y/n\]:\s*$", pending):
                # Keep PDF-native metadata. Open Library is wrong on new books.
                reply = "n"
                log("[driver] write OL metadata -> n")
            elif re.search(
                r"Enter DDC manually to file this book \(or Enter to skip\):\s*$",
                pending,
            ):
                reply = ddc_by_file.get(current or "", "005")
                log(f"[driver] DDC for {current} -> {reply}")
            elif re.search(
                r"Would you like to define a new subcategory for DDC .+\? \(y/N\):\s*$",
                pending,
            ):
                reply = "n"
                log("[driver] new subcategory -> n")
            elif re.search(r"Enter DDC prefix to match \(default .+\):\s*$", pending):
                reply = ""
            elif re.search(r"Enter subfolder name .+:\s*$", pending):
                reply = ""

            if reply is not None:
                os.write(fd, (reply + "\n").encode("utf-8"))
                answered_upto = len(buf)
                last_output = time.time()

            if child_exited:
                try:
                    _, status = os.waitpid(pid, 0)
                except ChildProcessError:
                    status = 0
                return 0 if os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0 else 1
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned title/author/DDC and exit")
    parser.add_argument("--move-from", type=Path,
                        help="Move PDFs from this directory into _Inbox first")
    parser.add_argument("--since", default=None,
                        help="With --move-from: 'today' or YYYY-MM-DD")
    parser.add_argument("--no-catalog", action="store_true",
                        help="Skip dlm-catalog after sorting")
    args = parser.parse_args()

    if LOG_PATH.exists():
        LOG_PATH.unlink()

    if args.move_from:
        move_from(args.move_from, args.since)

    files = sorted(
        p for p in INBOX.iterdir()
        if p.is_file() and not p.name.startswith(".")
    )
    if not files:
        log(f"Inbox is empty: {INBOX}")
        return 0

    log(f"Preparing {len(files)} file(s) in {INBOX}")
    plans = []
    for path in files:
        plan = prepare_file(path)
        plans.append(plan)
        log(f"  {plan['file']}")
        log(f"    title : {plan['title']}")
        log(f"    author: {plan['author']}")
        log(f"    ddc   : {plan['ddc']}  ({plan['source']})")

    if args.dry_run:
        log("dry-run: not running dlm-sort")
        return 0

    ddc_by_file = {p["file"]: p["ddc"] for p in plans}
    status = drive_sort(ddc_by_file)
    if status != 0:
        log(f"dlm-sort failed with status {status}")
        return status

    if not args.no_catalog:
        log("Regenerating catalog...")
        cat = run(["dlm-catalog"], timeout=180)
        sys.stdout.write(cat.stdout)
        if cat.stderr:
            sys.stderr.write(cat.stderr)
        if cat.returncode != 0:
            return cat.returncode
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
