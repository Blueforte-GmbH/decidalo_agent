# Decidalo Sales Profile Agent

Ein Claude-Code-Plugin, das IT-Berater:innen-Profile aus Decidalo lädt und daraus
fertige Word-Sales-Profile (`.docx`) erzeugt — optional auf einen Zielkunden
zugeschnitten und nach einheitlichen Formatierungsregeln standardisiert.

Die Pipeline: **Profil aus Decidalo holen → Projektdaten anreichern → auf
Template-Felder mappen → (optional) auf Kunden tailoren → standardisieren →
Word-Template füllen.**

---

## Installation

Marketplace hinzufügen und Plugin installieren:

```
/plugin marketplace add lpetersdorf/decidalo_agent
/plugin install decidalo-agent@decidalo-plugins
```

### Voraussetzungen

- **Decidalo API-Key:** Lege eine `.env` an (`cp .env.example .env`) und trage
  `DECIDALO_IMPORT_API_KEY` ein. Der Key wird für den MCP-Zugriff und die
  Projekt-Anreicherung benötigt.
- **Python-Abhängigkeiten** für die mitgelieferten Skripte:
  ```bash
  pip install -r requirements.txt
  ```

---

## Workflow

### Schritt 1 — Templates einmalig laden

Die Word-Vorlagen sind Firmen-IP und werden **nicht** mit dem Plugin
ausgeliefert. Lade deine eigenen `.docx`-Vorlagen einmal lokal:

```
/setup-templates
```

Gib die Pfade zu deinen Vorlagen an. Der Skill prüft sie und kopiert sie nach
`./templates/` unter den erwarteten Namen:

- `Sales Profil - mit Name.docx` — Version mit Namen
- `Sales Profil - anonym.docx` — anonymisierte Version

> Die `.docx` in `templates/` sind git-ignoriert und werden nie eingecheckt.
> Schritt 1 muss pro Arbeitsverzeichnis einmal ausgeführt werden.

### Schritt 2 — CV erstellen

Erzeuge ein Sales Profile auf Basis der Decidalo-Daten:

```
/create_cv <UserID>
```

Dabei werden abgefragt (oder direkt mitgegeben):

| Eingabe | Bedeutung |
|---|---|
| **UserID** | Die Decidalo-UserID der Person, deren Profil erzeugt wird. |
| **Template** | `mit Name` oder `anonym` — welche Vorlage gefüllt wird. |
| **Kundenname** *(optional)* | Ist ein Zielkunde angegeben, wird der CV inhaltlich/sprachlich auf dessen Branche, Werte und Tonalität zugeschnitten (Tailoring). Ohne Kunden bleibt der Text unverändert. |

Das Plugin durchläuft anschließend automatisch:

1. **Extraktion** — Profil per UserID aus Decidalo holen, Projektdaten anreichern, auf Template-Felder mappen.
2. **Tailoring** *(nur mit Kundenname)* — Kunde per Websuche recherchieren, Freitextfelder anpassen.
3. **Standardisierung** — Formatierungs-/Inhaltsregeln aus `rules/` anwenden.
4. **Befüllen** — gewähltes Word-Template füllen und `.docx` schreiben.

Das fertige Dokument und alle Zwischen-Artefakte landen in `output/`.

---

## Befehle

| Befehl | Zweck |
|---|---|
| `/setup-templates [Pfade]` | Word-Vorlagen lokal installieren (Schritt 1). |
| `/create_cv [UserID]` | Kompletten Export von der UserID bis zur `.docx` ausführen (Schritt 2). |
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
Das Fill-Skript manipuliert `word/document.xml` direkt via `lxml`.

Technische Details für die Weiterentwicklung stehen in
[CLAUDE.md](CLAUDE.md).
