#!/usr/bin/env python3
"""Install Decidalo Sales Profile Word templates into a local templates/ folder.

The .docx templates are company IP and are not shipped with the public plugin.
After installing the plugin, the user provides their own template files once and
this script copies them into ./templates/ under the canonical names the
fill-template step expects:

    templates/Sales Profil - mit Name.docx
    templates/Sales Profil - anonym.docx

Usage:
    python3 install_templates.py --named "/path/to/named.docx"
    python3 install_templates.py --anonymous "/path/to/anonym.docx"
    python3 install_templates.py --named "a.docx" --anonymous "b.docx"
    python3 install_templates.py --named "a.docx" --target /some/dir
"""

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

NAMED_FILENAME = "Sales Profil - mit Name.docx"
ANON_FILENAME = "Sales Profil - anonym.docx"


def is_valid_docx(path: Path) -> bool:
    """A .docx is a zip archive containing word/document.xml."""
    if not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path) as zf:
            return "word/document.xml" in zf.namelist()
    except zipfile.BadZipFile:
        return False


def has_mergefields(path: Path) -> bool:
    """Heuristic check that the document uses Word MERGEFIELD markers."""
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", "ignore")
        return "MERGEFIELD" in xml
    except Exception:
        return False


def install_one(src: str, target_dir: Path, canonical_name: str) -> dict:
    result = {"src": src, "dest": str(target_dir / canonical_name), "ok": False}
    src_path = Path(src).expanduser()

    if not src_path.exists():
        result["error"] = f"file not found: {src_path}"
        return result
    if not is_valid_docx(src_path):
        result["error"] = f"not a valid .docx (no word/document.xml): {src_path}"
        return result

    dest_path = target_dir / canonical_name
    shutil.copyfile(src_path, dest_path)
    result["ok"] = True
    result["mergefields"] = has_mergefields(dest_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Sales Profile Word templates locally.")
    parser.add_argument("--named", help="Path to the named ('mit Name') template .docx")
    parser.add_argument("--anonymous", help="Path to the anonymised ('anonym') template .docx")
    parser.add_argument(
        "--target",
        default="templates",
        help="Target templates directory (default: ./templates)",
    )
    args = parser.parse_args()

    if not args.named and not args.anonymous:
        parser.error("provide at least one of --named or --anonymous")

    target_dir = Path(args.target).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    if args.named:
        jobs.append((args.named, NAMED_FILENAME))
    if args.anonymous:
        jobs.append((args.anonymous, ANON_FILENAME))

    failures = 0
    for src, canonical in jobs:
        res = install_one(src, target_dir, canonical)
        if res["ok"]:
            note = "" if res.get("mergefields") else "  [WARN: no MERGEFIELD markers found]"
            print(f"OK   {res['src']}  ->  {res['dest']}{note}")
        else:
            failures += 1
            print(f"FAIL {res['src']}  ({res['error']})", file=sys.stderr)

    print()
    installed = [p.name for p in sorted(target_dir.glob("*.docx"))]
    print(f"templates/ now contains: {installed if installed else '(none)'}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
