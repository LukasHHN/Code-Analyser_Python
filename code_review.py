#!/usr/bin/env python3
"""
code_review.py – KI-gestütztes Code Review Tool
Einstiegspunkt / CLI

Verwendung:
  python code_review.py datei.py
  python code_review.py ./mein_projekt/
  python code_review.py datei.py --only-lint
  python code_review.py datei.py --json-out report.json
"""

import argparse
import json
import sys
from pathlib import Path

from ui.display import (
    console,
    print_banner,
    print_stage_header,
    print_linter_report,
    print_ai_report,
    print_fix_session_summary,
    interactive_fix_callback,
    print_error,
    print_info,
)
from stages.stage1_linter import run_linter
from stages.stage2_ai_review import run_ai_review
from stages.stage3_apply_fixes import run_fix_session


# ── CLI-Definition ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code_review",
        description="KI-gestütztes Code Review in 3 Stufen.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python code_review.py mein_skript.py
  python code_review.py ./src/ --only-lint
  python code_review.py app.py --json-out report.json
  python code_review.py app.py --select E,F,W
        """,
    )
    parser.add_argument(
        "target",
        help="Pfad zur Python-Datei oder zum Verzeichnis",
    )
    parser.add_argument(
        "--only-lint",
        action="store_true",
        help="Nur Stufe 1 (Linter) ausführen",
    )
    parser.add_argument(
        "--json-out",
        metavar="FILE",
        help="Linter-Report als JSON speichern (z.B. report.json)",
    )
    parser.add_argument(
        "--select",
        metavar="CODES",
        help="Komma-getrennte ruff-Regelcodes (Standard: alle). Bsp: E,F,W",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="ASCII-Banner unterdrücken",
    )
    return parser


# ── Stufe 1 ───────────────────────────────────────────────────────────────────

def run_stage1(target: str, select_codes: list[str] | None, json_out: str | None) -> bool:
    """
    Führt Stufe 1 aus.
    Gibt True zurück wenn der Code für Stufe 2 geeignet ist (keine kritischen Fehler),
    sonst False.
    """
    print_stage_header(
        1,
        "Syntaktische Analyse",
        "Statische Code-Prüfung via ruff – schnell, ohne KI-Anfragen.",
    )

    try:
        with console.status("[cyan]Analysiere Code…[/cyan]", spinner="dots"):
            report = run_linter(target, select=select_codes)
    except FileNotFoundError as e:
        print_error(str(e))
        return False
    except RuntimeError as e:
        print_error(str(e))
        return False

    print_linter_report(report)

    # Optionaler JSON-Export
    if json_out:
        out_path = Path(json_out)
        out_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        print_info(f"JSON-Report gespeichert: {out_path.resolve()}")

    # Für Stufe 2 nur freigeben wenn keine hard errors
    return report.error_count == 0


# ── Platzhalter für spätere Stufen ────────────────────────────────────────────

def run_stage2(target: str, linter_report, json_out: str | None):
    print_stage_header(
        2,
        "KI-Analyse (Logik & Verständnis)",
        "Claude analysiert Logik, Lesbarkeit und potenzielle Bugs.",
    )

    try:
        with console.status("[cyan]KI analysiert Code…[/cyan]", spinner="dots"):
            ai_report = run_ai_review(target, linter_report)
    except RuntimeError as e:
        print_error(str(e))
        return None

    print_ai_report(ai_report)

    # Optionaler JSON-Export – an bestehenden Report anhängen
    if json_out:
        import json
        from pathlib import Path
        out_path = Path(json_out)
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        existing["ai_review"] = ai_report.to_dict()
        out_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        print_info(f"KI-Report zu JSON hinzugefügt: {out_path.resolve()}")

    return ai_report


def run_stage3(target: str, ai_report):
    print_stage_header(
        3,
        "Lösungsvorschlag & Implementierung",
        "Jede Verbesserung einzeln prüfen und direkt auf die Datei anwenden.",
    )

    # Nur bei Einzeldateien anwendbar
    from pathlib import Path
    if Path(target).is_dir():
        console.print(
            "  [warning]⚠  Automatisches Anwenden ist nur bei Einzeldateien verfügbar.[/warning]\n"
        )
        return

    actionable = [i for i in ai_report.issues if i.line > 0]
    if not actionable:
        console.print(
            "  [dim]→  Keine Issues mit Zeilenbezug – nichts anzuwenden.[/dim]\n"
        )
        return

    try:
        session = run_fix_session(
            target    = target,
            ai_report = ai_report,
            callback  = interactive_fix_callback,
        )
    except RuntimeError as e:
        print_error(str(e))
        return

    print_fix_session_summary(session)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()

    # Ziel validieren
    target_path = Path(args.target)
    if not target_path.exists():
        print_error(f"Pfad existiert nicht: {args.target}")
        sys.exit(1)

    if not args.no_banner:
        print_banner()

    # Regelcodes aufsplitten falls angegeben
    select_codes = [c.strip() for c in args.select.split(",")] if args.select else None

    # ── Stufe 1
    stage1_ok = run_stage1(str(target_path), select_codes, args.json_out)

    if args.only_lint:
        sys.exit(0 if stage1_ok else 1)

    # ── Stufe 2
    # Läuft immer – auch wenn Stufe 1 Fehler gefunden hat.
    # Die Linter-Ergebnisse werden als Kontext mitgeschickt, damit
    # Claude sie kennt und NICHT dupliziert, sondern nur Logikprobleme angeht.
    from stages.stage1_linter import run_linter as _rerun
    linter_report = _rerun(str(target_path), select=select_codes)
    ai_report = run_stage2(str(target_path), linter_report, args.json_out)

    # ── Stufe 3
    if ai_report is not None:
        run_stage3(str(target_path), ai_report)


if __name__ == "__main__":
    main()
