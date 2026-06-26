---
description: Export a Decidalo Sales Profile as a Word .docx file — fetches the profile, enriches project data, optionally tailors it to a target customer, and fills the Word template.
---

Trigger the split Decidalo Sales Profile export flow.

If the user provided a UserID or other context after the slash command, pass it as part of the task. Otherwise ask the user for the Decidalo UserID first.

Invoke the `profile-export` subagent with the following prompt, substituting $ARGUMENTS with any text the user typed after the command:

---

Generate a Sales Profile Word document for the following Decidalo UserID/person context (if specified): $ARGUMENTS

Follow the split profile-export workflow:
1. Use `profile-information-extractor` behavior to fetch the Decidalo profile by UserID
2. Save raw, enriched, mapped, and manifest JSON artifacts in `output/`
3. Ask the user whether they want the anonymised version or the version with name
4. Use `project-filler` behavior to fill the matching template from `output/<user_id>_template_data.json`
5. Save the generated `.docx` in `output/`
6. Report all generated artifact paths and any fields that had no data
