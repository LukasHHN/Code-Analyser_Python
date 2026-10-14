code_review.py – KI-gestütztes Code Review in 3 Stufen

Ein Kommandozeilen-Tool für Python-Code, das Dateien oder ganze Projektordner in drei aufeinander aufbauenden Stufen prüft: erst schnell und regelbasiert per Linter, dann inhaltlich per KI (Claude über die Anthropic-API) und zuletzt mit der Möglichkeit, Verbesserungsvorschläge direkt in die Datei zu übernehmen.

Inhaltsverzeichnis
Funktionsweise
Voraussetzungen
Installation
API-Key einrichten
Verwendung
Optionen
JSON-Export
Projektstruktur
Exit-Codes
Grenzen und Hinweise
Sicherheit
Funktionsweise
Stufe	Name	Was passiert	KI-Anfrage
1	Syntaktische Analyse	Statische Code-Prüfung mit ruff. Findet Stil-, Syntax- und Importfehler in Sekunden.	nein
2	KI-Analyse	Claude prüft Logik, Lesbarkeit und mögliche Bugs. Die Linter-Ergebnisse aus Stufe 1 werden als Kontext mitgeschickt, damit Claude sie nicht doppelt meldet, sondern sich auf Logikprobleme konzentriert.	ja
3	Lösungsvorschlag und Umsetzung	Jede Verbesserung wird einzeln angezeigt und kann direkt auf die Datei angewendet werden.	ja

Stufe 2 läuft immer, auch wenn Stufe 1 Fehler gefunden hat. Stufe 3 startet nur, wenn Stufe 2 einen Report geliefert hat.

Voraussetzungen
Python 3.10 oder neuer
Ein Anthropic-API-Key (Anthropic Console)
Python-Pakete: ruff, anthropic, rich
Installation
bash
git clone <REPO-URL>
cd <REPO-ORDNER>

python -m venv .venv
# Windows (Git Bash):
source .venv/Scripts/activate
# Linux / macOS:
# source .venv/bin/activate

pip install ruff anthropic rich
API-Key einrichten

Das Tool benötigt den Key als Umgebungsvariable ANTHROPIC_API_KEY.

bash
# Git Bash / Linux / macOS
export ANTHROPIC_API_KEY="dein_key_hier"

# Windows PowerShell
$env:ANTHROPIC_API_KEY = "dein_key_hier"

Alternativ kannst du den Key in einer lokalen .env-Datei ablegen. Diese Datei darf nie ins Repository eingecheckt werden (siehe Sicherheit). Als Vorlage dient eine .env.example mit Platzhaltern:

ANTHROPIC_API_KEY=dein_key_hier
Verwendung
bash
# Einzelne Datei: alle drei Stufen
python code_review.py datei.py

# Ganzes Verzeichnis: Stufe 1 und 2 (Stufe 3 nur bei Einzeldateien)
python code_review.py ./mein_projekt/

# Nur der schnelle Linter, ohne KI
python code_review.py datei.py --only-lint

# Linter-Report als JSON speichern
python code_review.py datei.py --json-out report.json

# Nur bestimmte ruff-Regelgruppen prüfen
python code_review.py datei.py --select E,F,W
Optionen
Option	Beschreibung
target	Pfad zur Python-Datei oder zum Verzeichnis (Pflichtargument)
--only-lint	Nur Stufe 1 ausführen, keine KI-Anfragen
--json-out FILE	Ergebnisse als JSON in FILE speichern
--select CODES	Komma-getrennte ruff-Regelcodes, z. B. E,F,W (Standard: alle)
--no-banner	ASCII-Banner unterdrücken
JSON-Export

Mit --json-out report.json wird nach Stufe 1 der Linter-Report geschrieben. Läuft anschließend Stufe 2, wird der KI-Report unter dem Schlüssel ai_review in dieselbe Datei eingefügt. Eine vorhandene Datei wird dabei erweitert, die Linter-Daten bleiben erhalten.

json
{
  "...": "Linter-Report aus Stufe 1",
  "ai_review": {
    "...": "KI-Report aus Stufe 2"
  }
}
Projektstruktur
.
├── code_review.py              # Einstiegspunkt / CLI
├── stages/
│   ├── stage1_linter.py        # Stufe 1: ruff-Anbindung
│   ├── stage2_ai_review.py     # Stufe 2: Claude-Analyse
│   └── stage3_apply_fixes.py   # Stufe 3: Fixes anwenden
└── ui/
    └── display.py              # Konsolenausgabe (Banner, Reports, interaktive Abfragen)
Exit-Codes
Code	Bedeutung
0	Erfolgreich. Bei --only-lint: keine Linter-Fehler gefunden
1	Zielpfad existiert nicht, oder bei --only-lint wurden Linter-Fehler gefunden
Grenzen und Hinweise
Stufe 3 nur für Einzeldateien. Bei Verzeichnissen wird das automatische Anwenden übersprungen.
Nur Issues mit Zeilenbezug können in Stufe 3 angewendet werden. Hinweise ohne konkrete Zeile bleiben im Report stehen.
Änderungen betreffen die Originaldatei. Arbeite deshalb mit Versionskontrolle (git commit vor dem Lauf), damit sich jede Änderung nachvollziehen und zurückrollen lässt.
KI-Vorschläge prüfen. Claude kann sich irren. Jeder Vorschlag sollte vor dem Anwenden gelesen und bei Bedarf abgelehnt werden.
Datenschutz. In Stufe 2 und 3 wird der Quellcode an die Anthropic-API gesendet. Setze das Tool nicht auf Code ein, der vertraulich bleiben muss oder Zugangsdaten enthält.
Sicherheit
API-Keys gehören in Umgebungsvariablen oder in eine .env, niemals in den Quellcode.
Trage .env in die .gitignore ein, bevor du sie das erste Mal committest:
  .env
Checke nur eine .env.example mit Platzhaltern ein.
Wurde ein Key versehentlich committet, entferne ihn aus der Git-Historie und rotiere ihn in der Anthropic Console.
