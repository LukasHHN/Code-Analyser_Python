"""
TUI-Ausgabe mit rich.
Alle visuellen Komponenten des Code-Review-Tools sind hier gebündelt.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.columns import Columns
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.syntax import Syntax
from rich.theme import Theme

from stages.stage1_linter import LinterReport, LinterIssue
from stages.stage2_ai_review import AIReviewReport, AIIssue

# ── Theme ─────────────────────────────────────────────────────────────────────

THEME = Theme({
    "stage":     "bold cyan",
    "success":   "bold green",
    "error":     "bold red",
    "warning":   "bold yellow",
    "info":      "dim white",
    "code":      "bold magenta",
    "header":    "bold white on dark_blue",
    "fixable":   "bold green",
})

console = Console(theme=THEME)


# ── Banner ────────────────────────────────────────────────────────────────────

def print_banner():
    banner = Text()
    banner.append("  ██████╗ ██████╗ ██████╗ ███████╗    ", style="bold cyan")
    banner.append("██████╗ ███████╗██╗   ██╗\n", style="bold blue")
    banner.append("  ██╔════╝██╔═══██╗██╔══██╗██╔════╝    ", style="bold cyan")
    banner.append("██╔══██╗██╔════╝██║   ██║\n", style="bold blue")
    banner.append("  ██║     ██║   ██║██║  ██║█████╗      ", style="bold cyan")
    banner.append("██████╔╝█████╗  ██║   ██║\n", style="bold blue")
    banner.append("  ██║     ██║   ██║██║  ██║██╔══╝      ", style="bold cyan")
    banner.append("██╔══██╗██╔══╝  ╚██╗ ██╔╝\n", style="bold blue")
    banner.append("  ╚██████╗╚██████╔╝██████╔╝███████╗    ", style="bold cyan")
    banner.append("██║  ██║███████╗ ╚████╔╝ \n", style="bold blue")
    banner.append("   ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝    ", style="bold cyan")
    banner.append("╚═╝  ╚═╝╚══════╝  ╚═══╝  \n", style="bold blue")

    sub = Text("  KI-gestütztes Code Review Tool  •  Python Edition", style="italic dim white")
    console.print()
    console.print(banner)
    console.print(sub)
    console.print()


# ── Phasen-Header ─────────────────────────────────────────────────────────────

def print_stage_header(number: int, title: str, description: str):
    console.print()
    console.print(Rule(
        f"[stage] STUFE {number}[/stage]  [bold white]{title}[/bold white]",
        style="cyan"
    ))
    console.print(f"  [info]{description}[/info]")
    console.print()


# ── Linter-Report (Stufe 1) ───────────────────────────────────────────────────

def _severity_style(severity: str) -> str:
    return {"error": "error", "warning": "warning", "convention": "cyan"}.get(severity, "white")


def _severity_icon(severity: str) -> str:
    return {"error": "✖", "warning": "⚠", "convention": "ℹ"}.get(severity, "·")


def print_linter_summary(report: LinterReport):
    """Zeigt die Zusammenfassung-Kacheln nach dem Linter-Lauf."""

    # Stat-Kacheln
    stats = [
        Panel(
            f"[bold white]{report.files_scanned}[/bold white]\n[info]Dateien[/info]",
            border_style="blue", expand=True
        ),
        Panel(
            f"[error]{report.error_count}[/error]\n[info]Fehler[/info]",
            border_style="red", expand=True
        ),
        Panel(
            f"[warning]{report.warning_count}[/warning]\n[info]Warnungen[/info]",
            border_style="yellow", expand=True
        ),
        Panel(
            f"[fixable]{report.fixable_count}[/fixable]\n[info]Auto-fixbar[/info]",
            border_style="green", expand=True
        ),
    ]
    console.print(Columns(stats, equal=True))
    console.print()


def print_linter_issues(report: LinterReport, max_display: int = 50):
    """Gibt die Einzel-Issues als Tabelle aus."""

    if not report.issues:
        console.print(Panel(
            "[success]✔  Keine Linter-Probleme gefunden![/success]",
            border_style="green"
        ))
        return

    # Nach Datei gruppieren
    files: dict[str, list[LinterIssue]] = {}
    for issue in report.issues:
        files.setdefault(issue.file, []).append(issue)

    displayed = 0
    for filepath, issues in files.items():
        # Relativen Pfad anzeigen
        short = filepath.replace(report.target, "").lstrip("/\\") or filepath

        table = Table(
            title=f"[code]{short}[/code]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold white",
            border_style="dim",
            expand=True,
        )
        table.add_column("Zeile",  style="dim", width=7)
        table.add_column("Code",   style="bold magenta", width=8)
        table.add_column("Typ",    width=12)
        table.add_column("Meldung")
        table.add_column("Ruff Fixable",    width=5)

        for issue in sorted(issues, key=lambda x: x.line):
            if displayed >= max_display:
                break
            sev_style = _severity_style(issue.severity)
            icon      = _severity_icon(issue.severity)
            table.add_row(
                f"{issue.line}:{issue.col}",
                issue.code,
                f"[{sev_style}]{icon} {issue.severity}[/{sev_style}]",
                issue.message,
                "[green]✔[/green]" if issue.fix_available else "[error]X[/error]",
            )
            displayed += 1

        console.print(table)

    if displayed >= max_display and len(report.issues) > max_display:
        remaining = len(report.issues) - max_display
        console.print(f"  [warning]… und {remaining} weitere Probleme (im JSON-Report)[/warning]")

    console.print()


def print_linter_report(report: LinterReport):
    """Vollständige Ausgabe von Stufe 1."""
    print_linter_summary(report)
    print_linter_issues(report)

    # Abschluss-Bewertung
    total = len(report.issues)
    if total == 0:
        console.print(Panel("[success]✔  Code ist syntaktisch sauber.[/success]", border_style="green"))
    elif report.error_count > 0:
        console.print(Panel(
            f"[error]✖  {report.error_count} kritische Fehler gefunden. "
            f"Bitte vor Stufe 2 beheben.[/error]",
            border_style="red"
        ))
    else:
        console.print(Panel(
            f"[warning]⚠  {total} Warnungen / Stil-Probleme gefunden. "
            f"Stufe 2 wird trotzdem gestartet.[/warning]",
            border_style="yellow"
        ))
    console.print()

# ── KI-Review-Report (Stufe 2) ───────────────────────────────────────────────

def _ai_severity_style(severity: str) -> str:
    return {"high": "error", "medium": "warning", "low": "cyan"}.get(severity, "white")


def _ai_severity_icon(severity: str) -> str:
    return {"high": "✖", "medium": "⚠", "low": "ℹ"}.get(severity, "·")


def _quality_style(quality: str) -> str:
    return {"good": "success", "medium": "warning", "poor": "error"}.get(quality, "info")


def _quality_label(quality: str) -> str:
    return {"good": "Gut", "medium": "Verbesserungswürdig", "poor": "Kritisch"}.get(quality, "Unbekannt")


def print_ai_summary(report: AIReviewReport):
    """Zeigt die KI-Zusammenfassung und Stat-Kacheln."""
    q_style = _quality_style(report.overall_quality)
    q_label = _quality_label(report.overall_quality)
    console.print(Panel(
        f"[{q_style}]Gesamtqualität: {q_label}[/{q_style}]\n\n"
        f"[white]{report.summary}[/white]",
        title=f"[bold cyan]KI-Analyse  •  {report.model_used}[/bold cyan]",
        border_style=q_style,
    ))
    console.print()

    stats = [
        Panel(
            f"[error]{report.high_count}[/error]\n[info]Kritisch[/info]",
            border_style="red", expand=True
        ),
        Panel(
            f"[warning]{report.medium_count}[/warning]\n[info]Mittel[/info]",
            border_style="yellow", expand=True
        ),
        Panel(
            f"[cyan]{report.low_count}[/cyan]\n[info]Gering[/info]",
            border_style="cyan", expand=True
        ),
    ]
    console.print(Columns(stats, equal=True))
    console.print()


def print_ai_issues(report: AIReviewReport):
    """Gibt die KI-Befunde als Tabelle aus."""
    if not report.issues:
        console.print(Panel(
            "[success]✔  KI hat keine weiteren Probleme gefunden.[/success]",
            border_style="green"
        ))
        return

    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold white",
        border_style="dim",
        expand=True,
        show_lines=True,
    )
    table.add_column("Zeile",     style="dim",          width=6)
    table.add_column("Schwere",                          width=10)
    table.add_column("Kategorie", style="bold magenta", width=14)
    table.add_column("Problem")
    table.add_column("Lösung")

    for issue in sorted(report.issues, key=lambda x: (
        {"high": 0, "medium": 1, "low": 2}.get(x.severity, 3), x.line
    )):
        sev_style = _ai_severity_style(issue.severity)
        icon      = _ai_severity_icon(issue.severity)
        line_str  = str(issue.line) if issue.line > 0 else "–"
        table.add_row(
            line_str,
            f"[{sev_style}]{icon} {issue.severity}[/{sev_style}]",
            issue.category,
            f"[bold white]{issue.title}[/bold white]\n[dim]{issue.explanation}[/dim]",
            f"[dim]{issue.suggestion}[/dim]",
        )

    console.print(table)
    console.print()


def print_ai_report(report: AIReviewReport):
    """Vollständige Ausgabe von Stufe 2."""
    print_ai_summary(report)
    print_ai_issues(report)



# ── Spinner (für spätere Stufen) ──────────────────────────────────────────────

def create_spinner(label: str):
    """Gibt einen konfigurierten Progress-Spinner zurück (als Kontextmanager)."""
    return Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold white]{task.description}"),
        BarColumn(bar_width=30, style="cyan"),
        console=console,
        transient=True,
    )


# ── Fehlermeldungen ───────────────────────────────────────────────────────────

def print_error(message: str):
    console.print(Panel(f"[error]✖  {message}[/error]", border_style="red"))


def print_info(message: str):
    console.print(f"  [info]{message}[/info]")


# ── Stufe 3: Interaktive Fix-Ansicht ─────────────────────────────────────────

def _print_diff(diff_lines: list[str]) -> None:
    """Gibt einen unified diff farbig aus."""
    if not diff_lines:
        console.print("  [dim](Keine Änderungen erkannt)[/dim]")
        return

    for line in diff_lines:
        if line.startswith("+++") or line.startswith("---"):
            console.print(f"[dim]{line}[/dim]")
        elif line.startswith("@@"):
            console.print(f"[cyan]{line}[/cyan]")
        elif line.startswith("+"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("-"):
            console.print(f"[red]{line}[/red]")
        else:
            console.print(f"[dim]{line}[/dim]")


def interactive_fix_callback(
    issue,
    diff_lines:  list[str],
    apply_fn:    callable,
    skip_fn:     callable,
    quit_fn:     callable,
) -> None:
    """
    UI-Callback für stage3_apply_fixes.run_fix_session().
    Zeigt das Issue + Diff an und fragt den Nutzer nach seiner Entscheidung.
    """
    from stages.stage2_ai_review import AIIssue

    sev_style = {"high": "error", "medium": "warning", "low": "cyan"}.get(issue.severity, "white")
    sev_icon  = {"high": "✖", "medium": "⚠", "low": "ℹ"}.get(issue.severity, "·")

    console.print()
    console.print(Rule(
        f"[{sev_style}]{sev_icon}  {issue.title}[/{sev_style}]",
        style=sev_style,
    ))

    # Detailansicht des Issues
    console.print(Panel(
        f"[bold white]Zeile:[/bold white]      {issue.line if issue.line > 0 else '–'}\n"
        f"[bold white]Kategorie:[/bold white]  {issue.category}\n"
        f"[bold white]Schwere:[/bold white]    [{sev_style}]{issue.severity}[/{sev_style}]\n\n"
        f"[bold white]Erklärung:[/bold white]\n{issue.explanation}\n\n"
        f"[bold white]Vorschlag:[/bold white]\n[green]{issue.suggestion}[/green]",
        border_style=sev_style,
        title="[bold]Problem-Detail[/bold]",
    ))

    # Diff-Vorschau
    console.print()
    console.print(Rule("[bold white]Vorschau der Änderungen[/bold white]", style="dim"))
    _print_diff(diff_lines)
    console.print()

    # Nutzer-Eingabe
    while True:
        console.print(
            "  [bold white]Was möchtest du tun?[/bold white]  "
            "[green]\\[a][/green] Anwenden  "
            "[yellow]\\[s][/yellow] Überspringen  "
            "[red]\\[q][/red] Beenden"
        )
        try:
            choice = input("  Eingabe: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            choice = "q"

        if choice == "a":
            with console.status("[cyan]Änderung wird angewendet…[/cyan]", spinner="dots"):
                apply_fn()
            console.print("  [success]✔  Änderung angewendet.[/success]")
            break
        elif choice == "s":
            skip_fn()
            console.print("  [dim]→  Übersprungen.[/dim]")
            break
        elif choice == "q":
            quit_fn()
            console.print("  [warning]⚠  Sitzung beendet.[/warning]")
            break
        else:
            console.print("  [dim]Ungültige Eingabe. Bitte a, s oder q eingeben.[/dim]")


def print_fix_session_summary(session) -> None:
    """Abschluss-Zusammenfassung der Stufe-3-Sitzung."""
    from stages.stage3_apply_fixes import FixSession

    console.print()
    console.print(Rule("[bold white]Stufe 3 – Abschluss[/bold white]", style="cyan"))
    console.print()

    stats = [
        Panel(
            f"[success]{session.applied_count}[/success]\n[info]Angewendet[/info]",
            border_style="green", expand=True
        ),
        Panel(
            f"[dim]{session.skipped_count}[/dim]\n[info]Übersprungen[/info]",
            border_style="dim", expand=True
        ),
        Panel(
            f"[error]{session.error_count}[/error]\n[info]Fehler[/info]",
            border_style="red", expand=True
        ),
    ]
    console.print(Columns(stats, equal=True))
    console.print()

    if session.applied_count > 0:
        console.print(Panel(
            f"[success]✔  {session.applied_count} Verbesserung(en) wurden auf die Datei angewendet.[/success]\n"
            f"[info]Backup gespeichert unter: {session.backup_path}[/info]",
            border_style="green",
        ))
    else:
        console.print(Panel(
            "[dim]Keine Änderungen vorgenommen. Die Originaldatei ist unverändert.[/dim]",
            border_style="dim",
        ))
    console.print()
