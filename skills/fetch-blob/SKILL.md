---
name: fetch-blob
description: Save Decidalo wrapper blob assets to local files. Use download_url.py for short-lived SAS URLs returned by get_template_download_url, or save_blob.py for legacy download_*_blob base64/JSON responses.
---

# Fetch Blob

Templates and candidate pictures are stored in Azure Blob Storage and reached
through the `decidalo_api_wrapper` MCP server. Templates are fetched by asking
the wrapper for a short-lived SAS URL and downloading it to a local `.docx`.
Legacy blob tools may still return file contents as **text** (a JSON dict or
base64); `save_blob.py` decodes that text and writes the real bytes to a local
path that `$fill-template` can consume.

## MCP tools (on `decidalo_api_wrapper`)

Cloud names are `mcp__claude_ai_Decidalo__*`; local CLI names are
`mcp__decidalo_api_wrapper__*`.

- `list_template_blobs` → template blob names in the `templates` container, e.g.
  `"Sales Profil - mit Name.docx"`, `"Sales Profil - anonym.docx"`.
- `get_template_download_url(blob_name)` → a short-lived SAS URL for the
  template. The URL is valid for 15 minutes.
- `download_template_blob(blob_name)` → `{ "name", "encoding": "utf-8"|"base64", "size", "content" }`.
- `list_image_blobs` → image blob names in the `profile-images` container,
  pathed by profile id, e.g. `"<user_id>/photo.jpg"`.
- `get_image_download_url(blob_name)` → a short-lived SAS URL for the candidate
  picture. The URL is valid for ~15 minutes.
- `download_image_blob(blob_name)` → the image bytes (base64). Legacy fallback.

## Download a template blob through SAS URL

1. Call `list_template_blobs` and confirm the exact blob name exists.
2. Call `get_template_download_url("Sales Profil - mit Name.docx")`.
3. Extract the SAS URL from the response and download it immediately:

```bash
bin/py.sh skills/fetch-blob/scripts/download_url.py \
  --url "<sas-url-from-get_template_download_url>" \
  --output "templates/Sales Profil - mit Name.docx"
```

Pass that `--output` path to `$fill-template` as `--template`.

Use `download_template_blob` + `save_blob.py` only as a legacy fallback if the
SAS URL tool is unavailable.

## Download a candidate image through SAS URL

1. Pick the right blob from `list_image_blobs` — the one whose name starts with
   `"<user_id>/"`.
2. Call `get_image_download_url("<user_id>/photo.jpg")` and extract the SAS URL.
3. Download it immediately, matching the blob's extension:

```bash
bin/py.sh skills/fetch-blob/scripts/download_url.py \
  --url "<sas-url-from-get_image_download_url>" \
  --output output/<user_id>_candidate_picture.jpg
```

Pass that path to `$fill-template` as `--candidate-picture`, or set it as
`CandidatePicture` in the mapped JSON.

Use `download_image_blob` + `save_blob.py` only as a legacy fallback if the SAS
URL tool is unavailable:

```bash
bin/py.sh skills/fetch-blob/scripts/save_blob.py \
  --input output/<user_id>_image_blob.b64 \
  --output output/<user_id>_candidate_picture.jpg
```

## Notes

- `--encoding auto` (default) reads the `encoding` field from a JSON dict and
  otherwise assumes base64; `data:` URL prefixes and embedded newlines are
  tolerated. Use `--encoding utf-8` only for text blobs.
- If a `download_image_blob` response is only available as rendered image content
  and its base64 text cannot be captured, skip the picture: render without it and
  report `CandidatePicture` as missing.
