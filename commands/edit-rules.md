---
description: Add a new CV standardization rule or change an existing one, so the cv-standardizer enforces new formatting/content requirements.
---

Add or change a CV standardization rule in the `rules/` folder.

Use the `$edit-rules` skill. If the user described a new rule, gather title,
affected field(s), requirement, before/after example, and exceptions (ask for what
is missing), then scaffold and fill the rule file. If they want to change an
existing rule, locate it via `$list-rules`, then edit it — always keeping the
canonical rule structure (Gilt für / Anforderung / Beispiel / Ausnahmen).

User request (what to add or change): $ARGUMENTS
