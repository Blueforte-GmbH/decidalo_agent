# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Fetches IT-consultant profiles from the Decidalo MCP API and renders them into Word Sales Profile `.docx` files. The pipeline is: resolve UserID (from a name if needed) → fetch raw JSON → enrich project metadata → map to template keys → fill Word template. The candidate picture and the Word templates are pulled from Azure Blob Storage through the `decidalo_api_wrapper` MCP server (not from Decidalo signed URLs or local files).

## Plugin installation

This repository is a Claude Code plugin and marketplace (`decidalo-plugins`, containing the `decidalo-agent` plugin). Others install it by adding the marketplace and installing the plugin:

```
/plugin marketplace add Blueforte-GmbH/decidalo_agent
/plugin install decidalo-agent@decidalo-plugins
```

The plugin source is pinned to the `github` source type tracking the default branch (no SHA pin) in `.claude-plugin/marketplace.json`. The repo must be reachable by the installer — for Claude Cowork (cloud) that means public, or a private repo its GitHub integration can read.

## Setup (local development)

```bash
pip install -r requirements.txt   # lxml, click, requests
```

The Decidalo MCP server is configured in `.mcp.json` — an Azure Container App wrapper (`decidalo-api-wrapper…northeurope.azurecontainerapps.io/`, **Streamable HTTP** transport, `type: "http"`) that holds the Decidalo Import API token **server-side**. The wrapper itself is an **OAuth-protected resource** (`/.well-known/oauth-protected-resource`, scope `mcp.access`, dynamic client registration), so the MCP client must complete an OAuth flow on first connect — the client handles registration and the browser login automatically; check status with `/mcp`. No Decidalo Import API key is needed client-side (that token stays server-side); the OAuth login gates access to the wrapper.

**MCP tool naming + runtime gotcha (read this before debugging "tool not found"):** the wrapper's tools are `get_profile_name_mapping`, `get_project`, `list_image_blobs`, `download_image_blob`, `list_template_blobs`, `download_template_blob`.

⚠️ `mcp__claude_ai_Decidalo__*` is **NOT** the wrapper — it is a *separate, official* Decidalo connector (profile/catalog/candidates/resource-plan/CV-export tools, ~14 of them). Its `profile` and `search_catalog` tools overlap enough to fetch a profile and resolve a name, but it has **no** `get_project` and **no** blob tools. So `profile-fetcher` deliberately uses this official connector for the profile, while the wrapper does name mapping, `get_project`, and blobs.

Where the wrapper is actually callable depends on the **runtime** — this is the important part:

- **Local CLI** (verified working) — `.mcp.json` names the server `decidalo_api_wrapper`, so the tools are exposed to the model as `mcp__decidalo_api_wrapper__*` and work directly. (A user-level copy in `~/.claude.json` named `decidalo-api-wrapper` would be `mcp__decidalo-api-wrapper__*`, hyphens — but a duplicate registration of the same URL can break tool exposure; keep just one.)
- **Claude Cowork / claude.ai (cloud)** — the cloud runtime only surfaces **claude.ai connectors** (`mcp__claude_ai_*`) to the model. A wrapper configured only via `.mcp.json`/`~/.claude.json` shows as "connected · 6 tools" in `/mcp` but its tools are **never exposed to the model**, so enrichment and blob downloads fail. To use the pipeline in the cloud, register the wrapper as a **custom claude.ai connector** (same URL, a name that does *not* collide with the official "Decidalo" connector, complete the OAuth login). It then surfaces under `mcp__claude_ai_<name>__*`.

For that reason every agent that needs the wrapper lists the candidate prefixes together — `mcp__decidalo_api_wrapper__*, mcp__decidalo-api-wrapper__*` (and `mcp__claude_ai_Decidalo__*` only where the official connector is genuinely used). Don't "normalize" these `tools:` lists to one form. Confirm what's actually connected (and under which name) with `/mcp`.

### Word templates (blob storage, with local fallback)

The `.docx` templates are company IP and are **not** shipped in the repo (`templates/*.docx` is git-ignored). They live in the `templates` blob container and are fetched at fill time through the `decidalo_api_wrapper` MCP server (`list_template_blobs` → `download_template_blob`, decoded to a local `.docx` with the `fetch-blob` skill).

As an **offline fallback**, you can still install your own copies locally with `/setup-templates`, or directly:

```bash
python3 skills/setup-templates/scripts/install_templates.py \
  --named "/path/to/named template.docx" \
  --anonymous "/path/to/anonymous template.docx"
```

This copies the files into `templates/` under the canonical names the fill step expects.

## Key commands

List all MERGEFIELD names in a template:
```bash
python3 skills/fill-template/scripts/fill_template.py --list-fields --template "templates/Sales Profil - mit Name.docx"
```

Run the three steps manually:
```bash
# 1. Enrich project metadata — data comes from the get_project MCP tool, so this is
#    two script calls around the MCP fetch (no API key in the script):
#    a) list which projects need data
python3 skills/enrich-information/scripts/enrich_projects.py \
  --profile output/<user_id>_profile_raw.json --list-pending
#    b) call get_project for each ID, save responses to output/<user_id>_project_details.json,
#       then merge:
python3 skills/enrich-information/scripts/enrich_projects.py \
  --profile output/<user_id>_profile_raw.json \
  --details output/<user_id>_project_details.json \
  --output output/<user_id>_profile_enriched.json

# 2. Map to template-ready JSON
python3 skills/map-profile/scripts/map_profile_to_template.py \
  --profile output/<user_id>_profile_enriched.json \
  --output output/<user_id>_template_data.json

# 3. Fill Word template
python3 skills/fill-template/scripts/fill_template.py \
  --template "templates/Sales Profil - mit Name.docx" \
  --profile output/<user_id>_template_data.json \
  --output "output/<Nachname>_<Vorname>_Salesprofil.docx"
```

There is no automated test suite or linter. Verify changes by running the pipeline end-to-end against a real UserID and opening the resulting `.docx`, and use `--list-fields` to confirm a template's MERGEFIELDs match what the mapper produces. `list_rules.py` doubles as a validator for rule files.

## Plugin structure

```
.claude-plugin/
  plugin.json          ← Plugin manifest (name, version, author)
  marketplace.json     ← Marketplace listing for /plugin marketplace add
agents/                ← Agents
skills/                ← Skills with bundled Python scripts
commands/              ← Slash commands
rules/                 ← Standardization rules consumed by cv-standardizer
templates/             ← Word templates (.docx git-ignored; fetched from blob storage, local copy = offline fallback)
output/                ← Per-export JSON + .docx artifacts (git-ignored)
requirements.txt       ← Python deps for the bundled scripts
.mcp.json              ← MCP server config (server name: `decidalo_api_wrapper`)
.claude/
  settings.json        ← Permissions
  settings.local.json
```

## Agent pipeline

The export is split into **single-responsibility sub-agents** in `agents/`, chained by the `/create_cv` command (the orchestration lives in the command, run by the main thread — there is no separate orchestrator agent, so the main thread can both spawn the sub-agents and ask the user the interactive questions):

- `profile-name-resolver` — name → UserID via `get_profile_name_mapping` (wrapper), with an official `search_catalog (name, …)` fallback. Skipped if a numeric UserID was given.
- `profile-fetcher` — UserID → full profile via the **official** Decidalo MCP `profile` tool; normalizes the columnar `{columns, rows}` sections to lists of dicts; writes `output/<user_id>_profile_raw.json`.
- `project-enricher` — enriches project title/description/industry via the wrapper `get_project` tool (`$enrich-information`), then maps to template-ready JSON (`$map-profile`); writes `output/<user_id>_profile_enriched.json` and `output/<user_id>_template_data.json`.
- `cv-tailoring` — *optional*; researches a target customer via web search and rewrites free-text fields in the mapped JSON; writes `output/<user_id>_template_data_<customer_slug>.json`.
- `cv-standardizer` — applies formatting/content rules from `rules/` to the most recent template data JSON; writes `output/<user_id>_template_data_*_standardized.json`.
- `profile-image-fetcher` — UserID → candidate picture via the wrapper `download_image_blob` (+ `$fetch-blob`); returns a local image path. Runs right before `project-filler`.
- `project-filler` — fetches the Word template from blob storage (`download_template_blob` + `$fetch-blob`), calls `$fill-template` on the standardized JSON, passes the picture via `--candidate-picture`; writes `.docx`.

Which MCP server each agent uses: **wrapper** (`decidalo_api_wrapper`) for name mapping, `get_project`, and blob downloads; **official** Decidalo connector (`mcp__claude_ai_Decidalo__*`) for the profile itself.

Slash commands (in `commands/`):
- `/create_cv [UserID or name]` — orchestrates the whole pipeline end-to-end (accepts a name; resolved via `profile-name-resolver`). The chain lives in this command, not a sub-agent.
- `/resolve-id [name]` — resolves a person's name to their UserID only (via `get_profile_name_mapping`, with a `search_catalog` fallback); fetches/generates nothing.
- `/setup-templates [paths]` — installs the `.docx` templates locally as an offline fallback (see `setup-templates` skill)
- `/list-rules` — shows active standardization rules
- `/edit-rules` — adds or changes a standardization rule

Skills in `skills/` bundle the Python scripts (`enrich-information`, `map-profile`, `fill-template`, `fetch-blob` for decoding blob downloads into local files, plus `setup-templates` as an offline template fallback). Agents must use the bundled skill scripts — no ad-hoc transformation code.

The `/setup-templates` command installs the `.docx` templates into `templates/` as an offline fallback (see [Word templates](#word-templates-blob-storage-with-local-fallback)); templates are normally fetched from blob storage at fill time.

## Word template engine (important)

**The templates do NOT use docxtpl or Jinja2 syntax.** They use Word's native MERGEFIELD format and a custom `RangeStart`/`RangeEnd` marker scheme. The fill script directly manipulates `word/document.xml` XML via `lxml`.

- **Scalar fields**: `«MERGEFIELD FieldName»` — e.g. `CandidateName`, `CandidatePosition`
- **List ranges**: a `RangeStart:ListName` marker and a `RangeEnd:ListName` marker bracket template blocks that get cloned once per list item
- **Nested ranges**: e.g. `Skills` inside `Projects` — expanded recursively
- **Candidate picture**: the placeholder text `@@CandidatePicture@@` in a paragraph is replaced by an embedded image. `CandidatePicture` is now a **local image path** (downloaded from the `profile-images` blob container via `download_image_blob` and decoded with the `fetch-blob` skill); `load_image_source` in `fill_template.py` also still accepts `data:` and HTTPS URLs.

## Template data structure

`map_profile_to_template.py` produces this JSON shape:

```json
{
  "CandidateName": "...",
  "CandidatePosition": "...",
  "CandidatePicture": "<signed URL>",
  "cpKontakt": "...",
  "CV": [{ ...same keys... }],
  "ProfessionalExperience": [{ "JobTitle", "Description", "Duration", "Name" }],
  "Projects": [{ "ProjectName", "ProjectPosition", "Duration", "ProjectDescription", "Contribution", "CompanyIndustry", "Skills": [{"Name"}] }],
  "Certificates": [{ "Name" }],
  "Languages": [{ "Name" }],
  "Industries": [{ "Name" }],
  "SkillSection_Tools": [{ "Name" }],
  "SkillSection_Programmiersprachen": [{ "Name" }],
  "SkillSection_Methoden": [{ "Name" }],
  "SkillSection_Skills": [{ "Name" }]
}
```

Skills are bucketed by `categoryName` — see `TOOLS_CATEGORIES`, `PROGRAMMING_CATEGORIES`, `METHOD_CATEGORIES` sets in `map_profile_to_template.py`, plus hard-coded fallback name lists for uncategorized skills.

## Enrichment

Project metadata is fetched via the **`get_project` MCP tool** of the Decidalo Container App (an Azure Container App that runs the MCP server and holds the Import API token as a server-side env var — clients authenticate to the wrapper via OAuth, not with the Import API token). `enrich_projects.py` itself makes **no network calls** and needs **no API key**; it has two modes:

- `--list-pending` — prints a JSON array of `projectReferenceId`s that have a reference but are missing `projectName`/`industryName`. The agent calls `get_project(project_id=…)` for each.
- `--details <file>` — merges the collected `get_project` responses (`{"<id>": <response>}`, object or JSON string) back into the profile. Enriched fields are title, description, and industry.

The agent orchestrates the loop (list → get_project per ID → save to `output/<user_id>_project_details.json` → merge); the script keeps all parsing/merge logic. See the `enrich-information` skill for the exact steps.

> Note: the Import API token lives server-side in the Azure Container App wrapper. `.mcp.json` points at the wrapper's Streamable HTTP endpoint, which is OAuth-protected — clients log in via OAuth (no client-side Decidalo Import API key needed) and that login gates both enrichment and profile fetch.

## Name resolution & blob storage assets

Beyond profile/enrichment data, the `decidalo_api_wrapper` MCP server exposes:

- **`get_profile_name_mapping`** — resolves a person's name to a Decidalo UserID, so users can ask for a CV by name instead of ID. The agent disambiguates multiple matches with the user.
- **`list_image_blobs` / `download_image_blob(blob_name)`** — candidate pictures in the `profile-images` container, pathed by id (e.g. `"<user_id>/photo.jpg"`). `download_image_blob` returns the image bytes (base64).
- **`list_template_blobs` / `download_template_blob(blob_name)`** — Word templates in the `templates` container (e.g. `"Sales Profil - mit Name.docx"`). `download_template_blob` returns `{name, encoding, size, content}` (base64 for the binary `.docx`).

These blob downloads come back as **text** (base64/JSON), so the agent saves the response and decodes it to a real local file with the **`fetch-blob` skill** (`skills/fetch-blob/scripts/save_blob.py`) before passing the path to `$fill-template` (`--template` / `--candidate-picture`). Agents cannot write binary directly with the Write tool — always route blob bytes through `fetch-blob`.

## Output artifacts per export

```
output/<user_id>_profile_raw.json                                  ← from MCP, unmodified
output/<user_id>_project_details.json                              ← raw get_project responses, keyed by ID (enrichment input)
output/<user_id>_profile_enriched.json                             ← project titles/industries added
output/<user_id>_template_data.json                                ← mapped, ready for standardizer
output/<user_id>_image_blob.b64                                    ← raw download_image_blob payload (decode input)
output/<user_id>_candidate_picture.<ext>                           ← candidate picture decoded from blob storage
output/<user_id>_template_blob.json                                ← raw download_template_blob response (decode input)
output/<user_id>_template_data_<customer_slug>.json                ← customer-tailored copy (optional)
output/<user_id>_template_data_standardized.json                   ← after standardizer, no tailoring
output/<user_id>_template_data_<customer_slug>_standardized.json   ← after tailoring + standardizer
output/<Nachname>_<Vorname>_Salesprofil.docx
```

## Rules

Formatting and content rules for the `cv-standardizer` agent live in `rules/` at the project root. Each `.md` file in that folder defines one rule category. Active rules:

- [rules/01_beschreibungsformat.md](rules/01_beschreibungsformat.md) — Tätigkeitsbeschreibungen als Stichpunkte mit `\n`-Zeilenumbrüchen

Manage rules with the bundled skills instead of editing by hand:

- `/list-rules` (`$list-rules`) — list active rules, their affected fields, and flag any incomplete rule (missing section or `TODO:` placeholder). Script: `skills/list-rules/scripts/list_rules.py`.
- `/edit-rules` (`$edit-rules`) — add a new rule (scaffolded with the correct numeric prefix and canonical structure) or change/remove an existing one. Script: `skills/edit-rules/scripts/scaffold_rule.py`.

Each rule file follows the canonical structure: `# Regel: <Titel>`, a `**Gilt für:**` field list, and `## Anforderung` / `## Beispiel` / `## Ausnahmen` sections. To add a rule manually, create a new `.md` file in `rules/` with that structure.

## Available templates

The `.docx` templates are not shipped with the plugin — they are fetched from blob storage at fill time (`download_template_blob` + `fetch-blob`), or installed locally as an offline fallback with `/setup-templates` (see [Word templates](#word-templates-blob-storage-with-local-fallback)). The fill step expects these canonical filenames under `templates/`:

- `templates/Sales Profil - mit Name.docx` — named version
- `templates/Sales Profil - anonym.docx` — anonymised version
