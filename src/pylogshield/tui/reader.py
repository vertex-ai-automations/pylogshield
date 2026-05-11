from __future__ import annotations

import json
import os
import re
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Matches the current PyLogShield standard formatter:
# "%(asctime)s.%(msecs)03d  %(levelname)-8s  %(name)s  %(module)s:%(lineno)d  %(message)s"
_NEW_STD = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s{2}"
    r"(\w+)\s+"
    r"(\S+)\s+"
    r"(\S+):(\d+)\s{2}"
    r"(.+)$"
)
# Matches the old PyLogShield standard formatter:
# "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_OLD_STD = re.compile(
    r"^(.+?) - (\S+) - (\w+) - (.+)$"
)


@dataclass
class ParsedLine:
    timestamp: str
    level: str
    logger: str
    module: str
    lineno: int
    message: str
    raw: str
    extra: Dict[str, object] = field(default_factory=dict)


class LogReader:
    """Reads, parses, and optionally follows a log file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self._stop_lock = threading.Lock()
        self._stop: threading.Event = threading.Event()
        self._stop.set()  # Idle state: no active follow session

    def _parse_line(self, line: str) -> ParsedLine:
        line = line.rstrip("\r\n")
        if not line.strip():
            return ParsedLine("", "N/A", "", "", 0, "", line)

        # JSON format
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError("not a dict")
            extra = {
                k: v for k, v in entry.items()
                if k not in {"timestamp", "level", "logger", "message", "host",
                             "exc_info", "stack_info", "module", "lineno"}
            }
            return ParsedLine(
                timestamp=entry.get("timestamp", "N/A"),
                level=entry.get("level", "N/A"),
                logger=entry.get("logger", ""),
                module=str(entry.get("module", "")),
                lineno=int(entry.get("lineno") or 0),
                message=str(entry.get("message", "")),
                raw=line,
                extra=extra,
            )
        except (json.JSONDecodeError, ValueError):
            pass

        # New standard format
        m = _NEW_STD.match(line)
        if m:
            ts, lvl, logger, module, lineno, msg = m.groups()
            return ParsedLine(
                timestamp=ts,
                level=lvl.strip(),
                logger=logger,
                module=module,
                lineno=int(lineno),
                message=msg,
                raw=line,
            )

        # Old standard format
        m = _OLD_STD.match(line)
        if m:
            ts, logger, lvl, msg = m.groups()
            return ParsedLine(
                timestamp=ts,
                level=lvl,
                logger=logger,
                module="",
                lineno=0,
                message=msg,
                raw=line,
            )

        return ParsedLine("N/A", "N/A", "", "", 0, line, line)

    def _tail_lines(self, limit: int) -> List[str]:
        if not self.path.exists():
            return []
        file_size = self.path.stat().st_size
        if file_size < 1_000_000:
            with self.path.open("r", encoding="utf-8", errors="replace") as f:
                return list(deque(f, maxlen=limit))

        chunk_size = 8192
        byte_lines: List[bytes] = []
        with self.path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            remaining = f.tell()
            buffer: bytes = b""
            while remaining > 0 and len(byte_lines) < limit:
                read_size = min(chunk_size, remaining)
                remaining -= read_size
                f.seek(remaining)
                chunk = f.read(read_size)
                buffer = chunk + buffer
                split_lines = buffer.splitlines()
                if len(split_lines) > 1:
                    byte_lines = split_lines[1:] + byte_lines
                    buffer = split_lines[0]
            if buffer:
                byte_lines = [buffer.strip()] + byte_lines

        lines = [bl.decode("utf-8", errors="replace") for bl in byte_lines]
        return lines[-limit:]

    def tail(self, limit: int = 5000) -> List[ParsedLine]:
        return [
            self._parse_line(line)
            for line in self._tail_lines(limit)
            if line.strip()
        ]

    def follow(
        self,
        callback: Callable[[ParsedLine], None],
        interval: float = 0.25,
    ) -> None:
        """Block until stop() is called, invoking callback for each new line.

        Creates a fresh stop event for each session so that a concurrent or
        prior stop() call cannot race with the new session starting.
        """
        stop = threading.Event()
        with self._stop_lock:
            self._stop = stop  # Atomically publish new session event

        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(0, os.SEEK_END)
            last_size = f.tell()
            while not stop.is_set():
                try:
                    cur_size = os.fstat(f.fileno()).st_size
                except OSError:
                    stop.wait(interval)
                    continue
                if cur_size < last_size:
                    f.seek(0)
                line = f.readline()
                if not line:
                    last_size = cur_size
                    stop.wait(interval)
                    continue
                callback(self._parse_line(line))
                last_size = cur_size

    def stop(self) -> None:
        with self._stop_lock:
            self._stop.set()
