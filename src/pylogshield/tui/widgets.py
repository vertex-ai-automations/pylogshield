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

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._row_map: dict = {}

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
        self._row_map = {}
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
        row = self._row_map.get(key)
        if row is None:
            return
        self.app.push_screen(DetailModal(row))

    def on_key(self, event) -> None:
        if event.key == "end":
            self.post_message(self.Resumed())
        elif event.key in ("up", "pageup"):
            self.post_message(self.ScrolledUp())


import json as _json
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, RadioButton, RadioSet


class FilterChipBar(Static):
    """Shows active filters as removable chip labels."""

    DEFAULT_CSS = """
    FilterChipBar {
        height: 3;
        background: $surface-darken-1;
        layout: horizontal;
        align: left middle;
        padding: 0 1;
        border-top: solid $accent 20%;
    }
    FilterChipBar .chip-label { color: $text-muted; margin-right: 1; }
    FilterChipBar .chip { background: $accent 20%; color: $accent;
                          margin-right: 1; padding: 0 1; }
    FilterChipBar .add-hint { color: $text-muted; opacity: 0.6; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = None

    def compose(self) -> ComposeResult:
        yield Label("Filters", classes="chip-label")
        yield Label("none active", classes="add-hint", id="chip-list")

    def update_chips(self, state) -> None:
        from pylogshield.tui.app import _ALL_LEVELS
        self._state = state
        chips = []
        if state.levels != _ALL_LEVELS:
            min_sev = min(
                {"CRITICAL": 50, "ERROR": 40, "WARNING": 30,
                 "INFO": 20, "DEBUG": 10}.get(l, 0)
                for l in state.levels
            )
            label = {50: "CRITICAL+", 40: "ERROR+", 30: "WARNING+",
                     20: "INFO+", 10: "DEBUG+"}.get(min_sev, "custom")
            chips.append(label)
        if state.time_range != "all":
            chips.append(state.time_range)
        if state.logger_name:
            chips.append(f"logger:{state.logger_name}")

        chip_lbl = self.query_one("#chip-list", Label)
        if chips:
            chip_lbl.update("  ".join(f"[{c}]" for c in chips) + "  + add filter")
        else:
            chip_lbl.update("none active  + add filter")


class DetailModal(ModalScreen):
    """Full detail view for a single log row (Enter to open, Esc to close)."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    DetailModal { align: center middle; }
    DetailModal > Vertical {
        width: 80; height: auto; max-height: 80%;
        background: $surface; border: solid $accent; padding: 1 2;
    }
    DetailModal .detail-title { color: $accent; margin-bottom: 1; }
    DetailModal .detail-field { margin-bottom: 0; }
    DetailModal .section-title { color: $text-muted; margin-top: 1; }
    """

    def __init__(self, row, **kwargs) -> None:
        super().__init__(**kwargs)
        self._row = row

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        r = self._row
        with Vertical():
            yield Label("Row Detail", classes="detail-title")
            for lbl, value in [
                ("Timestamp", r.timestamp),
                ("Level", r.level),
                ("Logger", r.logger),
                ("Location", f"{r.module}:{r.lineno}" if r.module else "N/A"),
                ("Message", r.message),
            ]:
                yield Label(f"[bold]{lbl}:[/bold]  {value}", classes="detail-field")
            if r.extra:
                yield Label(
                    f"[bold]Extra:[/bold]  {_json.dumps(r.extra, default=str)}",
                    classes="detail-field",
                )
            yield Label("", classes="detail-field")
            yield Label(f"[dim]{r.raw}[/dim]", classes="detail-field")
            yield Label("Esc to close", classes="section-title")


class FilterPanel(ModalScreen):
    """Modal filter configuration panel."""

    BINDINGS = [
        Binding("escape", "dismiss_default", "Close"),
        Binding("r", "reset_filters", "Reset"),
    ]

    DEFAULT_CSS = """
    FilterPanel { align: center middle; }
    FilterPanel > Vertical {
        width: 60; height: auto;
        background: $surface; border: solid $accent; padding: 1 2;
    }
    FilterPanel .panel-title { color: $accent; margin-bottom: 1; }
    FilterPanel .section-title { color: $text-muted; margin-top: 1; }
    FilterPanel Button { margin-top: 1; }
    """

    def __init__(self, state, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = state

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        with Vertical():
            yield Label("Filter Panel", classes="panel-title")

            yield Label("Log Levels", classes="section-title")
            for lvl in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
                yield Checkbox(
                    lvl,
                    value=(lvl in self._state.levels),
                    id=f"lvl-{lvl.lower()}",
                )

            yield Label("Time Range", classes="section-title")
            with RadioSet(id="time-range"):
                for lbl, value in [
                    ("All time", "all"),
                    ("Last 1h", "1h"),
                    ("Last 6h", "6h"),
                    ("Last 24h", "24h"),
                ]:
                    yield RadioButton(
                        lbl,
                        value=(self._state.time_range == value),
                        id=f"tr-{value}",
                    )

            yield Label("Logger name (substring)", classes="section-title")
            yield Input(
                value=self._state.logger_name,
                placeholder="e.g. myapp",
                id="logger-input",
            )

            yield Button("Apply  [Esc]", variant="primary", id="apply-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-btn":
            self._collect_and_dismiss()

    def action_dismiss_default(self) -> None:
        self._collect_and_dismiss()

    def action_reset_filters(self) -> None:
        from pylogshield.tui.app import FilterState
        self.dismiss(FilterState())

    def _collect_and_dismiss(self) -> None:
        from pylogshield.tui.app import FilterState
        levels = set()
        for lvl in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
            cb = self.query_one(f"#lvl-{lvl.lower()}", Checkbox)
            if cb.value:
                levels.add(lvl)

        time_range = "all"
        for lbl, value in [("All time", "all"), ("Last 1h", "1h"),
                             ("Last 6h", "6h"), ("Last 24h", "24h")]:
            rb = self.query_one(f"#tr-{value}", RadioButton)
            if rb.value:
                time_range = value
                break

        logger_name = self.query_one("#logger-input", Input).value.strip()
        new_state = FilterState(
            levels=levels or {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"},
            time_range=time_range,
            logger_name=logger_name,
            search_text=self._state.search_text,
            search_regex=self._state.search_regex,
        )
        self.dismiss(new_state)

from datetime import date as _date


class ExportModal(ModalScreen):
    """Four-format export picker."""

    BINDINGS = [Binding("escape", "dismiss", "Cancel")]

    DEFAULT_CSS = """
    ExportModal { align: center middle; }
    ExportModal > Vertical {
        width: 60; height: auto;
        background: $surface; border: solid $accent; padding: 1 2;
    }
    ExportModal .modal-title { color: $accent; margin-bottom: 1; }
    ExportModal .export-opt { margin-bottom: 0; }
    ExportModal #export-status { color: $success; margin-top: 1; display: none; }
    ExportModal #export-status.visible { display: block; }
    ExportModal #export-error { color: $error; margin-top: 1; display: none; }
    ExportModal #export-error.visible { display: block; }
    """

    _FORMATS = [
        ("csv",  "CSV (Excel-compatible)"),
        ("json", "JSON"),
        ("txt",  "Plain text"),
        ("html", "HTML report"),
    ]

    def __init__(self, rows: list, log_path: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rows = rows
        self._log_path = log_path

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        stem = self._log_path.stem
        today = _date.today().isoformat()
        with Vertical():
            yield Label(
                f"Export {len(self._rows)} rows",
                classes="modal-title",
            )
            for ext, lbl in self._FORMATS:
                filename = f"{stem}-export-{today}.{ext}"
                yield Button(
                    f"{lbl}  →  {filename}",
                    id=f"export-{ext}",
                    classes="export-opt",
                )
            yield Label("", id="export-status")
            yield Label("", id="export-error")
            yield Label(
                "Esc to cancel · Exports to current directory",
                classes="section-title",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        ext = event.button.id.removeprefix("export-")
        stem = self._log_path.stem
        today = _date.today().isoformat()
        out = Path(f"{stem}-export-{today}.{ext}")
        from pylogshield.tui.exporter import Exporter
        exp = Exporter(self._rows, out)
        try:
            {"csv": exp.to_csv, "json": exp.to_json,
             "txt": exp.to_text, "html": exp.to_html}[ext]()
            status = self.query_one("#export-status", Label)
            status.update(f"Saved → {out.resolve()}")
            status.add_class("visible")
        except Exception as exc:
            err = self.query_one("#export-error", Label)
            err.update(f"Export failed: {exc}")
            err.add_class("visible")


class HelpModal(ModalScreen):
    """Two-column keyboard reference overlay."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpModal { align: center middle; }
    HelpModal > Vertical {
        width: 72; height: auto;
        background: $surface; border: solid $accent; padding: 1 2;
    }
    HelpModal .help-title { color: $accent; margin-bottom: 1; }
    HelpModal .col { width: 1fr; }
    HelpModal .section-title { color: $text-muted; }
    """

    _BINDINGS_TABLE = [
        ("Navigation", [
            ("↑ ↓", "Move between rows"),
            ("PgUp PgDn", "Page up / down"),
            ("Home / End", "First / last row (End resumes follow)"),
            ("Enter", "Expand row detail"),
        ]),
        ("Search & Filter", [
            ("/", "Focus search bar"),
            ("Ctrl+R", "Toggle regex mode"),
            ("Esc", "Clear search / close modal"),
            ("Ctrl+F", "Open filter panel"),
        ]),
        ("View & Actions", [
            ("F", "Toggle live follow"),
            ("E", "Open export modal"),
            ("?", "Show / hide this help"),
            ("Q / Ctrl+C", "Quit"),
        ]),
    ]

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, Vertical
        with Vertical():
            yield Label("PyLogShield — Keyboard Reference", classes="help-title")
            with Horizontal():
                for section, keys in self._BINDINGS_TABLE:
                    with Vertical(classes="col"):
                        yield Label(section, classes="section-title")
                        for key, desc in keys:
                            yield Label(f"  [{key}]  {desc}")
            yield Label("Press Esc or ? to close", classes="section-title")
