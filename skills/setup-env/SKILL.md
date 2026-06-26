---
name: setup-env
description: Write the Decidalo API key into a local .env file so the enrichment pipeline can read it. Use when DECIDALO_IMPORT_API_KEY is not available as an environment variable — for example in a fresh checkout or a Claude Cowork session where env vars are not injected. Takes a user-provided token (a file or pasted value) and saves it as .env.
---

# Setup Env

The enrichment step (`enrich_projects.py`) reads `DECIDALO_IMPORT_API_KEY` via
python-dotenv from a `.env` file in the working directory. When that variable is
not present in the environment — notably in **Claude Cowork**, where env vars are
not passed to MCP servers or scripts — this skill writes the key into a local
`.env` so enrichment can run.

> This only enables the **enrichment** step (a REST call to `import.decidalo.app`).
> The main Decidalo MCP data access in Cowork still requires the OAuth connector,
> not this `.env`. See CLAUDE.md / README for the connector setup.

## Inputs

The user provides their Decidalo API token. Accept it either as:
- a **file path** the user gives (their own `.env`, or any file containing the
  token), or
- the **raw token value** (pasted), which you pass via stdin.

The source may be a full dotenv file (a `DECIDALO_IMPORT_API_KEY=...` line) or a
file/line containing just the raw token.

## Workflow

1. Get the source from the user (file path or pasted token). Ask if missing.

2. Write the key into `.env` using the bundled script. The script hard-codes the
   `.env` output filename, so your Bash command never mentions it.

   From a file:
   ```bash
   python3 skills/setup-env/scripts/setup_env.py --from "/path/to/token-file"
   ```

   From a pasted token (pipe it in — avoid putting the secret in argv):
   ```bash
   printf '%s' "<TOKEN>" | python3 skills/setup-env/scripts/setup_env.py --stdin
   ```

   The script:
   - extracts the token (dotenv line or raw value),
   - creates or updates `.env`, preserving any other variables already in it,
   - prints a **masked** confirmation (never the full key),
   - warns if `.env` is not git-ignored.

3. Confirm to the user that enrichment can now run, and remind them that in Cowork
   the `.env` is per-session (ephemeral) and must be re-supplied each session.

## Safety

- Never echo the full token back to the user; the script masks it.
- Never commit `.env` (it is git-ignored in this repo).
- Do not write the token into any tracked file or into command output.
