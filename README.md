# Decidalo Sales Profile Agent

Ein Claude-Code-Plugin, das IT-Berater:innen-Profile aus Decidalo lädt und daraus
fertige Word-Sales-Profile (`.docx`) erzeugt — optional auf einen Zielkunden
zugeschnitten und nach einheitlichen Formatierungsregeln standardisiert.

Die Pipeline: **UserID auflösen (auch per Name) → Profil aus Decidalo holen →
Projektdaten anreichern → auf Template-Felder mappen → (optional) auf Kunden
tailoren → standardisieren → Word-Template füllen.**

Profilbild und Word-Vorlagen werden dabei aus Azure Blob Storage über den
`decidalo_api_wrapper`-MCP-Server bezogen — nicht mehr über Decidalo-Signed-URLs
oder lokale Dateien.

---

## Installation

Marketplace hinzufügen und Plugin installieren:

```
/plugin marketplace add Blueforte-GmbH/decidalo_agent
/plugin install decidalo-agent@decidalo-plugins
```

### Voraussetzungen

- **Kein API-Key nötig, aber OAuth-Login.** Der Decidalo-MCP-Server ist eine
  Azure Container App (`decidalo-api-wrapper…northeurope.azurecontainerapps.io/`,
  **Streamable-HTTP**-Transport), die den Decidalo-Import-Token serverseitig hält.
  Der Server ist eine **OAuth-geschützte Ressource** — der MCP-Client durchläuft
  beim ersten Verbinden automatisch den OAuth-Flow (Registrierung + Browser-Login).
  Status prüfen mit `/mcp`. Ein clientseitiger Decidalo-API-Key bzw. eine lokale
  `.env` ist nicht nötig.
- **Python-Abhängigkeiten** für die mitgelieferten Skripte:
  ```bash
  pip install -r requirements.txt
  ```

---

## Workflow

### CV erstellen

Erzeuge ein Sales Profile auf Basis der Decidalo-Daten:

```
/create_cv <UserID oder Name>
```

Dabei werden abgefragt (oder direkt mitgegeben):

| Eingabe | Bedeutung |
|---|---|
| **UserID oder Name** | Die Decidalo-UserID oder der Name der Person. Wird ein Name angegeben, löst das Plugin ihn per `get_profile_name_mapping` zur UserID auf (bei mehreren Treffern wird nachgefragt). |
| **Template** | `mit Name` oder `anonym` — welche Vorlage gefüllt wird. Die Vorlage wird automatisch aus dem Blob Storage geladen. |
| **Kundenname** *(optional)* | Ist ein Zielkunde angegeben, wird der CV inhaltlich/sprachlich auf dessen Branche, Werte und Tonalität zugeschnitten (Tailoring). Ohne Kunden bleibt der Text unverändert. |

Das Plugin durchläuft anschließend automatisch:

1. **Extraktion** — Profil aus Decidalo holen, Profilbild aus Blob Storage laden, Projektdaten anreichern, auf Template-Felder mappen.
2. **Tailoring** *(nur mit Kundenname)* — Kunde per Websuche recherchieren, Freitextfelder anpassen.
3. **Standardisierung** — Formatierungs-/Inhaltsregeln aus `rules/` anwenden.
4. **Befüllen** — gewähltes Word-Template aus Blob Storage laden, füllen und `.docx` schreiben.

Das fertige Dokument und alle Zwischen-Artefakte landen in `output/`.

> **Vorlagen & Profilbilder** liegen in Azure Blob Storage und werden zur Laufzeit
> über den `decidalo_api_wrapper`-MCP-Server geladen — keine manuelle Installation
> nötig. `/setup-templates` bleibt als **Offline-Fallback**, um lokale `.docx`-Kopien
> nach `./templates/` zu legen (`Sales Profil - mit Name.docx`,
> `Sales Profil - anonym.docx`; git-ignoriert).

---

## Befehle

| Befehl | Zweck |
|---|---|
| `/create_cv [UserID oder Name]` | Kompletten Export von der UserID/dem Namen bis zur `.docx` ausführen. |
| `/setup-templates [Pfade]` | Word-Vorlagen lokal installieren (Offline-Fallback; normalerweise kommen sie aus Blob Storage). |
| `/list-rules` | Aktive Standardisierungs-Regeln anzeigen. |
| `/edit-rules` | Standardisierungs-Regel hinzufügen oder ändern. |

---

## Standardisierungs-Regeln

Die `cv-standardizer`-Stufe wendet konfigurierbare Regeln auf die Freitextfelder
an, damit jedes Profil einheitlich aussieht. Jede Regel ist eine Markdown-Datei
in `rules/`.

- `/list-rules` zeigt alle aktiven Regeln, ihre betroffenen Felder und meldet
  unvollständige Regeln.
- `/edit-rules` legt eine neue Regel in kanonischer Struktur an (oder ändert eine
  bestehende), sodass neue Vorgaben in die Standardisierung aufgenommen werden.

Beispiel: [rules/01_beschreibungsformat.md](rules/01_beschreibungsformat.md) —
Tätigkeits- und Projektbeschreibungen als Stichpunkte.

---

## Output

Pro Export entstehen in `output/`:

```
<UserID>_profile_raw.json                       ← Rohdaten aus Decidalo
<UserID>_profile_enriched.json                  ← Projekttitel/-branchen ergänzt
<UserID>_template_data.json                     ← gemappt, bereit für Standardisierung
<UserID>_template_data_<kunde>.json             ← kundenspezifische Kopie (optional)
<UserID>_template_data_*_standardized.json      ← nach Standardisierung
<UserID>_candidate_picture.<ext>                ← Profilbild aus Blob Storage (dekodiert)
<UserID>_profile_manifest.json                  ← Verweise auf die JSON-Dateien
<Nachname>_<Vorname>_Salesprofil.docx           ← fertiges Word-Dokument
```

---

## Architektur

Das Plugin besteht aus spezialisierten Agents (`agents/`), die jeweils eine Stufe
der Pipeline übernehmen, und Skills (`skills/`) mit gebündelten Python-Skripten
für die eigentlichen Transformationen. Der `profile-export`-Agent orchestriert den
gesamten Ablauf und ist das, was `/create_cv` auslöst.

Die Word-Vorlagen nutzen **nicht** docxtpl/Jinja2, sondern Words native
`MERGEFIELD`-Felder plus ein eigenes `RangeStart`/`RangeEnd`-Schema für Listen.
Das Fill-Skill manipuliert `word/document.xml` direkt via `lxml`.

Vorlagen und Profilbilder kommen aus Azure Blob Storage über die Tools des
`decidalo_api_wrapper`-MCP-Servers (`list_template_blobs`/`download_template_blob`,
`list_image_blobs`/`download_image_blob`). Da diese Downloads als Text (base64/JSON)
zurückkommen, dekodiert der `fetch-blob`-Skill sie in echte lokale Dateien, bevor
das Fill-Skill sie einbettet.

Technische Details für die Weiterentwicklung stehen in
[CLAUDE.md](CLAUDE.md).
