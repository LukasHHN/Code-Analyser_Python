"""
Stage 2 – KI-gestützte Code-Analyse via Anthropic Claude API
Nimmt den Quellcode + LinterReport aus Stufe 1 entgegen und gibt
einen strukturierten AIReviewReport zurück.
"""

import os
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field

import anthropic

from stages.stage1_linter import LinterReport


# ── Konfiguration ─────────────────────────────────────────────────────────────

CLAUDE_MODEL      = "claude-sonnet-4-6"
MAX_OUTPUT_TOKENS = 4096


# ── Datenmodell ───────────────────────────────────────────────────────────────

@dataclass
class AIIssue:
    """Ein einzelnes Problem das die KI im Code gefunden hat."""
    line:        int
    severity:    str          # "high" | "medium" | "low"
    category:    str          # "logic" | "readability" | "security" | "performance" | "style"
    title:       str
    explanation: str
    suggestion:  str

    def to_dict(self) -> dict:
        return {
            "line":        self.line,
            "severity":    self.severity,
            "category":    self.category,
            "title":       self.title,
            "explanation": self.explanation,
            "suggestion":  self.suggestion,
        }


@dataclass
class AIReviewReport:
    """Gesamtergebnis der KI-Analyse aus Stufe 2."""
    target:          str
    model_used:      str
    issues:          list[AIIssue] = field(default_factory=list)
    summary:         str = ""
    overall_quality: str = "unknown"
    raw_response:    str = ""

    @property
    def high_count(self)   -> int: return sum(1 for i in self.issues if i.severity == "high")
    @property
    def medium_count(self) -> int: return sum(1 for i in self.issues if i.severity == "medium")
    @property
    def low_count(self)    -> int: return sum(1 for i in self.issues if i.severity == "low")

    def to_dict(self) -> dict:
        return {
            "target":          self.target,
            "model_used":      self.model_used,
            "overall_quality": self.overall_quality,
            "summary":         self.summary,
            "high_count":      self.high_count,
            "medium_count":    self.medium_count,
            "low_count":       self.low_count,
            "issues":          [i.to_dict() for i in self.issues],
        }


# ── Prompt-Erstellung ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Du bist ein erfahrener Python-Entwickler der Code Reviews durchführt.
Deine Aufgabe ist es, Python-Code auf folgende Aspekte zu analysieren:
- Logikfehler und potenzielle Bugs
- Lesbarkeit und Wartbarkeit
- Sicherheitsprobleme
- Performance-Probleme
- Verletzung von Python-Best-Practices (über reine Syntax hinaus)

Du erhältst:
1. Den originalen Python-Quellcode
2. Die Ergebnisse eines Linters (ruff) aus einer Vorstufe

Fokussiere dich auf Probleme die der Linter NICHT gefunden hat.
Dupliziere keine Linter-Befunde, sondern gehe tiefer.

Antworte AUSSCHLIESSLICH mit einem validen JSON-Objekt.
Kein erklärender Text, keine Markdown-Backticks, nur reines JSON.

Das JSON muss exakt diesem Schema folgen:
{
  "issues": [
    {
      "line": <Zeilennummer als Integer, 0 wenn allgemein>,
      "severity": "<high|medium|low>",
      "category": "<logic|readability|security|performance|style>",
      "title": "<kurze Überschrift max 60 Zeichen>",
      "explanation": "<ausführliche Erklärung des Problems>",
      "suggestion": "<konkreter Lösungsvorschlag, gerne mit Code-Beispiel>"
    }
  ],
  "summary": "<Gesamteinschätzung in 2-3 Sätzen>",
  "overall_quality": "<good|medium|poor>"
}

Wenn keine Probleme gefunden werden, gib ein leeres issues-Array zurück."""


def _build_user_prompt(source_code: str, linter_report: LinterReport) -> str:
    """Baut den User-Prompt aus Quellcode + Linter-Ergebnissen zusammen."""
    linter_summary = f"Fehler: {linter_report.error_count}, Warnungen: {linter_report.warning_count}"
    linter_issues_text = "\n".join(
        f"  Zeile {i.line}: [{i.code}] {i.message}"
        for i in linter_report.issues[:20]
    ) or "  (keine Probleme gefunden)"

    return f"""=== QUELLCODE ===
{source_code}

=== LINTER-ERGEBNISSE (ruff) – diese bereits bekannt, nicht duplizieren ===
{linter_summary}
{linter_issues_text}

=== AUFGABE ===
Analysiere den Code und gib dein Review als JSON zurück."""


# ── Parsing der Claude-Antwort ────────────────────────────────────────────────

def _parse_ai_response(raw: str, target: str, model: str) -> AIReviewReport:
    """Parst die JSON-Antwort von Claude in ein AIReviewReport-Objekt."""
    report = AIReviewReport(target=target, model_used=model, raw_response=raw)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        report.summary = f"Fehler beim Parsen der KI-Antwort: {e}"
        report.overall_quality = "unknown"
        return report

    for entry in data.get("issues", []):
        try:
            report.issues.append(AIIssue(
                line        = int(entry.get("line", 0)),
                severity    = entry.get("severity", "low"),
                category    = entry.get("category", "style"),
                title       = entry.get("title", ""),
                explanation = entry.get("explanation", ""),
                suggestion  = entry.get("suggestion", ""),
            ))
        except (ValueError, TypeError):
            continue

    report.summary         = data.get("summary", "")
    report.overall_quality = data.get("overall_quality", "unknown")
    return report


# ── Datei einlesen ────────────────────────────────────────────────────────────

def _read_source(target: str) -> str:
    """Liest den Quellcode ein (Datei oder Verzeichnis, max. 500 Zeilen)."""
    path = Path(target)
    MAX_LINES = 500

    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[:MAX_LINES])

    parts = []
    total = 0
    for py_file in sorted(path.rglob("*.py")):
        if total >= MAX_LINES:
            break
        lines = py_file.read_text(encoding="utf-8").splitlines()
        remaining = MAX_LINES - total
        parts.append(f"# ── {py_file.name} ──")
        parts.extend(lines[:remaining])
        total += min(len(lines), remaining)

    return "\n".join(parts)


# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def run_ai_review(target: str, linter_report: LinterReport) -> AIReviewReport:
    """
    Führt die KI-Analyse via Claude API durch.

    Args:
        target:        Pfad zur Datei oder zum Verzeichnis
        linter_report: LinterReport aus Stufe 1

    Returns:
        AIReviewReport mit den KI-Befunden
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY nicht gefunden.\n"
            "Bitte setzen mit: export ANTHROPIC_API_KEY='sk-ant-...'\n"
            "Oder dauerhaft in ~/.bashrc eintragen."
        )

    client = anthropic.Anthropic(api_key=api_key)

    source_code = _read_source(target)
    user_prompt = _build_user_prompt(source_code, linter_report)

    try:
        response = client.messages.create(
            model      = CLAUDE_MODEL,
            max_tokens = MAX_OUTPUT_TOKENS,
            system     = SYSTEM_PROMPT,
            messages   = [
                {"role": "user", "content": user_prompt}
            ],
        )
    except anthropic.AuthenticationError:
        raise RuntimeError(
            "Ungültiger API-Key. Bitte prüfe deinen ANTHROPIC_API_KEY in ~/.bashrc."
        )
    except anthropic.RateLimitError:
        raise RuntimeError(
            "Rate Limit erreicht. Bitte kurz warten und erneut versuchen."
        )
    except Exception as e:
        raise RuntimeError(f"Claude API Fehler: {e}")

    # Claude gibt eine Liste von Content-Blöcken zurück – wir brauchen den Text
    raw_text = response.content[0].text
    return _parse_ai_response(raw_text, target, CLAUDE_MODEL)
