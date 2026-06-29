---
name: setup-templates
description: Install Decidalo Sales Profile Word templates into the local templates/ folder as an OFFLINE FALLBACK. Templates normally come from blob storage via the decidalo_api_wrapper MCP server (list_template_blobs / download_template_blob + $fetch-blob); use this skill only when blob access is unavailable or to pin a custom local copy. Takes the user's own .docx files (by path) and copies them under the canonical names the fill-template step expects.
---

# Setup Templates

> **Note:** Templates are normally fetched from blob storage at fill time via the
> `decidalo_api_wrapper` MCP server (`list_template_blobs` / `download_template_blob`,
> decoded with `$fetch-blob`). This skill is an **offline fallback** for installing
> a local copy when blob access is unavailable.

The Sales Profile Word templates are company IP and are **not** shipped with the
plugin. This skill copies the user-provided `.docx` files into `./templates/`
under the canonical names the fill step expects:

- `templates/Sales Profil - mit Name.docx` — named version
- `templates/Sales Profil - anonym.docx` — anonymised version

## Inputs

The user provides the path(s) to their template `.docx` file(s). They may provide
one or both. Accept paths given as arguments to the command, or ask for them.

If the user is unsure which file is which, the named template contains the
candidate's real name; the anonymised one does not.

## Workflow

1. Determine the source path(s) from the user. Ask for whichever is missing.
2. Run the bundled script to validate and copy the file(s) into `./templates/`:

```bash
python3 skills/setup-templates/scripts/install_templates.py \
  --named "/path/to/the/named template.docx" \
  --anonymous "/path/to/the/anonymous template.docx"
```

Both flags are optional — pass only the one(s) the user provided. The script:
- creates `./templates/` if needed,
- verifies each file is a real `.docx` (zip containing `word/document.xml`),
- warns if a file contains no `MERGEFIELD` markers (likely the wrong document),
- copies it to the canonical filename.

3. Report which templates are now installed (the script prints the final
   `templates/` contents).

## Notes

- Templates are stored at project level (`./templates/`). Run this skill once per
  project working directory where you generate Sales Profiles.
- Re-running the skill overwrites existing templates with the new files.
- A `[WARN: no MERGEFIELD markers found]` message means the document probably is
  not a valid Sales Profile template — double-check the source file with the user.
