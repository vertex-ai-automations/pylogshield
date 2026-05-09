# src/pylogshield/tui/widgets.py
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Input, Label, Static


# ── TopBar ────────────────────────────────────────────────────────────────

class TopBar(Static):
    """Search input + stats + live/static indicator in one compact bar."""

    DEFAULT_CSS = """
    TopBar {
        height: 3;
        background: $surface;
        border-bottom: solid $accent 50%;
        layout: horizontal;
        padding: 0 1;
        align: left middle;
    }
    TopBar #app-label { color: $accent; width: auto; margin-right: 1; }
    TopBar #file-label { color: $text-muted; width: auto; margin-right: 2; }
    TopBar #search-input { width: 1fr; }
    TopBar #regex-label { color: $warning; width: auto; margin-left: 1; display: none; }
    TopBar #regex-label.active { display: block; }
    TopBar #stats-label { color: $text-muted; width: auto; margin-left: 2; }
    TopBar #mode-label { width: auto; margin-left: 1; }
    TopBar #mode-label.live { color: $success; }
    TopBar #mode-label.static { color: $text-muted; }
    """

    def __init__(self, path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._path = path

    def compose(self) -> ComposeResult:
        yield Label("PyLogShield", id="app-label")
        yield Label(str(self._path), id="file-label")
        yield Input(placeholder="search…", id="search-input")
        yield Label("[re]", id="regex-label")
        yield Label("", id="stats-label")
        yield Label("○ STATIC", id="mode-label", classes="static")

    def update_stats(self, filtered: list, all_rows: list) -> None:
        counts: Counter = Counter(r.level for r in all_rows)
        parts = []
        for lvl, abbr, colour in [
            ("CRITICAL", "C", "red"),
            ("ERROR", "E", "red"),
            ("WARNING", "W", "yellow"),
            ("INFO", "I", "green"),
            ("DEBUG", "D", "dim"),
        ]:
            n = counts.get(lvl, 0)
            if n:
                parts.append(f"[{colour}]{n}{abbr}[/{colour}]")
        total = f"{len(filtered)} of {len(all_rows)}"
        self.query_one("#stats-label", Label).update(
            "  ".join(parts) + f"  [{total}]" if parts else total
        )

    def set_following(self, active: bool) -> None:
        lbl = self.query_one("#mode-label", Label)
        if active:
            lbl.update("● LIVE")
            lbl.set_classes("live")
        else:
            lbl.update("○ STATIC")
            lbl.set_classes("static")

    def set_regex(self, active: bool) -> None:
        lbl = self.query_one("#regex-label", Label)
        if active:
            lbl.add_class("active")
        else:
            lbl.remove_class("active")

import re as _re
from textual.message import Message
from textual.widgets import DataTable
from rich.text import Text

_LEVEL_STYLES = {
    "CRITICAL": "bold red",
    "ERROR": "red",
    "WARNING": "yellow",
    "INFO": "green",
    "DEBUG": "dim",
}


class LogTable(Static):
    """Scrollable, colour-coded log table backed by a Textual DataTable."""

    class ScrolledUp(Message):
        """Posted when the user scrolls up while in follow mode."""

    class Resumed(Message):
        """Posted when the user presses End to go back to the bottom."""

    DEFAULT_CSS = """
    LogTable { height: 1fr; }
    LogTable DataTable { height: 1fr; }
    LogTable #error-panel { height: 1fr; color: $error; content-align: center middle; }
    """

    def compose(self) -> ComposeResult:
        yield DataTable(cursor_type="row", zebra_stripes=True, id="data-table")

    def on_mount(self) -> None:
        tbl = self.query_one(DataTable)
        tbl.add_columns(
            "Timestamp", "Level", "Logger", "Location", "Message"
        )

    def load_rows(
        self,
        rows: list,
        search_text: str = "",
        use_regex: bool = False,
        mark_new: bool = False,
    ) -> None:
        tbl = self.query_one(DataTable)
        tbl.clear()
        self._row_map: dict = {}
        pat = None
        if search_text:
            try:
                pat = _re.compile(
                    search_text if use_regex else _re.escape(search_text),
                    _re.IGNORECASE,
                )
            except _re.error:
                pass

        for i, row in enumerate(rows):
            style = _LEVEL_STYLES.get(row.level, "")
            loc = f"{row.module}:{row.lineno}" if row.module else "N/A"

            msg = row.message
            if mark_new and i == len(rows) - 1:
                msg = msg + "  [NEW]"

            if pat:
                msg_text = Text(msg)
                for m in pat.finditer(msg):
                    msg_text.stylize("bold yellow", m.start(), m.end())
                message_cell = msg_text
            else:
                message_cell = Text(msg, style=style)

            key = str(id(row))
            self._row_map[key] = row
            tbl.add_row(
                Text(row.timestamp, style="dim"),
                Text(row.level, style=style),
                Text(row.logger, style=style),
                Text(loc, style="dim"),
                message_cell,
                key=key,
            )

    def show_error(self, message: str) -> None:
        self.query_one(DataTable).display = False
        self.mount(Label(message, id="error-panel"))

    def on_data_table_row_selected(self, event) -> None:
        """Expand a detail panel for the selected row (Enter key)."""
        key = str(event.row_key.value) if event.row_key else None
        if not key:
            return
        row = getattr(self, "_row_map", {}).get(key)
        if row is None:
            return
        self.app.push_screen(DetailModal(row))

    def on_key(self, event) -> None:
        if event.key == "end":
            self.post_message(self.Resumed())
        elif event.key in ("up", "pageup"):
            self.post_message(self.ScrolledUp())
