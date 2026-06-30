---
name: list-rules
description: List and summarize the CV standardization rules defined in the rules/ folder. Use when the user wants to see which standardization rules are active, what fields they affect, or to check whether the rules are well-formed before running the cv-standardizer.
---

# List Rules

The cv-standardizer applies every rule defined in the `rules/` folder to the
free-text fields of a Sales Profile. This skill gives an overview of those rules.

## Workflow

1. Run the bundled script to scan the `rules/` folder:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-.}"/skills/list-rules/scripts/list_rules.py
```

It prints, per rule file:
- the title,
- the JSON fields the rule applies to (`Gilt für`),
- the section headers present,
- a ⚠ warning if a canonical section (`Anforderung`, `Beispiel`, `Ausnahmen`)
  or the title is missing.

Use `--format json` for machine-readable output, or `--rules-dir <path>` for a
non-default location.

2. Summarize the result for the user in clear language: how many rules are active,
   what each one does, and which fields it touches.

3. If any rule is flagged as incomplete, point it out and offer to fix it with the
   `$edit-rules` skill (or `/edit-rules`).

## Notes

- This skill is read-only. To add or change a rule, use `$edit-rules`.
- If `rules/` is empty, tell the user no standardization rules are active — the
  cv-standardizer would then pass profiles through unchanged.
