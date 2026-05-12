from __future__ import annotations

import csv
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from pylogshield.tui.reader import ParsedLine


class Exporter:
    """Write a list of ParsedLine rows to one of four formats."""

    def __init__(self, rows: List[ParsedLine], filepath: Path) -> None:
        self._rows = rows
        self._filepath = Path(filepath)

    def to_csv(self) -> None:
        """UTF-8 with BOM so Excel opens it correctly."""
        fieldnames = ["timestamp", "level", "logger", "module", "lineno", "message"]
        extra_keys: list[str] = []
        for row in self._rows:
            for k in row.extra:
                if k not in extra_keys:
                    extra_keys.append(k)
        all_fields = fieldnames + extra_keys

        with self._filepath.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
            writer.writeheader()
            for row in self._rows:
                d = {
                    "timestamp": row.timestamp,
                    "level": row.level,
                    "logger": row.logger,
                    "module": row.module,
                    "lineno": row.lineno,
                    "message": row.message,
                }
                d.update(row.extra)
                writer.writerow(d)

    def to_json(self) -> None:
        data = [
            {
                "timestamp": r.timestamp,
                "level": r.level,
                "logger": r.logger,
                "module": r.module,
                "lineno": r.lineno,
                "message": r.message,
                "extra": r.extra,
            }
            for r in self._rows
        ]
        self._filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def to_text(self) -> None:
        lines = []
        for r in self._rows:
            loc = f"{r.module}:{r.lineno}" if r.module else ""
            parts = [r.timestamp, f"{r.level:<8}", r.logger]
            if loc:
                parts.append(loc)
            parts.append(r.message)
            lines.append("  ".join(parts))
        self._filepath.write_text("\n".join(lines), encoding="utf-8")

    def to_html(self) -> None:
        counts: Counter[str] = Counter(r.level for r in self._rows)
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        ts_range = ""
        if self._rows:
            ts_range = (
                f"{html.escape(self._rows[0].timestamp)} → "
                f"{html.escape(self._rows[-1].timestamp)}"
            )

        stats_html = " &nbsp;·&nbsp; ".join(
            f'<span style="color:{_LEVEL_COLOURS.get(lvl, "#ccc")}">'
            f"{cnt} {html.escape(lvl)}</span>"
            for lvl, cnt in sorted(
                counts.items(), key=lambda x: _LEVEL_ORDER.get(x[0], 99)
            )
        )

        rows_html = "\n".join(
            f"<tr>"
            f"<td>{html.escape(r.timestamp)}</td>"
            f'<td style="color:{_LEVEL_COLOURS.get(r.level, "#ccc")}">{html.escape(r.level)}</td>'
            f"<td>{html.escape(r.logger)}</td>"
            f"<td>{html.escape(r.module)}:{r.lineno}</td>"
            f"<td>{html.escape(r.message)}</td>"
            f"</tr>"
            for r in self._rows
        )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
<title>PyLogShield Export</title>
<style>
body {{ font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }}
h1 {{ color: #58a6ff; }}
.stats {{ margin-bottom: 16px; color: #8b949e; }}
table {{ border-collapse: collapse; width: 100%; }}
th {{ background: #161b22; color: #8b949e; padding: 6px 12px; text-align: left; border-bottom: 1px solid #30363d; }}
td {{ padding: 4px 12px; border-bottom: 1px solid #1c2128; }}
tr:hover td {{ background: #1c2128; }}
.footer {{ margin-top: 16px; color: #6e7681; font-size: 12px; }}
</style>
</head>
<body>
<h1>PyLogShield Log Export</h1>
<div class="stats">
  {len(self._rows)} rows &nbsp;·&nbsp; {stats_html}<br>
  Time range: {ts_range}
</div>
<table>
<tr><th>Timestamp</th><th>Level</th><th>Logger</th><th>Location</th><th>Message</th></tr>
{rows_html}
</table>
<div class="footer">Exported: {now}</div>
</body>
</html>"""
        self._filepath.write_text(html_content, encoding="utf-8")


_LEVEL_COLOURS = {
    "CRITICAL": "#ff7b72",
    "ERROR": "#f85149",
    "WARNING": "#d29922",
    "INFO": "#3fb950",
    "DEBUG": "#6e7681",
}
_LEVEL_ORDER = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3, "DEBUG": 4}
