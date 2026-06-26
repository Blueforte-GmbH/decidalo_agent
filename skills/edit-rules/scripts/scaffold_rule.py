#!/usr/bin/env python3
"""Scaffold a new standardization rule file in the rules/ folder.

Creates rules/<NN>_<slug>.md with the canonical structure the cv-standardizer
expects (Gilt für / Anforderung / Beispiel / Ausnahmen). The numeric prefix is
auto-incremented from the existing rule files so ordering stays consistent.

Sections you don't pass on the command line are written with a `TODO:` marker so
the calling skill can fill them in afterwards via Edit.

Usage:
    python3 scaffold_rule.py --title "Datumsformat vereinheitlichen"
    python3 scaffold_rule.py --title "..." --slug datumsformat \
        --fields "Projects[*].Duration,ProfessionalExperience[*].Duration" \
        --requirement "Alle Zeiträume als MM/YYYY – MM/YYYY."
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

TEMPLATE = """# Regel: {title}

**Gilt für:** {fields}

## Anforderung

{requirement}

## Beispiel

**Vorher:**
```
{before}
```

**Nachher:**
```
{after}
```

## Ausnahmen

{exceptions}
"""


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return value or "regel"


def next_prefix(rules_dir: Path) -> str:
    nums = []
    for p in rules_dir.glob("*.md"):
        m = re.match(r"(\d+)_", p.name)
        if m:
            nums.append(int(m.group(1)))
    nxt = (max(nums) + 1) if nums else 1
    return f"{nxt:02d}"


def format_fields(fields_arg: str | None) -> str:
    if not fields_arg:
        return "TODO: `Feld1`, `Feld2` — betroffene JSON-Felder als Backtick-Liste"
    parts = [f.strip() for f in fields_arg.split(",") if f.strip()]
    return ", ".join(f"`{p}`" for p in parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a new standardization rule.")
    parser.add_argument("--title", required=True, help="Rule title (after 'Regel: ')")
    parser.add_argument("--slug", help="Filename slug (default: derived from title)")
    parser.add_argument("--fields", help="Comma-separated JSON field paths the rule applies to")
    parser.add_argument("--requirement", help="The transformation requirement text")
    parser.add_argument("--before", help="Example input (before)")
    parser.add_argument("--after", help="Example output (after)")
    parser.add_argument("--exceptions", help="Exceptions text")
    parser.add_argument("--rules-dir", default="rules", help="Rules directory (default: ./rules)")
    args = parser.parse_args()

    rules_dir = Path(args.rules_dir).expanduser()
    rules_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(args.slug or args.title)
    prefix = next_prefix(rules_dir)
    dest = rules_dir / f"{prefix}_{slug}.md"

    if dest.exists():
        print(f"FAIL: rule file already exists: {dest}", file=sys.stderr)
        return 1
    # Guard against a same-slug rule under a different prefix
    for existing in rules_dir.glob(f"*_{slug}.md"):
        print(f"FAIL: a rule with slug '{slug}' already exists: {existing.name} "
              f"(use the edit flow to change it)", file=sys.stderr)
        return 1

    content = TEMPLATE.format(
        title=args.title,
        fields=format_fields(args.fields),
        requirement=args.requirement or "TODO: Beschreibe die Transformation präzise.",
        before=args.before or "TODO: Beispiel-Eingabe",
        after=args.after or "TODO: Beispiel-Ergebnis",
        exceptions=args.exceptions or "- TODO: Ausnahmen auflisten, oder „Keine.“",
    )
    dest.write_text(content, encoding="utf-8")

    print(f"OK: created {dest}")
    todos = [s for s in ("requirement", "before", "after", "exceptions", "fields")
             if not getattr(args, s)]
    if todos:
        print(f"Open TODOs to fill in: {', '.join(todos)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
