---
description: Save the Decidalo API key into a local .env file so the enrichment pipeline can run (e.g. in a Cowork session). Takes a token file or pasted token.
---

Write the Decidalo API key into a local `.env` file.

Use the `$setup-env` skill. If the user gave a file path or token after the
command, use it as the source; otherwise ask for the token (a file containing it,
or the pasted value). The skill saves it as `.env` (preserving any other
variables) and confirms with a masked key — it never echoes or commits the token.

Note: this enables the enrichment step only. The main Decidalo MCP access in
Cowork still needs the OAuth connector.

User-provided source (file path or token, if any): $ARGUMENTS
