from __future__ import annotations

import os
import time
from collections import deque
from pathlib import Path
from typing import List, Optional, Tuple, Union

try:
    from rich import box
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

from pylogshield.utils import LogLevel

# tui/reader.py is stdlib-only; the import is guarded so that any accidental
# future addition of a Textual import there does not break the core package.
try:
    from pylogshield.tui.reader import LogReader as _LogReader

    _HAS_READER = True
except ImportError:  # pragma: no cover
    _HAS_READER = False  # type: ignore[misc]
    _LogReader = None  # type: ignore[assignment]

# Per-level Rich styles — used for the Level column in the log table.
_LEVEL_STYLES: dict = {
    "CRITICAL": "bold red",
    "ERROR": "red",
    "WARNING": "yellow",
    "INFO": "green",
    "DEBUG": "cyan",
    "NOTSET": "dim",
}


class LogViewer:
    """Interactive log viewer with support for JSON and plaintext log files.

    Provides both static viewing (tail) and live following (tail -f) capabilities
    with filtering by log level and keyword search.

    Parameters
    ----------
    log_file : Path
        Path to the log file to view.

    Attributes
    ----------
    log_file : Path
        Resolved path to the log file.
    console : Console
        Rich console instance for output.

    Examples
    --------
    >>> viewer = LogViewer(Path("/var/log/app.log"))
    >>> viewer.display_logs(limit=100, level="ERROR")
    >>> viewer.follow_logs(level="INFO", keyword="user")
    """

    def __init__(self, log_file: Path) -> None:
        if not _HAS_RICH:
            raise ImportError(
                "LogViewer requires the 'rich' library. "
                "Install it with: pip install rich"
            )
        self.log_file = Path(log_file).expanduser().resolve()
        self.console = Console()

    def _tail_lines(self, limit: int) -> List[str]:
        """Read the last N lines from the log file efficiently.

        Uses a chunked approach for large files (>1MB) to avoid reading
        the entire file into memory.

        Parameters
        ----------
        limit : int
            Maximum number of lines to read from the end of the file.

        Returns
        -------
        list of str
            The last `limit` lines from the file.
        """
        if _HAS_READER:
            return _LogReader(self.log_file)._tail_lines(limit)  # type: ignore[union-attr]
        # Fallback (should never occur in a normal install)
        if not self.log_file.exists():
            return []
        from collections import deque

        with self.log_file.open("r", encoding="utf-8", errors="replace") as f:
            return list(deque(f, maxlen=limit))

    def _parse_line(self, line: str) -> Tuple[str, str, str]:
        """Parse a log line into timestamp, level, and message components.

        Attempts to parse as JSON first, then falls back to standard log format.

        Parameters
        ----------
        line : str
            The raw log line to parse.

        Returns
        -------
        tuple of (str, str, str)
            Tuple of (timestamp, levelname, message). Returns "N/A" for
            components that cannot be parsed.
        """
        if _HAS_READER:
            p = _LogReader(self.log_file)._parse_line(line)  # type: ignore[union-attr]
            ts = p.timestamp if p.timestamp else "N/A"
            return ts, p.level, p.message
        # Fallback (should never occur in a normal install)
        parts = line.strip().split(" - ", maxsplit=3)
        if len(parts) == 4:
            ts, _logger, levelname, message = parts
            return ts, levelname, message
        return "N/A", "N/A", line.strip()

    def _build_table(
        self,
        limit: int,
        level: Optional[Union[int, str]] = None,
        keyword: Optional[str] = None,
    ) -> Table:
        lines = self._tail_lines(limit)
        return self._build_table_from_lines(list(lines), level, keyword)

    def _build_table_from_lines(
        self,
        lines: List[str],
        level: Optional[Union[int, str]] = None,
        keyword: Optional[str] = None,
    ) -> Table:
        keyword_low = keyword.lower() if keyword else None

        table = Table(
            show_header=True,
            header_style="bold white",
            box=box.ROUNDED,
            border_style="bright_black",
            expand=True,
        )
        table.add_column("Timestamp", style="dim", no_wrap=True, min_width=26)
        table.add_column("Level", no_wrap=True, min_width=8)
        table.add_column("Message")

        def _passes_level(levelname: str) -> bool:
            if level is None:
                return True
            try:
                target = (
                    LogLevel.from_name(level) if isinstance(level, str) else int(level)
                )
                current = LogLevel.from_name(levelname)
                return current >= target
            except Exception:
                return not (isinstance(level, int) and level > LogLevel.INFO)

        for raw in lines:
            line = raw.strip()
            if not line:
                continue

            ts, lvl, msg = self._parse_line(line)

            if not _passes_level(lvl):
                continue
            if keyword_low and keyword_low not in str(msg).lower():
                continue

            level_text = Text(lvl, style=_LEVEL_STYLES.get(lvl.upper(), "white"))
            table.add_row(ts, level_text, str(msg))

        entry_word = "entry" if table.row_count == 1 else "entries"
        table.caption = f"[dim]{table.row_count} {entry_word} shown[/dim]"
        return table

    def display_logs(
        self,
        *,
        limit: int = 200,
        level: Optional[Union[int, str]] = None,
        keyword: Optional[str] = None,
    ) -> bool:
        """Display log entries in a formatted Rich table.

        Parameters
        ----------
        limit : int, optional
            Maximum number of lines to display from the end. Default is 200.
        level : int or str or None, optional
            Minimum log level to display (e.g., "INFO" or 20). Default is None
            (show all levels).
        keyword : str or None, optional
            Only show lines containing this keyword (case-insensitive).
            Default is None (no filtering).

        Returns
        -------
        bool
            True if logs were rendered successfully, False if file not found.
        """
        if not self.log_file.exists():
            self.console.print(
                Panel(
                    f"[bold]{self.log_file}[/bold]",
                    title="[bold red] File Not Found [/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                    expand=False,
                )
            )
            return False
        table = self._build_table(limit, level, keyword)
        self.console.print(table)
        if table.row_count == 0:
            self.console.print(
                "[yellow]No log entries matched the current filters.[/yellow]"
            )
        return True

    def follow_logs(
        self,
        *,
        level: Optional[Union[int, str]] = None,
        keyword: Optional[str] = None,
        interval: float = 0.5,
        max_lines: int = 500,
    ) -> bool:
        """Live-follow the log file, displaying new lines as they are written.

        Similar to ``tail -f``, this method continuously monitors the log file
        and displays new entries in a Rich live-updating table.

        Parameters
        ----------
        level : int or str or None, optional
            Minimum log level to display. Default is None (show all levels).
        keyword : str or None, optional
            Only show lines containing this keyword (case-insensitive).
            Default is None (no filtering).
        interval : float, optional
            Refresh interval in seconds. Default is 0.5.
        max_lines : int, optional
            Maximum lines to keep in the rolling display window. Default is 500.

        Returns
        -------
        bool
            True if following completed (via Ctrl+C), False if file not found.

        Notes
        -----
        - Starts at end of file (only shows new lines).
        - Automatically handles log rotation (file truncation).
        - Press Ctrl+C to stop following.
        """
        if not self.log_file.exists():
            self.console.print(
                Panel(
                    f"[bold]{self.log_file}[/bold]",
                    title="[bold red] File Not Found [/bold red]",
                    border_style="red",
                    box=box.ROUNDED,
                    expand=False,
                )
            )
            return False

        # Rolling buffer of *raw* lines to feed batch renderer
        window: deque[str] = deque(maxlen=max_lines)

        # Start with a headers-only table; show a "waiting" placeholder caption
        table = self._build_table_from_lines([], level, keyword)
        table.caption = "[dim]Waiting for new log entries…[/dim]"

        # Configure Live (only override refresh rate if interval > 0)
        live_kwargs = {"console": self.console, "transient": True}
        if interval > 0:
            live_kwargs["refresh_per_second"] = max(1, int(1.0 / interval))

        try:
            with self.log_file.open("r", encoding="utf-8", errors="replace") as f:
                # Start at EOF — only new lines will be shown
                f.seek(0, os.SEEK_END)
                try:
                    last_size = os.fstat(f.fileno()).st_size
                except OSError:
                    last_size = 0  # type: ignore[arg-type]

                with Live(table, **live_kwargs) as live:
                    while True:
                        try:
                            cur_size = os.fstat(f.fileno()).st_size
                        except OSError:
                            cur_size = 0
                        if cur_size < last_size:
                            f.seek(0, os.SEEK_SET)
                            last_size = cur_size

                        pos = f.tell()
                        line = f.readline()
                        if not line:
                            f.seek(pos)
                            last_size = cur_size
                            if interval > 0:
                                time.sleep(interval)
                            continue

                        window.append(line)
                        new_table = self._build_table_from_lines(
                            list(window), level, keyword
                        )
                        live.update(new_table)
                        table = new_table
                        last_size = cur_size
        except KeyboardInterrupt:
            return True

        return True
