---
description: Install your Sales Profile Word templates into the local templates/ folder. Run once after installing the plugin, then again whenever the template files change.
---

Install the Decidalo Sales Profile Word templates locally.

The `.docx` templates are not shipped with the plugin — each user provides their own.

If the user typed file path(s) after the command, treat them as the source template
file(s). Otherwise, ask the user for the path(s) to their template `.docx` file(s)
(named version and/or anonymised version).

Then use the `$setup-templates` skill to validate and copy the file(s) into
`./templates/` under the canonical names the fill step expects:

- `templates/Sales Profil - mit Name.docx`
- `templates/Sales Profil - anonym.docx`

User-provided arguments (file paths, if any): $ARGUMENTS
