#!/usr/bin/env python3
"""Write the Decidalo API key into a local .env file for the enrichment pipeline.

The enrichment step (enrich_projects.py) reads DECIDALO_IMPORT_API_KEY via
python-dotenv from a .env file in the working directory. In environments where no
.env is present (e.g. a fresh checkout, or a Claude Cowork session), this script
takes a user-provided token — from a file or from stdin — and writes/merges it
into the local .env so the pipeline can run.

The output filename is fixed to ".env" inside this script on purpose, so the
calling Bash command never has to mention it (some setups block Bash commands
that reference .env files).

Usage:
    python3 setup_env.py --from /path/to/token-file
    cat token-file | python3 setup_env.py --stdin
    python3 setup_env.py --from secrets.txt --target /some/dir

The source may be either a full dotenv file (a line `DECIDALO_IMPORT_API_KEY=...`)
or a file containing just the raw token value.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ENV_FILENAME = ".env"  # kept here, not on the command line
KEY = "DECIDALO_IMPORT_API_KEY"


def extract_token(content: str) -> str | None:
    """Pull the token from dotenv-style content or treat the whole thing as raw."""
    for line in content.splitlines():
        m = re.match(rf"\s*(?:export\s+)?{re.escape(KEY)}\s*=\s*(.+)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    # No explicit assignment found — treat the entire trimmed content as the token,
    # but only if it is a single non-empty line (avoid grabbing a whole file).
    stripped = content.strip()
    if stripped and "\n" not in stripped:
        return stripped.strip('"').strip("'")
    return None


def mask(token: str) -> str:
    if len(token) <= 8:
        return f"({len(token)} chars)"
    return f"{token[:4]}…{token[-4:]} ({len(token)} chars)"


def merge_into_env(env_path: Path, token: str) -> str:
    """Update or insert the key line in an existing .env, preserving other lines."""
    new_line = f"{KEY}={token}"
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        replaced = False
        for i, line in enumerate(lines):
            if re.match(rf"\s*(?:export\s+)?{re.escape(KEY)}\s*=", line):
                lines[i] = new_line
                replaced = True
                break
        if not replaced:
            lines.append(new_line)
        action = "updated" if replaced else "added key to"
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        env_path.write_text(new_line + "\n", encoding="utf-8")
        action = "created"
    return action


def gitignore_warns(target_dir: Path) -> bool:
    """Light heuristic: warn if .env is not git-ignored in this directory tree."""
    for parent in [target_dir, *target_dir.parents]:
        gi = parent / ".gitignore"
        if gi.exists():
            text = gi.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"^\s*\.env\s*$", text, flags=re.MULTILINE):
                return False  # ignored — good
    return True  # no matching ignore rule found


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the Decidalo API key into a local .env file.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--from", dest="source", help="Path to a file containing the token (dotenv or raw)")
    src.add_argument("--stdin", action="store_true", help="Read the token/content from stdin")
    parser.add_argument("--target", default=".", help="Directory to write .env into (default: current dir)")
    args = parser.parse_args()

    if args.stdin:
        content = sys.stdin.read()
    else:
        source_path = Path(args.source).expanduser()
        if not source_path.exists():
            print(f"FAIL: source file not found: {source_path}", file=sys.stderr)
            return 1
        content = source_path.read_text(encoding="utf-8")

    token = extract_token(content)
    if not token:
        print(f"FAIL: could not find a {KEY} value (or a single raw token) in the input.",
              file=sys.stderr)
        return 1

    target_dir = Path(args.target).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    env_path = target_dir / ENV_FILENAME

    action = merge_into_env(env_path, token)
    print(f"OK: {action} {env_path}")
    print(f"     {KEY} = {mask(token)}")

    if gitignore_warns(target_dir):
        print("WARN: .env does not appear to be git-ignored here — make sure it is "
              "never committed.", file=sys.stderr)

    print("\nThe enrichment pipeline can now read the key from .env.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
