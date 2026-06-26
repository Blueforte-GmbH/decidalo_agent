---
name: fill-template
description: Fill Blueforte/Decidalo Sales Profile Word templates from mapped template-ready JSON. Use when an agent has an output/*_template_data.json artifact and needs to render a .docx using templates/Sales Profil - mit Name.docx or templates/Sales Profil - anonym.docx.
---

# Fill Template

Use the bundled script to render a Word document from mapped profile data. If the
template contains `@@CandidatePicture@@`, provide the candidate picture signed URL
from Decidalo as `CandidatePicture` in the mapped JSON or via `--candidate-picture`.

## Script

List fields when debugging a template:

```bash
python3 skills/fill-template/scripts/fill_template.py \
  --list-fields \
  --template "templates/Sales Profil - mit Name.docx"
```

Fill the selected template:

```bash
python3 skills/fill-template/scripts/fill_template.py \
  --template "templates/Sales Profil - mit Name.docx" \
  --profile output/<user_id>_template_data.json \
  --output "output/<Nachname>_<Vorname>_Salesprofil.docx"
```

Use `templates/Sales Profil - anonym.docx` when the user requests the anonymised version.

If `output/<user_id>_template_data.json` does not contain `CandidatePicture`, use
the Decidalo MCP profile/detail tool for that UserID and take the profile picture
signed URL from the tool result. Then pass it to the script without modifying the
raw profile artifact:

```bash
python3 skills/fill-template/scripts/fill_template.py \
  --template "templates/Sales Profil - mit Name.docx" \
  --profile output/<user_id>_template_data.json \
  --candidate-picture "<signed profile picture URL from Decidalo MCP>" \
  --output "output/<Nachname>_<Vorname>_Salesprofil.docx"
```

The script replaces the literal placeholder `@@CandidatePicture@@` with an
embedded image. The image source may be a signed HTTPS URL, `data:image/...` URL,
or local image path.

## Templates

The `.docx` templates are not shipped with the plugin. If the requested template
under `templates/` does not exist, ask the user to install it first with the
`$setup-templates` skill (or `/setup-templates`).

## Input Contract

The `--profile` file must already be mapped by `$map-profile`. Do not pass raw Decidalo/MCP JSON directly to this skill.

`CandidatePicture` is optional for old artifacts. If the template still contains
`@@CandidatePicture@@` and no image source is available, report the missing
`CandidatePicture` field.

Save generated documents in `output/`.
