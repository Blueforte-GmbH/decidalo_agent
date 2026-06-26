#!/usr/bin/env python3
"""
Map a raw Decidalo profile export to the field structure expected by the
Word mailmerge templates in templates/.

The output keys intentionally match MERGEFIELD / RangeStart names used by
scripts/fill_template.py, for example CV, ProfessionalExperience, Projects,
SkillSection_Tools, Certificates, Languages, and Industries.
"""

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import click
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


TOOLS_CATEGORIES = {
    "Tools / Cloud Platforms",
    "Tools / Database",
    "Tools / Data frameworks",
    "Tools / Orchestration",
    "Tools / Analytics",
    "Tools / Data transformation & Data integration",
}

PROGRAMMING_CATEGORIES = {"Programming & Scripting"}
METHOD_CATEGORIES = {"Methods / Requirements Management", "Methods / Data modeling"}

TOOLS_FALLBACK_NAMES = {
    "Docker",
    "TensorFlow",
    "PyTorch",
    "Scikit-learn",
    "LangChain",
    "LangGraph",
    "Flask",
    "Next.js",
    "Polars",
    "Tableau",
    "MongoDB",
    "Apache Spark",
    "Apache Airflow",
    "dbt Core",
    "Vector Databases",
    "NoSQL Database",
    "Amazon Web Services",
    "AWS RDS",
    "AWS Bedrock",
    "AWS ECS",
    "Azure Cosmos DB",
    "Azure AI",
    "Azure Cloud",
}

PROGRAMMING_FALLBACK_NAMES = {"TypeScript"}
METHOD_FALLBACK_NAMES = {"Requirements Engineering", "Data Modeling"}


def strip_html(value: str | None) -> str:
    """Convert the small HTML fragments returned by Decidalo to plain text."""
    if not value:
        return ""

    text = re.sub(r"<li[^>]*>", "- ", value)
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fmt_date(value: str | None) -> str:
    """Format an ISO date as MM.YYYY, keeping unknown formats unchanged."""
    if not value:
        return ""

    normalized = value.replace("Z", "")
    try:
        return datetime.fromisoformat(normalized).strftime("%m.%Y")
    except ValueError:
        return value


def fmt_duration(start: str | None, end: str | None) -> str:
    start_value = fmt_date(start)
    end_value = fmt_date(end)
    if start_value and end_value:
        return f"{start_value} - {end_value}"
    return start_value or end_value or ""


def _name_item(name: str | None) -> dict[str, str]:
    return {"Name": name or ""}


def _skill_name(skill: Any) -> str:
    if isinstance(skill, str):
        return skill
    if isinstance(skill, dict):
        return skill.get("name") or skill.get("Name") or ""
    return str(skill)


def _certificate_date(cert: dict[str, Any]) -> str:
    year = cert.get("issueYear") or ""
    month = cert.get("issueMonth") or ""
    if month:
        return f"{month} {year}".strip()
    return str(year).strip()


def _category_matches(category: str, candidates: set[str]) -> bool:
    return any(category == candidate or category.startswith(candidate) for candidate in candidates)


def categorize_skills(skills: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    tools: list[dict[str, str]] = []
    programming: list[dict[str, str]] = []
    methods: list[dict[str, str]] = []
    other: list[dict[str, str]] = []

    for skill in skills:
        name = skill.get("name") or skill.get("Name") or ""
        category = skill.get("categoryName") or skill.get("CategoryName") or ""
        item = _name_item(name)

        if _category_matches(category, TOOLS_CATEGORIES) or name in TOOLS_FALLBACK_NAMES:
            tools.append(item)
        elif _category_matches(category, PROGRAMMING_CATEGORIES) or name in PROGRAMMING_FALLBACK_NAMES:
            programming.append(item)
        elif _category_matches(category, METHOD_CATEGORIES) or name in METHOD_FALLBACK_NAMES:
            methods.append(item)
        else:
            other.append(item)

    return {
        "SkillSection_Tools": tools,
        "SkillSection_Programmiersprachen": programming,
        "SkillSection_Methoden": methods,
        "SkillSection_Skills": other,
    }


def _first_text(data: dict[str, Any], *keys: str) -> str:
    lower_keys = {key.lower() for key in keys}
    for key, value in data.items():
        if key.lower() in lower_keys and isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _find_candidate_picture(profile: dict[str, Any]) -> str:
    direct_keys = (
        "CandidatePicture",
        "CandidatePictureUrl",
        "CandidatePictureSignedUrl",
        "ProfilePicture",
        "ProfilePictureUrl",
        "ProfilePictureSignedUrl",
        "profilePicture",
        "profilePictureUrl",
        "profilePictureSignedUrl",
        "pictureUrl",
        "pictureSignedUrl",
        "photoUrl",
        "photoSignedUrl",
        "signedUrl",
        "signed_url",
    )

    overview = profile.get("overview") or {}
    if isinstance(overview, dict):
        value = _first_text(overview, *direct_keys)
        if value:
            return value

    value = _first_text(profile, *direct_keys)
    if value:
        return value

    def walk(value: Any) -> str:
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(child, str) or not child.strip():
                    continue
                key_lower = key.lower()
                looks_like_picture = any(token in key_lower for token in ("picture", "photo", "avatar", "image"))
                looks_like_url = "url" in key_lower or child.startswith(("http://", "https://", "data:image/"))
                if looks_like_picture and looks_like_url:
                    return child.strip()
            for child in value.values():
                found = walk(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = walk(child)
                if found:
                    return found
        return ""

    return walk(profile)


def map_profile_to_template_data(profile: dict[str, Any]) -> dict[str, Any]:
    """Return template-shaped data for scripts/fill_template.py."""
    overview = profile.get("overview") or {}

    professional_experience = [
        {
            "JobTitle": item.get("position") or item.get("JobTitle") or "",
            "Description": strip_html(item.get("description") or item.get("Description") or "")
            or item.get("company")
            or item.get("Name")
            or "",
            "Duration": fmt_duration(item.get("startDate"), item.get("endDate")),
            "Name": item.get("company") or item.get("Name") or "",
        }
        for item in profile.get("professionalExperience") or []
    ]

    projects = [
        {
            "ProjectName": item.get("projectName") or item.get("ProjectName") or "",
            "ProjectPosition": item.get("projectPosition") or item.get("ProjectPosition") or "",
            "Duration": fmt_duration(item.get("startDate"), item.get("endDate")),
            "ProjectDescription": strip_html(
                item.get("projectDescription") or item.get("ProjectDescription") or ""
            ),
            "Contribution": strip_html(item.get("contribution") or item.get("Contribution") or ""),
            "CompanyIndustry": item.get("industryName") or item.get("IndustryName") or "",
            "Skills": [_name_item(_skill_name(skill)) for skill in item.get("skills", []) or []],
        }
        for item in profile.get("projects") or profile.get("Projects") or []
    ]

    certificates = []
    for cert in profile.get("certificates") or profile.get("Certificates") or []:
        name = cert.get("name") or cert.get("Name") or ""
        issuer = (cert.get("issuerOrganizationName") or "").strip()
        date_value = _certificate_date(cert)
        if issuer:
            name = f"{name} ({issuer})"
        if date_value:
            name = f"{name}, {date_value}"
        certificates.append(_name_item(name))

    languages = [
        _name_item(f"{item.get('name') or item.get('Name') or ''} - {item.get('languageLevel') or ''}".strip(" -"))
        for item in profile.get("languages") or profile.get("Languages") or []
    ]

    industries = [
        _name_item(item.get("name") or item.get("Name") or "")
        for item in profile.get("industries") or profile.get("Industries") or []
    ]

    skill_sections = categorize_skills(profile.get("skills") or profile.get("Skills") or [])
    candidate_picture = _find_candidate_picture(profile)

    cv_item = {
        "CandidateName": overview.get("displayName") or overview.get("CandidateName") or "",
        "CandidatePosition": overview.get("JobTitle") or overview.get("CandidatePosition") or "",
        "CandidatePicture": candidate_picture,
        "cpKontakt": overview.get("cpKontakt") or "",
        "ProfessionalExperience": professional_experience,
        "Projects": projects,
        "Certificates": certificates,
        "Languages": languages,
        "Industries": industries,
        **skill_sections,
    }

    return {
        "CandidateName": cv_item["CandidateName"],
        "CandidatePosition": cv_item["CandidatePosition"],
        "CandidatePicture": candidate_picture,
        "cpKontakt": cv_item["cpKontakt"],
        "CV": [cv_item],
        "ProfessionalExperience": professional_experience,
        "Projects": projects,
        "Certificates": certificates,
        "Languages": languages,
        "Industries": industries,
        **skill_sections,
    }


@click.command()
@click.option("--profile", "-p", required=True, help="Path to the raw Decidalo profile JSON")
@click.option("--output", "-o", required=True, help="Path for the template-shaped JSON output")
def main(profile: str, output: str) -> None:
    """Map a raw Decidalo profile JSON to template field/range names."""
    profile_path = Path(profile)
    if not profile_path.exists():
        click.echo(f"ERROR: Profile file not found: {profile}", err=True)
        sys.exit(1)

    with open(profile_path, encoding="utf-8") as f:
        data = json.load(f)

    output_data = map_profile_to_template_data(data)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    click.echo(f"Written: {output_path}")
    click.echo(f"ProfessionalExperience entries: {len(output_data['ProfessionalExperience'])}")
    click.echo(f"Projects entries: {len(output_data['Projects'])}")
    click.echo(f"Certificates: {len(output_data['Certificates'])}")
    click.echo(f"Languages: {len(output_data['Languages'])}")
    click.echo(f"Industries: {len(output_data['Industries'])}")
    click.echo(f"SkillSection_Tools: {len(output_data['SkillSection_Tools'])}")
    click.echo(f"SkillSection_Programmiersprachen: {len(output_data['SkillSection_Programmiersprachen'])}")
    click.echo(f"SkillSection_Methoden: {len(output_data['SkillSection_Methoden'])}")
    click.echo(f"SkillSection_Skills: {len(output_data['SkillSection_Skills'])}")


if __name__ == "__main__":
    main()
