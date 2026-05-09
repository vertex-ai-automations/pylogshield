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
