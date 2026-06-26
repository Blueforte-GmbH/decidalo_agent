#!/usr/bin/env python3
"""
Enrich Decidalo project entries with title, description, and industry name.

The project data comes from the `get_project` MCP tool of the Decidalo Container App
(the token lives server-side in Azure — no API key on the client). This script no
longer makes any network calls itself. Instead the calling agent:

  1. Runs this script with --list-pending to learn which projectReferenceIds are
     still missing a title or industry.
  2. Calls the `get_project` MCP tool once per pending ID.
  3. Writes the raw responses to a details JSON file: {"<project_id>": <response>, ...}
     where each response is the get_project result (a JSON object or a JSON string).
  4. Runs this script with --details <file> to merge those responses into the profile.

Modes:
  --list-pending   Print a JSON array of projectReferenceIds needing enrichment.
  --details FILE   Merge get_project responses from FILE into the profile.
"""

import json
import sys
from pathlib import Path

try:
    import click
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


def _first(d: dict, *keys) -> str | None:
    for key in keys:
        val = d.get(key)
        if val:
            if isinstance(val, dict):
                return val.get("name") or val.get("Name") or None
            return str(val)
    return None


def _load_profile(profile_path: Path) -> tuple[dict, str, list[dict]]:
    with open(profile_path, encoding="utf-8") as f:
        data = json.load(f)

    # Support both "Projects" (template format) and "projects" (raw MCP format)
    projects_key = next((k for k in ("Projects", "projects") if isinstance(data.get(k), list)), None)
    if projects_key is None:
        click.echo("ERROR: No 'Projects' list found in the profile JSON", err=True)
        sys.exit(1)

    return data, projects_key, data[projects_key]


def _needs_enrichment(project: dict) -> tuple[bool, bool]:
    """Return (has_name, has_industry) for a project entry."""
    has_name = bool(_first(project, "projectName", "ProjectName"))
    has_industry = bool(_first(project, "industryName", "IndustryName"))
    return has_name, has_industry


def _coerce_details(raw) -> dict | None:
    """get_project may return a JSON object or a plain-text/JSON string. Normalize to dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except (json.JSONDecodeError, ValueError):
            return None
    return None


@click.command()
@click.option("--profile", "-p", required=True, help="Path to the profile JSON file")
@click.option("--details", "-d", default=None,
              help="Path to a JSON file mapping projectReferenceId -> get_project response")
@click.option("--list-pending", "list_pending", is_flag=True,
              help="Print a JSON array of projectReferenceIds that still need enrichment, then exit")
@click.option("--output", "-o", default=None, help="Output path (default: overwrites input file)")
def main(profile: str, details: str, list_pending: bool, output: str) -> None:
    """Enrich project entries in a Decidalo profile JSON with title, description, and industry."""

    profile_path = Path(profile)
    data, _projects_key, projects = _load_profile(profile_path)

    # --- Mode 1: list the project IDs the agent must fetch via get_project ---
    if list_pending:
        pending: list[int] = []
        for project in projects:
            ref_id = project.get("projectReferenceId") or project.get("ProjectReferenceId")
            if not ref_id:
                continue
            has_name, has_industry = _needs_enrichment(project)
            if has_name and has_industry:
                continue
            pending.append(int(ref_id))
        # Machine-readable list on stdout; human note on stderr.
        click.echo(json.dumps(pending))
        click.echo(f"{len(pending)} project(s) need enrichment via get_project", err=True)
        return

    # --- Mode 2: merge fetched get_project responses into the profile ---
    if not details:
        click.echo(
            "ERROR: Provide --details <file> with get_project responses, "
            "or --list-pending to see which projects need fetching.",
            err=True,
        )
        sys.exit(1)

    with open(details, encoding="utf-8") as f:
        details_map = json.load(f)
    if not isinstance(details_map, dict):
        click.echo("ERROR: --details file must be a JSON object {\"<project_id>\": <response>, ...}", err=True)
        sys.exit(1)

    enriched = 0
    for project in projects:
        ref_id = project.get("projectReferenceId") or project.get("ProjectReferenceId")
        if not ref_id:
            continue

        has_name, has_industry = _needs_enrichment(project)
        if has_name and has_industry:
            continue

        raw = details_map.get(str(ref_id))
        if raw is None:
            continue
        detail = _coerce_details(raw)
        if detail is None:
            click.echo(f"  WARNING: could not parse get_project response for project {ref_id}", err=True)
            continue

        props = detail.get("properties") or {}
        title = (props.get("name") or {}).get("value") or _first(detail, "title", "Title", "projectName", "ProjectName")
        description = (props.get("description") or {}).get("value")
        industry = (detail.get("industry") or {}).get("industryName") or _first(detail, "industryName", "IndustryName")

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
