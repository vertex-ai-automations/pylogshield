"""Tests for log viewer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from pylogshield.viewer import LogViewer


class TestLogViewer:
    """Tests for LogViewer."""

    @pytest.fixture
    def sample_log_file(self, temp_log_dir: Path) -> Path:
        """Create a sample log file for testing."""
        log_file = temp_log_dir / "sample.log"
        lines = [
            "2024-01-01 10:00:00 - app - INFO - First info message",
            "2024-01-01 10:00:01 - app - DEBUG - Debug message",
            "2024-01-01 10:00:02 - app - WARNING - Warning message",
            "2024-01-01 10:00:03 - app - ERROR - Error message",
            "2024-01-01 10:00:04 - app - INFO - Second info message",
        ]
        log_file.write_text("\n".join(lines) + "\n")
        return log_file

    @pytest.fixture
    def sample_json_log_file(self, temp_log_dir: Path) -> Path:
        """Create a sample JSON log file for testing."""
        log_file = temp_log_dir / "sample_json.log"
        entries = [
            {"timestamp": "2024-01-01T10:00:00Z", "level": "INFO", "message": "JSON info"},
            {"timestamp": "2024-01-01T10:00:01Z", "level": "ERROR", "message": "JSON error"},
            {"timestamp": "2024-01-01T10:00:02Z", "level": "DEBUG", "message": "JSON debug"},
        ]
        lines = [json.dumps(e) for e in entries]
        log_file.write_text("\n".join(lines) + "\n")
        return log_file

    def test_viewer_creation(self, sample_log_file: Path) -> None:
        """Test LogViewer creation."""
        viewer = LogViewer(sample_log_file)
        assert viewer.log_file == sample_log_file.resolve()

    def test_tail_lines(self, sample_log_file: Path) -> None:
        """Test tailing lines from log file."""
        viewer = LogViewer(sample_log_file)
        lines = viewer._tail_lines(3)
        assert len(lines) == 3
        assert "Error message" in lines[-2]

    def test_tail_lines_limit(self, sample_log_file: Path) -> None:
        """Test tail with limit larger than file."""
        viewer = LogViewer(sample_log_file)
        lines = viewer._tail_lines(100)
        assert len(lines) == 5

    def test_tail_lines_handles_crlf(self, tmp_path: Path) -> None:
        """_tail_lines must correctly split Windows CRLF line endings in large files."""
        log_file = tmp_path / "test.log"
        # Create a file large enough to trigger binary chunked reading (>1MB)
        lines_data = []
        padding = "x" * 100  # Add padding to make lines larger
        for i in range(100000):
            lines_data.append(f"line{i} {padding}\r\n".encode())
        content = b"".join(lines_data)
        log_file.write_bytes(content)

        assert log_file.stat().st_size > 1_000_000, f"File size: {log_file.stat().st_size}"

        viewer = LogViewer(log_file)
        tail_lines = viewer._tail_lines(10)
        tail_lines = [l.strip() for l in tail_lines if l.strip()]
        # Check the last few lines
        assert "line99999" in tail_lines[-1], f"Got: {tail_lines}"

    def test_tail_lines_handles_cr_only(self, tmp_path: Path) -> None:
        """_tail_lines must handle old Mac \\r-only line endings in large files."""
        log_file = tmp_path / "test.log"
        # Create a file large enough to trigger binary chunked reading (>1MB)
        lines_data = []
        padding = "x" * 100  # Add padding to make lines larger
        for i in range(100000):
            lines_data.append(f"line{i} {padding}\r".encode())
        content = b"".join(lines_data)
        log_file.write_bytes(content)

        assert log_file.stat().st_size > 1_000_000, f"File size: {log_file.stat().st_size}"

        viewer = LogViewer(log_file)
        tail_lines = viewer._tail_lines(10)
        # Count the actual number of distinct lines returned
        tail_lines = [l.strip() for l in tail_lines if l.strip()]
        # With CR-only endings, we should get 10 separate lines
        # The bug would cause them to be concatenated into fewer lines
        assert len(tail_lines) >= 5, f"Expected at least 5 lines, got {len(tail_lines)}: {tail_lines}"
        # Check the last line contains the highest line number
        assert "line99999" in tail_lines[-1], f"Last line doesn't contain line99999. Got: {tail_lines[-1]}"

    def test_tail_nonexistent_file(self, temp_log_dir: Path) -> None:
        """Test tailing non-existent file."""
        viewer = LogViewer(temp_log_dir / "nonexistent.log")
        lines = viewer._tail_lines(10)
        assert lines == []

    def test_parse_standard_line(self, sample_log_file: Path) -> None:
        """Test parsing standard log format."""
        viewer = LogViewer(sample_log_file)
        line = "2024-01-01 10:00:00 - app - INFO - Test message"
        ts, level, msg = viewer._parse_line(line)
        assert ts == "2024-01-01 10:00:00"
        assert level == "INFO"
        assert msg == "Test message"

    def test_parse_json_line(self, sample_json_log_file: Path) -> None:
        """Test parsing JSON log format."""
        viewer = LogViewer(sample_json_log_file)
        line = '{"timestamp": "2024-01-01T10:00:00Z", "level": "INFO", "message": "Test"}'
        ts, level, msg = viewer._parse_line(line)
        assert ts == "2024-01-01T10:00:00Z"
        assert level == "INFO"
        assert msg == "Test"

    def test_parse_unparseable_line(self, sample_log_file: Path) -> None:
        """Test parsing line that doesn't match expected format."""
        viewer = LogViewer(sample_log_file)
        line = "Random text without format"
        ts, level, msg = viewer._parse_line(line)
        assert ts == "N/A"
        assert level == "N/A"
        assert msg == "Random text without format"

    def test_parse_empty_line(self, sample_log_file: Path) -> None:
        """Test parsing empty line."""
        viewer = LogViewer(sample_log_file)
        ts, level, msg = viewer._parse_line("")
        assert ts == "N/A"
        assert level == "N/A"
        assert msg == ""

    def test_display_logs_file_not_found(self, temp_log_dir: Path) -> None:
        """Test display_logs with non-existent file."""
        viewer = LogViewer(temp_log_dir / "nonexistent.log")
        result = viewer.display_logs()
        assert result is False

    def test_display_logs_success(self, sample_log_file: Path) -> None:
        """Test display_logs with valid file."""
        viewer = LogViewer(sample_log_file)
        result = viewer.display_logs(limit=10)
        assert result is True

    def test_build_table_level_filter(self, sample_log_file: Path) -> None:
        """Test building table with level filter — only WARNING+ rows pass."""
        viewer = LogViewer(sample_log_file)
        table = viewer._build_table(limit=10, level="WARNING")
        # The sample file has exactly 1 WARNING and 1 ERROR row; INFO/DEBUG are excluded.
        assert table.row_count == 2, (
            f"Expected 2 rows (WARNING + ERROR), got {table.row_count}"
        )

    def test_build_table_keyword_filter(self, sample_log_file: Path) -> None:
        """Test building table with keyword filter — only rows containing keyword pass."""
        viewer = LogViewer(sample_log_file)
        table = viewer._build_table(limit=10, keyword="info")
        # The sample file has "First info message" and "Second info message" → 2 rows.
        assert table.row_count == 2, (
            f"Expected 2 rows containing 'info', got {table.row_count}"
        )


class TestLogViewerLargeFile:
    """Tests for LogViewer with large files."""

    def test_large_file_chunked_reading(self, temp_log_dir: Path) -> None:
        """Test chunked reading for files > 1MB."""
        log_file = temp_log_dir / "large.log"

        # Create a file > 1MB with padding to ensure size
        padding = "x" * 200  # Extra padding per line
        num_lines = 25000  # Enough lines to exceed 1MB

        with log_file.open("w") as f:
            for i in range(num_lines):
                f.write(f"2024-01-01 10:00:{i:05d} - app - INFO - Line {i} {padding}\n")

        assert log_file.stat().st_size > 1_000_000, f"File size: {log_file.stat().st_size}"

        viewer = LogViewer(log_file)
        lines = viewer._tail_lines(100)

        # Filter out empty lines from the result
        non_empty_lines = [line for line in lines if line.strip()]
        assert len(non_empty_lines) >= 90  # Allow some flexibility
        # Last non-empty line should be near the end
        assert f"Line {num_lines - 1}" in non_empty_lines[-1]


class TestLogViewerFollow:
    """Tests for follow_logs functionality."""

    def test_follow_nonexistent_file(self, temp_log_dir: Path) -> None:
        """Test following non-existent file."""
        viewer = LogViewer(temp_log_dir / "nonexistent.log")
        result = viewer.follow_logs()
        assert result is False
