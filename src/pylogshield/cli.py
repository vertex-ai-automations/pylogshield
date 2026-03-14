from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from pylogshield.utils import LogLevel
from pylogshield.viewer import LogViewer

app = typer.Typer(add_completion=False)
_console = Console()


@app.command("view")
def view_logs(
    file: Path = typer.Option(
        ..., "--file", "-f", exists=True, readable=True, help="Path to the log file."
    ),
    limit: int = typer.Option(
        200, "--limit", "-n", min=1, help="Max lines to display from the end."
    ),
    level: Optional[str] = typer.Option(
        None, "--level", "-l", help="Filter by minimum level (e.g., INFO or 20)."
    ),
    keyword: Optional[str] = typer.Option(
        None, "--keyword", "-k", help="Show only lines containing this text."
    ),
) -> None:
    """Pretty-print logs from a file, attempting JSON first and falling back to plain text."""
    viewer = LogViewer(file)
    min_level = LogLevel.from_name(level) if level else None
    ok = viewer.display_logs(limit=limit, level=min_level, keyword=keyword)
    raise typer.Exit(code=0 if ok else 1)


@app.command("follow")
def follow_logs(
    file: Path = typer.Option(
        ..., "--file", "-f", exists=True, readable=True, help="Path to the log file."
    ),
    level: Optional[str] = typer.Option(
        None, "--level", "-l", help="Minimum level (e.g., INFO or 20)."
    ),
    keyword: Optional[str] = typer.Option(
        None, "--keyword", "-k", help="Show only lines containing this text."
    ),
    interval: float = typer.Option(
        0.5, "--interval", "-i", min=0.05, help="Refresh interval in seconds."
    ),
    max_lines: int = typer.Option(
        500, "--max-lines", "-m", min=10, help="Max lines to keep in the live table."
    ),
) -> None:
    """Live-follow a log file (tail -f style) with a rich table that updates in place.

    Press Ctrl+C to stop.
    """
    viewer = LogViewer(file)
    min_level = LogLevel.from_name(level) if level else None
    ok = viewer.follow_logs(
        level=min_level, keyword=keyword, interval=interval, max_lines=max_lines
    )
    raise typer.Exit(code=0 if ok else 1)


@app.command("levels")
def show_levels() -> None:
    """List supported log levels and their numeric values."""
    table = Table(title="Log Levels", style="bold green")
    table.add_column("Name", style="bold cyan")
    table.add_column("Value", justify="right")
    for name in LogLevel.valid_levels():
        table.add_row(name, str(LogLevel.from_name(name)))
    _console.print(table)
