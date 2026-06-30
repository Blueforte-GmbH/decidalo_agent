---
description: Resolve a Decidalo person's name to their UserID via get_profile_name_mapping (with a search_catalog fallback).
---

Resolve a Decidalo person's name to their numeric UserID and report it.

Name to resolve (from the user): $ARGUMENTS

If no name was provided after the command, ask the user for the person's name first.

Steps:

1. Call the **`get_profile_name_mapping`** MCP tool with the given name. Tool name by runtime:
   - installed plugin: `mcp__plugin_decidalo-agent_decidalo_api_wrapper__get_profile_name_mapping`
   - local project dev (repo `.mcp.json`): `mcp__decidalo_api_wrapper__get_profile_name_mapping`
   - cloud (custom connector): the wrapper tool under its registered connector name


1. Report the result:
   - **Exactly one match** → output the person's display name and their UserID plainly (e.g. `Lukas Petersdorf → UserID 74`).
   - **Multiple matches** → list each candidate (name + UserID + any distinguishing field like role/company) and ask the user which one they mean. Do not guess.
   - **No match** → say so and suggest the user check the spelling.

Do not fetch the profile, enrich, or generate any files — this command only resolves the name to a UserID.
