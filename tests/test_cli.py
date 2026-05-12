"""Tests for the CLI commands (view, levels)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pylogshield.cli import app

runner = CliRunner()


@pytest.fixture()
def log_file(tmp_path: Path) -> Path:
    f = tmp_path / "app.log"
    f.write_text(
        "2026-05-12 10:00:00.001  INFO      myapp  core:10  Server started\n"
        "2026-05-12 10:00:01.002  WARNING   myapp  core:20  High memory\n"
        "2026-05-12 10:00:02.003  ERROR     myapp  core:30  Connection lost\n"
    )
    return f


@pytest.fixture()
def json_log_file(tmp_path: Path) -> Path:
    import json

    f = tmp_path / "app.json.log"
    lines = [
        {
            "timestamp": "2026-05-12T10:00:00.001+00:00",
            "level": "INFO",
            "logger": "app",
            "message": "started",
        },
        {
            "timestamp": "2026-05-12T10:00:01.002+00:00",
            "level": "ERROR",
            "logger": "app",
            "message": "crashed",
        },
    ]
    f.write_text("\n".join(json.dumps(entry) for entry in lines) + "\n")
    return f


class TestViewCommand:
    def test_view_exits_zero_on_existing_file(self, log_file):
        result = runner.invoke(app, ["view", "--file", str(log_file)])
        assert result.exit_code == 0

    def test_view_exits_one_on_missing_file(self, tmp_path):
        result = runner.invoke(app, ["view", "--file", str(tmp_path / "missing.log")])
        assert result.exit_code != 0

    def test_view_level_filter(self, log_file):
        result = runner.invoke(
            app, ["view", "--file", str(log_file), "--level", "ERROR"]
        )
        assert result.exit_code == 0
        assert "ERROR" in result.output

    def test_view_keyword_filter(self, log_file):
        result = runner.invoke(
            app, ["view", "--file", str(log_file), "--keyword", "memory"]
        )
        assert result.exit_code == 0
        assert "memory" in result.output.lower()

    def test_view_limit(self, log_file):
        result = runner.invoke(app, ["view", "--file", str(log_file), "--limit", "1"])
        assert result.exit_code == 0

    def test_view_json_log(self, json_log_file):
        result = runner.invoke(app, ["view", "--file", str(json_log_file)])
        assert result.exit_code == 0


class TestLevelsCommand:
    def test_levels_exits_zero(self):
        result = runner.invoke(app, ["levels"])
        assert result.exit_code == 0

    def test_levels_output_contains_standard_levels(self):
        result = runner.invoke(app, ["levels"])
        for level in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"):
            assert level in result.output

    def test_levels_output_contains_numeric_values(self):
        result = runner.invoke(app, ["levels"])
        for value in ("50", "40", "30", "20", "10"):
            assert value in result.output


class TestVersionFlag:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "PyLogShield" in result.output
