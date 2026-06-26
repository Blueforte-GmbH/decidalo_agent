# Regel: Tätigkeitsbeschreibungen als Stichpunkte

**Gilt für:** `ProfessionalExperience[*].Description`, `Projects[*].ProjectDescription`, `Projects[*].Contribution`  
**sowie deren Spiegelfelder** in `CV[*].ProfessionalExperience[*].Description`, `CV[*].Projects[*].ProjectDescription`, `CV[*].Projects[*].Contribution`

## Anforderung

Tätigkeits- und Projektbeschreibungen sowie Beiträge werden als Stichpunkte mit je einem Zeilenumbruch dazwischen formatiert.

- Jeder Stichpunkt beginnt mit `• ` (Unicode-Aufzählungszeichen, dann Leerzeichen).
- Stichpunkte werden durch `\n` (einfacher Zeilenumbruch) getrennt — das Fill-Script rendert `\n` in JSON-Werten als Word-Zeilenumbruch (`<w:br/>`).
- Der Text eines Stichpunkts endet **ohne** abschließendes Satzzeichen, sofern er kein vollständiger Satz ist.
- Liegt der Text bereits als Stichpunktliste vor (erkennbar an `•`, `-` oder `*` am Zeilenanfang), wird er nur vereinheitlicht (alle Marker → `• `), nicht neu aufgeteilt.
- Fließtextsätze werden an Satzgrenzen (`. `) in einzelne Stichpunkte aufgeteilt.

## Beispiel

**Vorher (Fließtext):**
```
Konzeption und Umsetzung einer Microservice-Architektur. Enge Zusammenarbeit mit dem Product-Owner. Durchführung von Code-Reviews.
```

**Nachher (Stichpunkte):**
```
• Konzeption und Umsetzung einer Microservice-Architektur
• Enge Zusammenarbeit mit dem Product-Owner
• Durchführung von Code-Reviews
```

## Ausnahmen

- Felder mit weniger als 20 Zeichen bleiben unverändert (zu kurz zum Aufteilen).
- Wenn ein Feld bereits **ausschließlich** aus einem einzigen Stichpunkt besteht, wird kein `•` vorangestellt — der Text bleibt als Fließtext erhalten.
