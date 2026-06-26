---
name: map-profile
description: Convert raw or enriched Decidalo profile JSON into template-ready JSON whose keys match the Word MERGEFIELD and RangeStart names. Use after Decidalo profile extraction and optional enrichment, before filling Sales Profile Word templates.
---

# Map Profile

Use the bundled script to transform Decidalo profile JSON into the data structure expected by the Word template filler.

## Script

Run from the working directory:

```bash
python3 skills/map-profile/scripts/map_profile_to_template.py \
  --profile output/<user_id>_profile_enriched.json \
  --output output/<user_id>_template_data.json
```

If enrichment was skipped, pass the raw profile JSON as `--profile`.

## Output Contract

Write mapped data to `output/<user_id>_template_data.json`.

The output must contain template/range keys such as `CV`, `ProfessionalExperience`, `Projects`, `Certificates`, `Languages`, `Industries`, `SkillSection_Tools`, `SkillSection_Programmiersprachen`, `SkillSection_Methoden`, and `SkillSection_Skills`.
