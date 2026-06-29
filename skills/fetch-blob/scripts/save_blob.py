#!/usr/bin/env python3
"""Decode a download_*_blob MCP response into a local binary file.

The Decidalo wrapper's blob tools return file contents as text, not as a file on
disk:

- ``download_template_blob(blob_name)`` returns a dict
  ``{"name", "encoding": "utf-8"|"base64", "size", "content"}``.
- ``download_image_blob(blob_name)`` returns the raw image bytes as base64 text.

An agent cannot write binary with the Write tool, so it saves the tool response
(the dict, or the raw base64/data-URL string) to a file and runs this helper to
decode it and write the real bytes to ``--output``.

Accepts the payload from ``--input <file>`` or stdin. Handles:
- the full ``download_template_blob`` JSON dict (reads ``content`` + ``encoding``),
- a raw base64 string (optionally a ``data:<mime>;base64,...`` URL),
- a raw utf-8 text payload (with ``--encoding utf-8``).
"""

import base64
import json
import sys
from pathlib import Path

try:
    import click
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


def _extract(raw: str, encoding: str) -> bytes:
    """Return the decoded bytes for the given payload and encoding choice."""
    content = raw
    enc = encoding

    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict) and "content" in obj:
            content = obj["content"]
            if encoding == "auto":
                enc = obj.get("encoding", "base64")

    if enc == "auto":
        enc = "base64"

    if enc == "utf-8":
        return content.encode("utf-8")

    # base64 — tolerate a data: URL prefix and embedded whitespace/newlines.
    if content.lstrip().startswith("data:"):
        content = content.split(",", 1)[1]
    return base64.b64decode("".join(content.split()))


@click.command()
@click.option("--input", "-i", "input_path", default=None,
              help="File with the blob response (JSON dict or raw content). Omit to read stdin.")
@click.option("--output", "-o", required=True,
              help="Destination path for the decoded bytes (e.g. templates/... .docx).")
@click.option("--encoding", "-e", type=click.Choice(["auto", "base64", "utf-8"]), default="auto",
              help="How to decode. 'auto' reads a JSON dict's encoding field, else assumes base64.")
def main(input_path: str, output: str, encoding: str) -> None:
    raw = Path(input_path).read_text() if input_path else sys.stdin.read()
    if not raw.strip():
        raise click.ClickException("Empty input — nothing to decode.")

    try:
        data = _extract(raw, encoding)
    except (base64.binascii.Error, ValueError) as exc:
        raise click.ClickException(f"Could not decode blob content: {exc}")

    out = Path(output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    click.echo(f"Wrote {len(data)} bytes to {out}")


if __name__ == "__main__":
    main()
