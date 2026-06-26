---
name: enrich-information
description: Enrich raw Decidalo profile JSON with missing project title, description, and industry data via the Decidalo Import API. Use when an agent has fetched a profile from Decidalo/MCP and needs to complete project information before mapping or rendering a Sales Profile.
---

# Enrich Information

Use the bundled script to enrich project entries in a raw Decidalo profile JSON.

## Script

Run from the working directory:

```bash
python3 skills/enrich-information/scripts/enrich_projects.py \
  --profile output/<user_id>_profile_raw.json \
  --output output/<user_id>_profile_enriched.json
```

The script reads `DECIDALO_IMPORT_API_KEY` from the environment or a `.env` file in the working directory. Pass `--api-key` only when a key was provided explicitly.

Use `--verbose` only for debugging missing Import API fields.

## Output Contract

Write the enriched JSON to `output/`. Keep the raw profile file unchanged so later agents can inspect both artifacts.

If the Import API key is missing, stop and report that enrichment could not run; do not invent project names or industries.
