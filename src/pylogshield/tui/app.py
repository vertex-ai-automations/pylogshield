# src/pylogshield/tui/app.py
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Set

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static

from pylogshield.tui.reader import LogReader, ParsedLine


@dataclass
class FilterState:
    levels: Set[str] = field(
        default_factory=lambda: {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
    )
    time_range: str = "all"       # "1h", "6h", "24h", "all"
    logger_name: str = ""         # substring match, case-insensitive
    search_text: str = ""
    search_regex: bool = False


_ALL_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
_LEVEL_SEVERITY = {"CRITICAL": 50, "ERROR": 40, "WARNING": 30, "INFO": 20, "DEBUG": 10}


class LogViewerApp(App[None]):
    """Interactive TUI log viewer."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f", "toggle_follow", "Follow"),
        Binding("ctrl+f", "open_filters", "Filters"),
        Binding("e", "open_export", "Export"),
        Binding("question_mark", "open_help", "Help"),
        Binding("/", "focus_search", "Search", show=False),
        Binding("ctrl+r", "toggle_regex", "Regex", show=False),
    ]

    CSS = """
    Screen { layers: base overlay; }
    #pause-banner {
        height: 1;
        background: $warning 30%;
        color: $warning;
        content-align: center middle;
        display: none;
    }
    #pause-banner.visible { display: block; }
    """

    def __init__(
        self,
        log_path: Path,
        initial_level: Optional[str] = None,
        start_following: bool = False,
    ) -> None:
        super().__init__()
        self._path = log_path
        self._reader = LogReader(log_path)
        self._all_rows: List[ParsedLine] = []
        self._filtered_rows: List[ParsedLine] = []
        self._filter_state = FilterState()
        if initial_level:
            severity = _LEVEL_SEVERITY.get(initial_level.upper(), 0)
            self._filter_state.levels = {
                lvl for lvl, sev in _LEVEL_SEVERITY.items() if sev >= severity
            }
        self._following = start_following
        self._paused = False
        self._follow_thread: Optional[threading.Thread] = None

    def compose(self) -> ComposeResult:
        from pylogshield.tui.widgets import FilterChipBar, LogTable, TopBar
        yield TopBar(self._path, id="top-bar")
        yield Static("⏸  Scrolled up — live follow paused. Press End to resume.",
                     id="pause-banner")
        yield LogTable(id="log-table")
        yield FilterChipBar(id="filter-chips")
        yield Footer()

    def on_mount(self) -> None:
        if not self._path.exists():
            self.query_one("#log-table").show_error(
                f"File not found: {self._path}"
            )
            return
        self._all_rows = self._reader.tail(5000)
        self._apply_filters()
        if self._following:
            self._start_follow()

    # ── filter pipeline ───────────────────────────────────────────────────

    def _apply_filters(self, mark_new: bool = False) -> None:
        fs = self._filter_state
        rows = self._all_rows

        if fs.levels != _ALL_LEVELS:
            rows = [r for r in rows if r.level in fs.levels]

        if fs.time_range != "all":
            cutoff = self._time_cutoff(fs.time_range)
            if cutoff:
                rows = [r for r in rows if self._parse_ts(r.timestamp) >= cutoff]

        if fs.logger_name:
            needle = fs.logger_name.lower()
            rows = [r for r in rows if needle in r.logger.lower()]

        if fs.search_text:
            if fs.search_regex:
                try:
                    pat = re.compile(fs.search_text, re.IGNORECASE)
                    rows = [r for r in rows if pat.search(r.message)]
                except re.error:
                    pass
            else:
                needle = fs.search_text.lower()
                rows = [r for r in rows if needle in r.message.lower()]

        self._filtered_rows = rows
        self._refresh_table(mark_new)
        self._refresh_stats()

    @staticmethod
    def _time_cutoff(time_range: str) -> Optional[datetime]:
        hours = {"1h": 1, "6h": 6, "24h": 24}.get(time_range)
        if hours is None:
            return None
        return datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        # Try full string first so ISO 8601 timezone offsets (+00:00) are not
        # truncated. Fall back to 23-char slice for plain-text variants that
        # may have trailing whitespace or extra content.
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S,%f",
        ):
            for candidate in (ts, ts[:23]):
                try:
                    dt = datetime.strptime(candidate, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
        return datetime.min.replace(tzinfo=timezone.utc)

    def _refresh_table(self, mark_new: bool = False) -> None:
        try:
            self.query_one("#log-table").load_rows(
                self._filtered_rows, self._filter_state.search_text,
                self._filter_state.search_regex, mark_new,
            )
        except Exception:
            pass

    def _refresh_stats(self) -> None:
        try:
            self.query_one("#top-bar").update_stats(self._filtered_rows, self._all_rows)
        except Exception:
            pass

    # ── live follow ───────────────────────────────────────────────────────

    def _start_follow(self) -> None:
        self._reader._stop.clear()
        self._following = True
        self._paused = False
        self._follow_thread = threading.Thread(
            target=self._reader.follow,
            args=(self._on_new_line,),
            daemon=True,
        )
        self._follow_thread.start()
        try:
            self.query_one("#top-bar").set_following(True)
        except Exception:
            pass

    def _stop_follow(self) -> None:
        self._reader.stop()
        if self._follow_thread is not None:
            self._follow_thread.join(timeout=1.0)
            self._follow_thread = None
        self._following = False
        self._paused = False
        try:
            self.query_one("#top-bar").set_following(False)
            self.query_one("#pause-banner").remove_class("visible")
        except Exception:
            pass

    def _on_new_line(self, line: ParsedLine) -> None:
        """Called from the follow background thread."""
        self.call_from_thread(self._append_live_row, line)

    def _append_live_row(self, line: ParsedLine) -> None:
        self._all_rows.append(line)
        self._apply_filters(mark_new=True)

    # ── actions ───────────────────────────────────────────────────────────

    def action_toggle_follow(self) -> None:
        if self._following:
            self._stop_follow()
        else:
            self._start_follow()

    def action_focus_search(self) -> None:
        try:
            self.query_one("#search-input").focus()
        except Exception:
            pass

    def action_toggle_regex(self) -> None:
        self._filter_state.search_regex = not self._filter_state.search_regex
        self._apply_filters()
        try:
            self.query_one("#top-bar").set_regex(self._filter_state.search_regex)
        except Exception:
            pass

    def action_open_filters(self) -> None:
        from pylogshield.tui.widgets import FilterPanel
        self.push_screen(FilterPanel(self._filter_state), self._on_filter_result)

    def _on_filter_result(self, state: FilterState) -> None:
        self._filter_state = state
        self._apply_filters()
        try:
            self.query_one("#filter-chips").update_chips(state)
        except Exception:
            pass

    def action_open_export(self) -> None:
        from pylogshield.tui.widgets import ExportModal
        self.push_screen(ExportModal(self._filtered_rows, self._path))

    def action_open_help(self) -> None:
        from pylogshield.tui.widgets import HelpModal
        self.push_screen(HelpModal())

    def on_log_table_scrolled_up(self) -> None:
        if self._following and not self._paused:
            self._paused = True
            try:
                self.query_one("#pause-banner").add_class("visible")
            except Exception:
                pass

    def on_log_table_resumed(self) -> None:
        self._paused = False
        try:
            self.query_one("#pause-banner").remove_class("visible")
        except Exception:
            pass

    def on_input_changed(self, event) -> None:
        if event.input.id == "search-input":
            self._filter_state.search_text = event.value
            self._apply_filters()

    def on_unmount(self) -> None:
        """Stop the follow thread cleanly when the app closes."""
        self._reader.stop()
