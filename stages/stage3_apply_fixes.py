"""
Stage 3 – Lösungsvorschlag & interaktive Implementierung
Zeigt dem Nutzer Diffs für jeden KI-Befund und ermöglicht
die direkte Anwendung auf die Python-Datei aus dem CLI.
"""

import os
import json
import shutil
import difflib
from pathlib import Path
from dataclasses import dataclass, field

import anthropic

from stages.stage2_ai_review import AIIssue, AIReviewReport


# ── Konfiguration ─────────────────────────────────────────────────────────────

CLAUDE_MODEL      = "claude-sonnet-4-6"
MAX_OUTPUT_TOKENS = 2048


# ── Datenmodell ───────────────────────────────────────────────────────────────

@dataclass
class ApplyResult:
    """Ergebnis eines Anwendungsversuchs für ein einzelnes Issue."""
    issue_title:  str
    applied:      bool
    skipped:      bool   = False
    error:        str    = ""
    original:     list[str] = field(default_factory=list)   # Original-Zeilen
    patched:      list[str] = field(default_factory=list)   # Korrigierte Zeilen
    line_start:   int    = 0
    line_end:     int    = 0


@dataclass
class FixSession:
    """Zusammenfassung einer kompletten Stufe-3-Sitzung."""
    target:          str
    backup_path:     str
    results:         list[ApplyResult] = field(default_factory=list)

    @property
    def applied_count(self)  -> int: return sum(1 for r in self.results if r.applied)
    @property
    def skipped_count(self)  -> int: return sum(1 for r in self.results if r.skipped)
    @property
    def error_count(self)    -> int: return sum(1 for r in self.results if r.error)


# ── Backup ────────────────────────────────────────────────────────────────────

def create_backup(target: str) -> str:
    """
    Erstellt eine Sicherungskopie der Originaldatei.
    Gibt den Pfad zur Backup-Datei zurück.
    """
    path = Path(target)
    backup_path = path.with_suffix(f".backup{path.suffix}")

    # Bereits vorhandenes Backup hochzählen statt überschreiben
    counter = 1
    while backup_path.exists():
        backup_path = path.with_suffix(f".backup{counter}{path.suffix}")
        counter += 1

    shutil.copy2(path, backup_path)
    return str(backup_path)


# ── Kontext-Zeilen bestimmen ──────────────────────────────────────────────────

def _get_context_lines(
    all_lines: list[str],
    target_line: int,
    context: int = 10,
) -> tuple[int, int]:
    """
    Bestimmt den Zeilenbereich der für eine Korrektur relevant ist.
    Gibt (start_index, end_index) zurück (0-basiert, end exklusiv).
    """
    total = len(all_lines)

    # Zeilennummer von 1-basiert auf 0-basiert umrechnen
    center = max(0, target_line - 1)

    start = max(0, center - context)
    end   = min(total, center + context + 1)
    return start, end


# ── Claude: Korrektur generieren ──────────────────────────────────────────────

def _request_fix(
    client:       anthropic.Anthropic,
    source_lines: list[str],
    issue:        AIIssue,
    line_start:   int,
    line_end:     int,
) -> list[str] | None:
    """
    Fragt Claude nach der korrigierten Version der betroffenen Zeilen.

    Gibt die korrigierten Zeilen als Liste zurück, oder None bei Fehler.
    """
    # Betroffene Zeilen mit Zeilennummern aufbereiten (für Claude lesbar)
    numbered = "\n".join(
        f"{line_start + i + 1:4d} | {line}"
        for i, line in enumerate(source_lines[line_start:line_end])
    )

    prompt = f"""Du erhältst einen Ausschnitt einer Python-Datei und einen konkreten Verbesserungsvorschlag.
Gib NUR die korrigierten Zeilen zurück – keine Erklärungen, keine Kommentare, keine Zeilennummern.
Behalte die exakte Einrückung bei. Gib nur reinen Python-Code zurück.

=== CODEAUSSCHNITT (Zeilen {line_start + 1}–{line_end}) ===
{numbered}

=== ZU BEHEBЕНDES PROBLEM ===
Titel: {issue.title}
Erklärung: {issue.explanation}
Vorschlag: {issue.suggestion}

=== AUFGABE ===
Schreibe den obigen Codeausschnitt so um, dass das Problem behoben wird.
Gib ausschließlich den korrigierten Python-Code zurück, ohne Nummerierung oder Backticks."""

    try:
        response = client.messages.create(
            model      = CLAUDE_MODEL,
            max_tokens = MAX_OUTPUT_TOKENS,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text

        # Backticks entfernen falls Claude sie trotzdem schreibt
        lines = raw.strip().splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        # Zeilenenden normalisieren
        return [line + "\n" for line in lines]

    except Exception:
        return None


# ── Diff erstellen ────────────────────────────────────────────────────────────

def generate_diff(
    original_lines: list[str],
    patched_lines:  list[str],
    filename:       str,
    line_start:     int,
) -> list[str]:
    """
    Erzeugt einen unified diff zwischen Original und Korrektur.
    Gibt die Diff-Zeilen als Liste zurück.
    """
    return list(difflib.unified_diff(
        original_lines,
        patched_lines,
        fromfile=f"{filename} (original)",
        tofile=f"{filename} (korrigiert)",
        lineterm="",
        n=3,
    ))


# ── Datei patchen ─────────────────────────────────────────────────────────────

def apply_patch(
    target:      str,
    all_lines:   list[str],
    line_start:  int,
    line_end:    int,
    new_lines:   list[str],
) -> list[str]:
    """
    Ersetzt den Zeilenbereich [line_start:line_end] durch new_lines.
    Gibt die vollständige neue Datei als Zeilenliste zurück.
    """
    return all_lines[:line_start] + new_lines + all_lines[line_end:]


def write_file(target: str, lines: list[str]) -> None:
    """Schreibt die Zeilenliste zurück in die Datei."""
    Path(target).write_text("".join(lines), encoding="utf-8")


# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def run_fix_session(
    target:        str,
    ai_report:     AIReviewReport,
    callback:      callable,       # Callback für UI – siehe unten
) -> FixSession:
    """
    Führt die interaktive Fix-Sitzung durch.

    Der `callback` wird für jedes Issue aufgerufen und steuert die UI:
        callback(issue, diff_lines, apply_fn, skip_fn, quit_fn) -> None

    Das ermöglicht eine saubere Trennung zwischen Logik (hier) und Anzeige (display.py).

    Args:
        target:    Pfad zur Python-Datei (nur Einzeldatei unterstützt)
        ai_report: AIReviewReport aus Stufe 2
        callback:  UI-Callback Funktion

    Returns:
        FixSession mit Zusammenfassung aller Aktionen
    """
    path = Path(target)

    # Nur Einzeldateien unterstützt – bei Verzeichnis erste .py-Datei nehmen
    if path.is_dir():
        py_files = sorted(path.rglob("*.py"))
        if not py_files:
            raise RuntimeError(f"Keine Python-Dateien in {target} gefunden.")
        path = py_files[0]

    # Backup anlegen
    backup_path = create_backup(str(path))
    session = FixSession(target=str(path), backup_path=backup_path)

    # API-Client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY nicht gefunden.\n"
            "Bitte setzen mit: export ANTHROPIC_API_KEY='sk-ant-...'"
        )
    client = anthropic.Anthropic(api_key=api_key)

    # Aktuelle Dateiinhalte (werden bei Anwendung aktualisiert)
    current_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    # Nur Issues mit Zeilenbezug verarbeiten
    actionable = [i for i in ai_report.issues if i.line > 0]
    # Issues ohne Zeilenbezug (line == 0) können nicht automatisch angewendet werden
    general    = [i for i in ai_report.issues if i.line == 0]

    quit_session = False

    for issue in actionable:
        if quit_session:
            break

        result = ApplyResult(issue_title=issue.title, applied=False)

        # Kontext-Zeilen ermitteln
        line_start, line_end = _get_context_lines(current_lines, issue.line)
        original_excerpt     = current_lines[line_start:line_end]

        # Korrigierte Version von Claude anfordern
        patched_excerpt = _request_fix(client, current_lines, issue, line_start, line_end)

        if patched_excerpt is None:
            result.error = "Korrektur konnte nicht generiert werden."
            session.results.append(result)
            continue

        # Diff erzeugen
        diff_lines = generate_diff(
            original_excerpt,
            patched_excerpt,
            path.name,
            line_start,
        )

        result.original   = original_excerpt
        result.patched    = patched_excerpt
        result.line_start = line_start
        result.line_end   = line_end

        # ── Callback: UI entscheidet was der Nutzer tut ──────────────────────

        user_action = {"value": None}   # Mutable für Closure

        def apply_fix():
            nonlocal current_lines
            current_lines = apply_patch(
                str(path), current_lines, line_start, line_end, patched_excerpt
            )
            write_file(str(path), current_lines)
            result.applied = True
            user_action["value"] = "apply"

        def skip_fix():
            result.skipped = True
            user_action["value"] = "skip"

        def quit_fix():
            nonlocal quit_session
            result.skipped = True
            quit_session   = True
            user_action["value"] = "quit"

        callback(issue, diff_lines, apply_fix, skip_fix, quit_fix)
        session.results.append(result)

    # Allgemeine Issues (ohne Zeilenbezug) als übersprungen markieren
    for issue in general:
        session.results.append(ApplyResult(
            issue_title = issue.title,
            applied     = False,
            skipped     = True,
        ))

    return session
