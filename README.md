# Aufgaben

## 1. AI-Code-Review-Skript

In diesem Aufgabenblatt entwickelst du ein Skript, das den Prozess von Code Reviews durch KI-Integration automatisiert. Dein Ziel ist es, eine Pipeline zu erstellen, die Code nicht nur auf formale Korrektheit prüft, sondern auch inhaltlich analysiert und Verbesserungen vorschlägt.

Achte auf eine saubere Trennung der einzelnen Analyseschritte, um die Ergebnisse übersichtlich darzustellen.


### Teilaufgaben

1. Syntax-Review: Erstelle den ersten Baustein deines Skripts, der sich rein auf die formale Ebene des Codes konzentriert. Integriere hierfür eine Linter-CLI oder andere Mechanismen. Dieser Schritt dient dazu, Fehler abzufangen, bevor sie an die kostenintensiveren KI-Modelle weitergeleitet werden.


2. Semantisches Review: Erweitere dein Skript um eine inhaltliche Analyse mithilfe der Gemini CLI oder anderer APIs. Nachdem der Code den Syntax-Check bestanden hat, soll er nun auf Logik und Verständnis geprüft werden.

Sende den Code an die CLI/API, um logische Schwachstellen, Sicherheitslücken oder "Bad Practices" zu identifizieren.


3. Lösungen: Implementiere im letzten Schritt eine Funktionalität, die anbietet, die Datei mit der Lösung zu beschreiben. Vorher soll allerdings der Lösungsvorschlag präsentiert werden.

Hinweis: Generiere dir selbst fehlerhafte Codeschnipsel und probiere dein Tool daran. Suche dir die Programmiersprache selbst aus oder baue dein Tool für mehrere Programmiersprachen gleichzeitig!
