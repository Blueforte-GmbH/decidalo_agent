#!/usr/bin/env python3
"""
Normalize a raw Decidalo `profile` MCP response into the flat,
list-of-dicts shape that enrich_projects.py and map_profile_to_template.py
expect.

The official Decidalo MCP `profile` tool returns each collection section in a
columnar ``{"columns": [...], "rows": [[...]]}`` encoding, wrapped in an
envelope (``body.items[0]``, and in the CLI an extra content-block layer).
This script peels the envelope and converts every columnar section to a list
of dicts, leaving flat sections (``overview``) and already-list sections
untouched. It is idempotent: feeding it an already-normalized profile is a
no-op.
"""

import json
import sys
from pathlib import Path

try:
    import click
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


def extract_profile(data: object) -> dict:
    """Peel the MCP response envelope down to the profile object."""
    # CLI content-block wrapping: [{"type": "text", "text": "<json>"}]
    if isinstance(data, list):
        for block in data:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                try:
                    return extract_profile(json.loads(block["text"]))
                except json.JSONDecodeError:
                    continue
        if data and isinstance(data[0], dict):
            return data[0]
        raise click.ClickException("Could not locate a profile object in the list input.")

    if isinstance(data, dict):
        body = data.get("body")
        if isinstance(body, dict):
            data = body
        items = data.get("items")
        if isinstance(items, list) and items and isinstance(items[0], dict):
            return items[0]
        return data

    raise click.ClickException("Unexpected input shape — expected a JSON object or content-block list.")


def is_columnar(value: object) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("columns"), list)
        and isinstance(value.get("rows"), list)
    )


def columnar_to_dicts(section: dict) -> list[dict]:
    columns = section["columns"]
    return [dict(zip(columns, row)) for row in section["rows"]]


def normalize(profile: dict) -> dict:
    """Convert every columnar section to a list of dicts; leave the rest as-is."""
    out: dict = {}
    for key, value in profile.items():
        out[key] = columnar_to_dicts(value) if is_columnar(value) else value
    return out


@click.command()
@click.option("--input", "-i", "input_path", required=True,
              help="Path to the saved raw `profile` MCP response JSON.")
@click.option("--output", "-o", "output_path", required=True,
              help="Path for the normalized list-of-dicts profile JSON.")
def main(input_path: str, output_path: str) -> None:
    raw = json.loads(Path(input_path).read_text(encoding="utf-8"))
    profile = extract_profile(raw)
    normalized = normalize(profile)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {
        k: len(v) for k, v in normalized.items()
        if isinstance(v, list)
    }
    click.echo(f"Wrote {output_path}")
    click.echo(f"Section counts: {json.dumps(counts, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
