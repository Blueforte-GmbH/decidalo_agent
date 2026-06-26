# Templates

The Sales Profile Word templates are **not** shipped with this plugin (they are
company IP). Each user installs their own `.docx` files into this folder locally.

## Install your templates

After installing the plugin, run:

```
/setup-templates
```

and provide the path(s) to your template file(s). The skill copies them here under
the canonical names the fill step expects:

- `Sales Profil - mit Name.docx` — named version
- `Sales Profil - anonym.docx` — anonymised version

You can also run the bundled script directly:

```bash
python3 skills/setup-templates/scripts/install_templates.py \
  --named "/path/to/named template.docx" \
  --anonymous "/path/to/anonymous template.docx"
```

`*.docx` files in this folder are git-ignored and never committed.
