from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pylogshield import __version__
from pylogshield.utils import LogLevel
from pylogshield.viewer import LogViewer, _LEVEL_STYLES

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

_console = Console()

_LEVEL_DESCRIPTIONS: dict = {
    "CRITICAL": "System failure — immediate attention required",
    "ERROR":    "An operation failed",
    "WARNING":  "Unexpected condition, application still running",
    "INFO":     "General operational messages",
    "DEBUG":    "Detailed diagnostic information",
    "NOTSET":   "No level assigned",
}


# ---------------------------------------------------------------------------
# Version callback
# ---------------------------------------------------------------------------

def _version_callback(value: bool) -> None:
    if value:
        _console.print(
            f"[bold cyan]PyLogShield[/bold cyan] [dim]v[/dim][bold]{__version__}[/bold]"
        )
        raise typer.Exit()


@app.callback()
def _main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        is_eager=True,
        callback=_version_callback,
        help="Show version and exit.",
    ),
) -> None:
    """[bold cyan]PyLogShield[/bold cyan] — structured log viewer and follower.

    Use [cyan]pylogshield <command> --help[/cyan] for detailed usage.
    """


# ---------------------------------------------------------------------------
# view
# ---------------------------------------------------------------------------

@app.command("view")
def view_logs(
    file: Path = typer.Option(
        ..., "--file", "-f", exists=True, readable=True,
        help="Path to the log file.",
    ),
    limit: int = typer.Option(
        200, "--limit", "-n", min=1,
        help="Max lines to display from the end of the file.",
    ),
    level: Optional[str] = typer.Option(
        None, "--level", "-l",
        help="Minimum log level (e.g. [green]INFO[/green], [yellow]WARNING[/yellow], [red]ERROR[/red]).",
    ),
    keyword: Optional[str] = typer.Option(
        None, "--keyword", "-k",
        help="Only show lines containing this text (case-insensitive).",
    ),
) -> None:
    """[bold]Pretty-print[/bold] the last N log entries from a file.

    Automatically detects JSON or plain-text log format.

    [bold]Examples:[/bold]

      [dim]# Show last 50 lines[/dim]
      pylogshield view -f app.log -n 50

      [dim]# Show ERROR logs containing "timeout"[/dim]
      pylogshield view -f app.log -l ERROR -k timeout
    """
    level_display = level.upper() if level else "[dim]all[/dim]"
    keyword_display = f'[italic]"{keyword}"[/italic]' if keyword else "[dim]none[/dim]"

    _console.print(
        Panel(
            f"[dim]File:[/dim]    [bold]{file}[/bold]\n"
            f"[dim]Limit:[/dim]   {limit} lines\n"
            f"[dim]Level:[/dim]   {level_display}\n"
            f"[dim]Keyword:[/dim] {keyword_display}",
            title="[bold cyan] Log Viewer [/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            expand=False,
        )
    )

    viewer = LogViewer(file)
    min_level = LogLevel.from_name(level) if level else None
    ok = viewer.display_logs(limit=limit, level=min_level, keyword=keyword)
    raise typer.Exit(code=0 if ok else 1)


# ---------------------------------------------------------------------------
# follow
# ---------------------------------------------------------------------------

@app.command("follow")
def follow_logs(
    file: Path = typer.Option(
        ..., "--file", "-f", exists=True, readable=True,
        help="Path to the log file.",
    ),
    level: Optional[str] = typer.Option(
        None, "--level", "-l",
        help="Minimum log level (e.g. [green]INFO[/green], [red]ERROR[/red]).",
    ),
    keyword: Optional[str] = typer.Option(
        None, "--keyword", "-k",
        help="Only show lines containing this text (case-insensitive).",
    ),
    interval: float = typer.Option(
        0.5, "--interval", "-i", min=0.05,
        help="Refresh interval in seconds.",
    ),
    max_lines: int = typer.Option(
        500, "--max-lines", "-m", min=10,
        help="Rolling buffer size — number of lines to keep in view.",
    ),
) -> None:
    """[bold]Live-follow[/bold] a log file ([italic]tail -f[/italic] style).

    Displays new log entries as they are written. Handles log rotation
    automatically. Press [bold]Ctrl+C[/bold] to stop.

    [bold]Examples:[/bold]

      [dim]# Follow all new log entries[/dim]
      pylogshield follow -f app.log

      [dim]# Follow only ERROR level and above[/dim]
      pylogshield follow -f app.log -l ERROR

      [dim]# Follow with keyword filter, faster refresh[/dim]
      pylogshield follow -f app.log -k payment -i 0.25
    """
    level_display = level.upper() if level else "[dim]all[/dim]"
    keyword_display = f'[italic]"{keyword}"[/italic]' if keyword else "[dim]none[/dim]"

    _console.print(
        Panel(
            f"[dim]File:[/dim]    [bold]{file}[/bold]\n"
            f"[dim]Level:[/dim]   {level_display}\n"
            f"[dim]Keyword:[/dim] {keyword_display}\n"
            f"[dim]Refresh:[/dim] {interval}s  [dim]Buffer:[/dim] {max_lines} lines\n\n"
            f"[dim]Waiting for new entries — press [bold]Ctrl+C[/bold] to stop.[/dim]",
            title="[bold cyan] Live Follow [/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            expand=False,
        )
    )

    viewer = LogViewer(file)
    min_level = LogLevel.from_name(level) if level else None
    ok = viewer.follow_logs(
        level=min_level, keyword=keyword, interval=interval, max_lines=max_lines
    )
    _console.print("\n[dim]Stopped following.[/dim]")
    raise typer.Exit(code=0 if ok else 1)


# ---------------------------------------------------------------------------
# levels
# ---------------------------------------------------------------------------

@app.command("levels")
def show_levels() -> None:
    """List all supported log levels and their [bold]numeric values[/bold]."""
    table = Table(
        title="[bold cyan]PyLogShield[/bold cyan] — Log Levels",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold white",
        expand=False,
    )
    table.add_column("Level", min_width=10)
    table.add_column("Value", justify="right", style="dim", min_width=6)
    table.add_column("Description", style="dim")

    for name in LogLevel.valid_levels():
        value = LogLevel.from_name(name)
        style = _LEVEL_STYLES.get(name, "")
        table.add_row(
            Text(name, style=style),
            str(value),
            _LEVEL_DESCRIPTIONS.get(name, ""),
        )

    _console.print()
    _console.print(table)
    _console.print()
