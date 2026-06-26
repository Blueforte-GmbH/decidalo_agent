---
name: edit-rules
description: Add a new CV standardization rule or change an existing one in the rules/ folder. Use when the user wants the cv-standardizer to enforce something new (a new formatting or content rule) or to adjust/remove an existing rule. Keeps each rule in the canonical structure the cv-standardizer parses.
---

# Edit Rules

Standardization rules live as Markdown files in the `rules/` folder. Each file is
one rule that the cv-standardizer applies to a Sales Profile's free-text fields.
This skill adds new rules and changes existing ones while keeping the canonical
structure intact.

## Canonical rule structure

Every rule file must contain:

```markdown
# Regel: <Titel>

**Gilt für:** `Feld1`, `Feld2`

## Anforderung

<Was genau transformiert wird — präzise und eindeutig.>

## Beispiel

**Vorher:**
```
<Eingabe>
```

**Nachher:**
```
<Ergebnis>
```

## Ausnahmen

- <Ausnahmen, oder „Keine.“>
```

## Allowed fields

Rules may only target the free-text fields the standardizer is allowed to reshape:

- `ProfessionalExperience[*].Description`
- `Projects[*].ProjectDescription`
- `Projects[*].Contribution`
- and their mirror fields under `CV[*]`

Never write a rule that targets identity or structural fields (`CandidateName`,
`ProjectName`, `Duration`, `JobTitle`, `Skills[*].Name`, etc.) — the standardizer
will refuse them. A rule must reshape existing text only, never invent content.

## Workflow

### Adding a new rule

1. Get from the user: a short title, the affected field(s), the requirement, a
   before/after example, and any exceptions. Ask for anything missing.
2. Scaffold the file with the correct numeric prefix and structure:

```bash
python3 skills/edit-rules/scripts/scaffold_rule.py \
  --title "Datumsformat vereinheitlichen" \
  --fields "Projects[*].Duration" \
  --requirement "..." \
  --before "..." \
  --after "..." \
  --exceptions "..."
```

Pass whatever you have; omitted sections are written with `TODO:` markers.
3. If any `TODO:` markers remain (the script lists them), open the created file
   and fill them in with the Edit tool.
4. Confirm the result by running `$list-rules` (or `/list-rules`) and report the
   new rule to the user.

### Changing an existing rule

1. Run `$list-rules` to find the file, then Read it.
2. Edit the relevant section(s) with the Edit tool, preserving the canonical
   structure (do not drop required sections).
3. Confirm with `$list-rules`.

### Removing a rule

Delete the rule's `.md` file from `rules/` only when the user explicitly asks.
Renumbering the remaining files is optional — gaps in the numeric prefix are fine.

## Notes

- One rule per file. Keep titles and slugs distinct.
- After changing rules, re-run the `cv-standardizer` to apply them to a profile.
