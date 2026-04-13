"""
Stage 1 – Syntaktische Analyse via ruff
Gibt eine strukturierte Liste von LinterIssue-Objekten zurück.
"""

import subprocess
import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ── Datenmodell ──────────────────────────────────────────────────────────────

@dataclass
class LinterIssue:
    file:    str
    line:    int
    col:     int
    code:    str          # z.B. "E501", "F841"
    message: str
    severity: str         # "error" | "warning" | "convention"
    fix_available: bool = False

    def to_dict(self) -> dict:
        return {
            "file":          self.file,
            "line":          self.line,
            "col":           self.col,
            "code":          self.code,
            "message":       self.message,
            "severity":      self.severity,
            "fix_available": self.fix_available,
        }


@dataclass
class LinterReport:
    target:       str
    issues:       list[LinterIssue] = field(default_factory=list)
    files_scanned: int = 0
    ruff_version: str = "unknown"

    # Convenience-Properties
    @property
    def error_count(self)   -> int: return sum(1 for i in self.issues if i.severity == "error")
    @property
    def warning_count(self) -> int: return sum(1 for i in self.issues if i.severity == "warning")
    @property
    def fixable_count(self) -> int: return sum(1 for i in self.issues if i.fix_available)

    def to_dict(self) -> dict:
        return {
            "target":        self.target,
            "ruff_version":  self.ruff_version,
            "files_scanned": self.files_scanned,
            "error_count":   self.error_count,
            "warning_count": self.warning_count,
            "fixable_count": self.fixable_count,
            "issues":        [i.to_dict() for i in self.issues],
        }


# ── Severity-Mapping ─────────────────────────────────────────────────────────

def _classify_severity(code: str) -> str:
    """Leitet die Schwere aus dem ruff-Regelcode ab."""
    prefix = code[0].upper() if code else "W"
    return {
        "E": "error",
        "F": "error",
        "W": "warning",
        "C": "convention",
        "N": "convention",
        "B": "warning",
        "I": "convention",
        "UP": "convention",
    }.get(prefix, "warning")


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _find_ruff_cmd() -> list[str]:
    """Gibt den richtigen ruff-Aufruf zurück: direkt oder über python -m ruff."""
    import shutil
    if shutil.which("ruff"):
        return ["ruff"]
    return [sys.executable, "-m", "ruff"]


def _get_ruff_version() -> str:
    try:
        result = subprocess.run(
            _find_ruff_cmd() + ["version"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _count_python_files(path: Path) -> int:
    if path.is_file():
        return 1
    return len(list(path.rglob("*.py")))


def _parse_ruff_output(raw: str, target: str) -> list[LinterIssue]:
    """Parsed das JSON-Output von `ruff check --output-format json`."""
    issues: list[LinterIssue] = []
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError:
        return issues

    for entry in entries:
        location = entry.get("location", {})
        fix      = entry.get("fix")
        code     = entry.get("code") or "UNKNOWN"

        issues.append(LinterIssue(
            file          = entry.get("filename", target),
            line          = location.get("row", 0),
            col           = location.get("column", 0),
            code          = code,
            message       = entry.get("message", ""),
            severity      = _classify_severity(code),
            fix_available = fix is not None,
        ))
    return issues


# ── Hauptfunktion ────────────────────────────────────────────────────────────

def run_linter(target: str, select: Optional[list[str]] = None) -> LinterReport:
    """
    Führt ruff auf `target` aus und gibt einen LinterReport zurück.

    Args:
        target:  Pfad zur Datei oder zum Verzeichnis
        select:  Optionale Liste von Regelcodes (z.B. ["E", "F", "W"])
    """
    path = Path(target).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Ziel nicht gefunden: {path}")

    report = LinterReport(
        target        = str(path),
        ruff_version  = _get_ruff_version(),
        files_scanned = _count_python_files(path),
    )

    # ruff-Befehl zusammenstellen
    cmd = _find_ruff_cmd() + [
        "check",
        "--output-format", "json",
        "--no-cache",
    ]
    if select:
        cmd += ["--select", ",".join(select)]

    cmd.append(str(path))

    # Linter ausführen
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "ruff ist nicht installiert. Bitte ausführen: pip install ruff\n"
            "Falls bereits installiert: python -m ruff check --version"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("ruff hat das Timeout überschritten (60s).")

    # stdout enthält JSON-Issues, stderr eventuelle Laufzeitfehler
    if result.stderr and not result.stdout:
        raise RuntimeError(f"ruff-Fehler: {result.stderr.strip()}")

    report.issues = _parse_ruff_output(result.stdout, str(path))
    return report
