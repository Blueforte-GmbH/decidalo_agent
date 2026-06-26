#!/usr/bin/env python3
"""
Enrich Decidalo project entries with title and industry name from the Import API.

Each project needs a "projectReferenceId" field — the MCP profile tool returns this
when projectName/industryName are null. The Import API fills in those gaps.

API key priority:
  1. --api-key / -k CLI flag
  2. DECIDALO_IMPORT_API_KEY environment variable
  3. .env file in the project root
"""

import json
import os
import sys
from pathlib import Path

try:
    import click
    import requests
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
    for candidate in (Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parent.parent):
        env_path = candidate / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass

API_URL = "https://import.decidalo.app/importapi/Project"


def fetch_project_details(project_id: int, api_key: str, verbose: bool = False) -> dict | None:
    try:
        resp = requests.get(
            API_URL,
            params={"projectid": project_id},
            headers={"accept": "text/plain", "X-Api-Key": api_key},
            timeout=10,
        )
        if verbose:
            click.echo(f"  HTTP {resp.status_code} — raw: {resp.text[:300]}")
        if resp.status_code == 200:
            return resp.json()
        click.echo(f"  WARNING: HTTP {resp.status_code} for project {project_id}", err=True)
    except requests.RequestException as e:
        click.echo(f"  Request error for project {project_id}: {e}", err=True)
    return None


def _first(d: dict, *keys) -> str | None:
    for key in keys:
        val = d.get(key)
        if val:
            if isinstance(val, dict):
                return val.get("name") or val.get("Name") or None
            return str(val)
    return None


@click.command()
@click.option("--profile", "-p", required=True, help="Path to the profile JSON file")
@click.option("--api-key", "-k", default=None, help="Import API key (or DECIDALO_IMPORT_API_KEY env var)")
@click.option("--output", "-o", default=None, help="Output path (default: overwrites input file)")
@click.option("--verbose", "-v", is_flag=True, help="Print raw API responses to debug field names")
def main(profile: str, api_key: str, output: str, verbose: bool) -> None:
    """Enrich project entries in a Decidalo profile JSON with title and industry name."""

    api_key = api_key or os.environ.get("DECIDALO_IMPORT_API_KEY")
    if not api_key:
        click.echo(
            "ERROR: Provide --api-key or set DECIDALO_IMPORT_API_KEY in .env or environment",
            err=True,
        )
        sys.exit(1)

    profile_path = Path(profile)
    with open(profile_path, encoding="utf-8") as f:
        data = json.load(f)

    # Support both "Projects" (template format) and "projects" (raw MCP format)
    projects_key = next((k for k in ("Projects", "projects") if isinstance(data.get(k), list)), None)
    if projects_key is None:
        click.echo("ERROR: No 'Projects' list found in the profile JSON", err=True)
        sys.exit(1)

    projects: list[dict] = data[projects_key]
    enriched = 0

    for project in projects:
        ref_id = project.get("projectReferenceId") or project.get("ProjectReferenceId")
        if not ref_id:
            continue

        has_name = bool(_first(project, "projectName", "ProjectName"))
        has_industry = bool(_first(project, "industryName", "IndustryName"))

        if has_name and has_industry:
            continue

        click.echo(f"Fetching project {ref_id}…")
        details = fetch_project_details(int(ref_id), api_key, verbose)
        if details is None:
            continue

        if verbose:
            click.echo(f"  Available fields: {list(details.keys())}")

        props = details.get("properties") or {}
        title = (props.get("name") or {}).get("value") or _first(details, "title", "Title", "projectName", "ProjectName")
        description = (props.get("description") or {}).get("value")
        industry = (details.get("industry") or {}).get("industryName") or _first(details, "industryName", "IndustryName")

        if not has_name and title:
            key = "ProjectName" if "ProjectName" in project else "projectName"
            project[key] = title
            click.echo(f"  → Title:       {title}")

        if description:
            key = "projectDescription" if "projectDescription" in project else "ProjectDescription"
            if not project.get(key):
                project[key] = description
                click.echo(f"  → Description: {description[:80]}…" if len(description) > 80 else f"  → Description: {description}")

        if not has_industry and industry:
            key = "IndustryName" if "IndustryName" in project else "industryName"
            project[key] = industry
            click.echo(f"  → Industry:    {industry}")

        if title or industry:
            enriched += 1

    out_path = Path(output) if output else profile_path
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    click.echo(f"\nEnriched {enriched}/{len(projects)} projects → {out_path}")


if __name__ == "__main__":
    main()
