---
name: normalize-profile
description: Normalize a raw Decidalo `profile` MCP response into the flat list-of-dicts shape that enrich-information and map-profile expect. Use right after fetching a profile via the official Decidalo MCP profile tool, before enriching or mapping.
---

# Normalize Profile

The official Decidalo MCP `profile` tool returns each collection section in a
**columnar** `{ "columns": [...], "rows": [[...]] }` encoding, wrapped in an
envelope (`body.items[0]`, plus — in the CLI — an extra content-block layer
`[{ "type": "text", "text": "<json>" }]`). The downstream scripts
(`$enrich-information`, `$map-profile`) expect a **flat object with lists of
dicts** (`{ "overview": {...}, "projects": [...], "skills": [...], ... }`).

`normalize_profile.py` bridges the two: it peels the envelope and converts every
columnar section to a list of dicts, leaving flat sections (`overview`) and
already-list sections untouched. **Use this bundled script — never write ad-hoc
normalization code per run.**

## Steps

1. Call the official `profile` MCP tool (`mcp__claude_ai_Decidalo__profile`) for
   the UserID, requesting the sections you need with `content='inline'`.
2. Save the **full response verbatim** to a file, e.g.
   `output/<user_id>_profile_mcp.json` (the wrapped content-block form is fine —
   the script tolerates it).
3. Normalize to the canonical raw profile:

```bash
python3 skills/normalize-profile/scripts/normalize_profile.py \
  --input output/<user_id>_profile_mcp.json \
  --output output/<user_id>_profile_raw.json
```

Pass `output/<user_id>_profile_raw.json` on to `$enrich-information` and
`$map-profile`.

## Notes

- **Row cells are left as-is.** A project's `skills` cell is already a list of
  `{id, name}` dicts — normalization only zips section `columns` with `rows`, it
  does not recurse into cell values.
- **Idempotent.** Feeding an already-normalized profile back in is a no-op, so
  it is safe to run even when unsure whether the input is columnar.
- The script reads the `body.items[0]` envelope, a bare `items` list, a
  content-block list, or an already-unwrapped profile object — whichever the
  runtime produced.
