#!/usr/bin/env python3
"""List the standardization rules defined in the rules/ folder.

Each rule is one Markdown file in rules/ with this canonical structure:

    # Regel: <title>
    **Gilt für:** `field`, `field`
    ## Anforderung
    ...
    ## Beispiel
    ...
    ## Ausnahmen
    ...

This script scans every `*.md` file, extracts the title, the affected fields,
and the section headers, and reports any rule that is missing a canonical
section so it can be fixed before the cv-standardizer runs.

Usage:
    python3 list_rules.py
    python3 list_rules.py --rules-dir rules
    python3 list_rules.py --format json
"""

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = ["Anforderung", "Beispiel", "Ausnahmen"]


def parse_rule(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    title = None
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    fields = []
    gilt_match = re.search(r"\*\*Gilt für:\*\*\s*(.+)", text)
    if gilt_match:
        fields = re.findall(r"`([^`]+)`", gilt_match.group(1))

    sections = re.findall(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    section_names = [s.strip() for s in sections]

    missing = [s for s in REQUIRED_SECTIONS if not any(s.lower() in n.lower() for n in section_names)]
    has_todos = "TODO:" in text

    return {
        "file": path.name,
        "title": title or "(kein Titel gefunden)",
        "fields": fields,
        "sections": section_names,
        "missing_sections": missing,
        "has_todos": has_todos,
        "valid": title is not None and not missing and not has_todos,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="List standardization rules.")
    parser.add_argument("--rules-dir", default="rules", help="Rules directory (default: ./rules)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    rules_dir = Path(args.rules_dir).expanduser()
    if not rules_dir.is_dir():
        print(f"No rules directory found at: {rules_dir}", file=sys.stderr)
        return 1

    rule_files = sorted(rules_dir.glob("*.md"))
    rules = [parse_rule(p) for p in rule_files]

    if args.format == "json":
        print(json.dumps({"rules_dir": str(rules_dir), "count": len(rules), "rules": rules},
                         indent=2, ensure_ascii=False))
        return 0

    if not rules:
        print(f"No rules defined in {rules_dir} (no *.md files).")
        return 0

    print(f"{len(rules)} Regel(n) in {rules_dir}/\n")
    for r in rules:
        flag = "" if r["valid"] else "  ⚠"
        print(f"• {r['file']}{flag}")
        print(f"    Titel:   {r['title']}")
        if r["fields"]:
            print(f"    Gilt für: {', '.join(r['fields'])}")
        else:
            print("    Gilt für: (keine Felder angegeben)")
        print(f"    Sektionen: {', '.join(r['sections']) if r['sections'] else '(keine)'}")
        if r["missing_sections"]:
            print(f"    ⚠ Fehlende Pflicht-Sektionen: {', '.join(r['missing_sections'])}")
        if r["has_todos"]:
            print("    ⚠ Enthält noch TODO-Platzhalter")
        print()

    invalid = [r["file"] for r in rules if not r["valid"]]
    if invalid:
        print(f"⚠ Unvollständige Regeln (vor dem Standardisieren korrigieren): {', '.join(invalid)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
