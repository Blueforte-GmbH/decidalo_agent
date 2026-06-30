---
name: fill-template
description: Fill Blueforte/Decidalo Sales Profile Word templates from mapped template-ready JSON. Use when an agent has an output/*_template_data.json artifact and needs to render a .docx using templates/Sales Profil - mit Name.docx or templates/Sales Profil - anonym.docx.
---

# Fill Template

Use the bundled script to render a Word document from mapped profile data. If the
template contains `@@CandidatePicture@@`, provide the candidate picture as
`CandidatePicture` in the mapped JSON or via `--candidate-picture`. The picture is
a **local image path** (downloaded from blob storage — see `$fetch-blob`); a
`data:` URL or HTTPS URL also works.

The template `.docx` itself comes from blob storage too: download it with
`download_template_blob` and decode it to a local `.docx` with `$fetch-blob`, then
pass that path to `--template`.

## Script

List fields when debugging a template:

```bash
bin/py.sh skills/fill-template/scripts/fill_template.py \
  --list-fields \
  --template "templates/Sales Profil - mit Name.docx"
```

Fill the selected template:

```bash
bin/py.sh skills/fill-template/scripts/fill_template.py \
  --template "templates/Sales Profil - mit Name.docx" \
  --profile output/<user_id>_template_data.json \
  --output "output/<Nachname>_<Vorname>_Salesprofil.docx"
```

Use `templates/Sales Profil - anonym.docx` when the user requests the anonymised version.

If `output/<user_id>_template_data.json` does not contain `CandidatePicture`,
fetch the image from blob storage with `$fetch-blob` (`list_image_blobs` →
`download_image_blob` → decode to a local file) and pass it to the script without
modifying the raw profile artifact:

```bash
bin/py.sh skills/fill-template/scripts/fill_template.py \
  --template "templates/Sales Profil - mit Name.docx" \
  --profile output/<user_id>_template_data.json \
  --candidate-picture "output/<user_id>_candidate_picture.jpg" \
  --output "output/<Nachname>_<Vorname>_Salesprofil.docx"
```

The script replaces the literal placeholder `@@CandidatePicture@@` with an
embedded image. The image source may be a local image path, `data:image/...` URL,
or signed HTTPS URL.

## Templates

Templates live in blob storage and are fetched with `$fetch-blob`
(`list_template_blobs` → `download_template_blob` → decode to a local `.docx`).
A copy installed locally via `$setup-templates` works as an offline fallback.

## Input Contract

The `--profile` file must already be mapped by `$map-profile`. Do not pass raw Decidalo/MCP JSON directly to this skill.

`CandidatePicture` is optional for old artifacts. If the template still contains
`@@CandidatePicture@@` and no image source is available, report the missing
`CandidatePicture` field.

Save generated documents in `output/`.
