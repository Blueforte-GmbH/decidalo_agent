---
name: fetch-blob
description: Decode a Decidalo wrapper download_*_blob MCP response (Word template or candidate image) into a local binary file. Use when an agent has called download_template_blob or download_image_blob and needs the bytes on disk for fill-template (--template / --candidate-picture).
---

# Fetch Blob

Templates and candidate pictures are stored in Azure Blob Storage and reached
through the `decidalo_api_wrapper` MCP server, not from local files or Decidalo
signed URLs. The download tools return file contents as **text** (a JSON dict or
base64), and an agent cannot write binary with the Write tool. This skill's
`save_blob.py` decodes that text and writes the real bytes to a local path that
`$fill-template` can consume.

## MCP tools (on `decidalo_api_wrapper`)

Cloud names are `mcp__claude_ai_Decidalo__*`; local CLI names are
`mcp__decidalo_api_wrapper__*`.

- `list_template_blobs` → template blob names in the `templates` container, e.g.
  `"Sales Profil - mit Name.docx"`, `"Sales Profil - anonym.docx"`.
- `download_template_blob(blob_name)` → `{ "name", "encoding": "utf-8"|"base64", "size", "content" }`.
- `list_image_blobs` → image blob names in the `profile-images` container,
  pathed by profile id, e.g. `"<user_id>/photo.jpg"`.
- `download_image_blob(blob_name)` → the image bytes (base64).

## Decode a template blob

1. Call `download_template_blob("Sales Profil - mit Name.docx")`.
2. Save the **full JSON response** verbatim to a file, e.g.
   `output/<user_id>_template_blob.json`.
3. Decode it to the canonical template path:

```bash
python3 skills/fetch-blob/scripts/save_blob.py \
  --input output/<user_id>_template_blob.json \
  --output "templates/Sales Profil - mit Name.docx"
```

Pass that `--output` path to `$fill-template` as `--template`.

## Decode a candidate image blob

1. Pick the right blob from `list_image_blobs` — the one whose name starts with
   `"<user_id>/"`.
2. Call `download_image_blob("<user_id>/photo.jpg")` and save its base64 content
   (or the `data:<mime>;base64,...` form) to a file, e.g.
   `output/<user_id>_image_blob.b64`.
3. Decode it to a local image, matching the blob's extension:

```bash
python3 skills/fetch-blob/scripts/save_blob.py \
  --input output/<user_id>_image_blob.b64 \
  --output output/<user_id>_candidate_picture.jpg
```

Pass that path to `$fill-template` as `--candidate-picture`, or set it as
`CandidatePicture` in the mapped JSON.

## Notes

- `--encoding auto` (default) reads the `encoding` field from a JSON dict and
  otherwise assumes base64; `data:` URL prefixes and embedded newlines are
  tolerated. Use `--encoding utf-8` only for text blobs.
- If a `download_image_blob` response is only available as rendered image content
  and its base64 text cannot be captured, skip the picture: render without it and
  report `CandidatePicture` as missing.
