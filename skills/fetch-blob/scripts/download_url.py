#!/usr/bin/env python3
"""
Download an HTTPS/SAS URL to a local file.

Used for Word templates returned by the wrapper's `get_template_download_url`
tool and for candidate pictures returned by `get_image_download_url`. Signed
Azure SAS URLs are short-lived, so fetch a fresh URL and run this immediately.
"""

import sys
from pathlib import Path

try:
    import click
    import requests
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


@click.command()
@click.option("--url", "-u", required=True, help="HTTPS/SAS URL to download.")
@click.option("--output", "-o", "output_path", required=True, help="Local path to write the bytes to.")
@click.option("--timeout", default=30, show_default=True, help="Request timeout in seconds.")
def main(url: str, output_path: str, timeout: int) -> None:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if not resp.content:
        raise click.ClickException(
            "Downloaded 0 bytes. The SAS URL may be expired or wrong; fetch a fresh URL and retry."
        )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.content)

    click.echo(f"Wrote {output_path} ({len(resp.content)} bytes, {content_type or 'unknown type'})")


if __name__ == "__main__":
    main()
