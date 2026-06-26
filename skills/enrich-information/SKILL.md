---
name: enrich-information
description: Enrich raw Decidalo profile JSON with missing project title, description, and industry data via the Decidalo get_project MCP tool. Use when an agent has fetched a profile from Decidalo/MCP and needs to complete project information before mapping or rendering a Sales Profile.
---

# Enrich Information

Fill in missing project title, description, and industry on a raw Decidalo profile JSON.
Project data comes from the **`get_project` MCP tool** of the Decidalo Container App — the
API token lives server-side in Azure, so there is **no API key on the client side** and the
bundled script makes **no network calls** itself.

The flow is: ask the script which projects are still missing data → fetch each via the
`get_project` MCP tool → hand the responses back to the script to merge.

## Steps

1. **List the projects that need enrichment.** The script prints a JSON array of
   `projectReferenceId`s (projects missing a title or industry) on stdout:

   ```bash
   python3 skills/enrich-information/scripts/enrich_projects.py \
     --profile output/<user_id>_profile_raw.json \
     --list-pending
   ```

   If the array is empty, nothing needs fetching — skip to copying the raw file to
   `output/<user_id>_profile_enriched.json` (or just reuse the raw file downstream).

2. **Fetch each pending project via the `get_project` MCP tool.** Call the Decidalo
   `get_project` tool once per ID (cloud: `mcp__claude_ai_Decidalo__get_project`, local:
   `mcp__decidalo__get_project`), passing `project_id`.

3. **Collect the responses into a details file** at `output/<user_id>_project_details.json`,
   keyed by project ID. Each value is the raw `get_project` result (a JSON object or a
   JSON string — the script accepts both):

   ```json
   { "590": { ...get_project response... }, "612": "{...}" }
   ```

4. **Merge the fetched data into the profile:**

   ```bash
   python3 skills/enrich-information/scripts/enrich_projects.py \
     --profile output/<user_id>_profile_raw.json \
     --details output/<user_id>_project_details.json \
     --output output/<user_id>_profile_enriched.json
   ```

## Output Contract

Write the enriched JSON to `output/`. Keep the raw profile file unchanged so later agents
can inspect both artifacts.

Do not invent project names or industries. If `get_project` returns no usable data for a
project, leave that project's fields as they were and move on.
