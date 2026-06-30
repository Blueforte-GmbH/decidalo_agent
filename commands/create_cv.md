---
description: Export a Decidalo Sales Profile as a Word .docx file — resolves the name, fetches & enriches the profile, optionally tailors it to a target customer, standardizes formatting, fetches the photo, and fills the Word template.
---

Orchestrate the Decidalo Sales Profile export end-to-end. You (the main thread) run the chain and spawn each specialized sub-agent in sequence. Handle every user-facing question yourself — sub-agents cannot ask the user.

UserID or person name (and any other context the user typed): $ARGUMENTS

## Collect inputs upfront

- Require a Decidalo **UserID or a person's name**. If neither was given, ask for it.
- Ask whether there is a **target customer** for this CV (for optional tailoring). If yes, note the company name; if no, skip tailoring.
- Ask whether the user wants the **named** (`Sales Profil - mit Name.docx`) or **anonymised** (`Sales Profil - anonym.docx`) version. Do not assume a default.

## Pipeline (spawn one sub-agent per step)

1. **`profile-name-resolver`** — only if a name was given (not a numeric UserID). Pass the name; get back the UserID. If it reports multiple matches, ask the user to disambiguate before continuing.

2. **`profile-fetcher`** — pass the UserID. Produces `output/<user_id>_profile_raw.json`.

3. **`project-enricher`** — pass the UserID / raw file path. Enriches via `get_project` and maps to `output/<user_id>_template_data.json` (also writes `output/<user_id>_profile_enriched.json`).

4. **`cv-tailoring`** *(only if a target customer was provided)* — adapts free-text fields in `output/<user_id>_template_data.json`; writes `output/<user_id>_template_data_<customer_slug>.json`. Skip this step entirely if there is no target customer.

5. **`cv-standardizer`** — applies the `rules/` to the most recent template data file (tailored if present, else base); writes `output/<user_id>_template_data_<customer_slug>_standardized.json` or `output/<user_id>_template_data_standardized.json`.

6. **`profile-image-fetcher`** — pass the UserID. Returns the local candidate-picture path (or reports none available).

7. **`project-filler`** — pass the standardized template data file, the chosen template version (named/anonymised), and the candidate-picture path from step 6 (as `--candidate-picture`). Produces `output/<Nachname>_<Vorname>_Salesprofil.docx`.

## Report

List all generated artifact paths (raw, enriched, mapped, tailored, standardized, picture, `.docx`) and any fields that had no data (e.g. missing project titles, no candidate picture).

## Hard rules

- Use only the bundled scripts in `skills/*/scripts/` (via the sub-agents). No ad-hoc transformation code.
- Never modify `output/<user_id>_template_data.json` in place — the tailored copy is always a separate file.
- Do not pass raw Decidalo JSON to the Word filler.
