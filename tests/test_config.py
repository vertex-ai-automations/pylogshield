"""Tests for sensitive field configuration."""

from __future__ import annotations

import re
import threading


from pylogshield.config import (
    add_sensitive_fields,
    get_sensitive_fields,
    get_sensitive_pattern,
    remove_sensitive_fields,
)


class TestSensitiveFields:
    """Tests for sensitive field registry."""

    def test_default_fields_exist(self) -> None:
        """Test that default sensitive fields are present."""
        fields = get_sensitive_fields()
        assert "password" in fields
        assert "token" in fields
        assert "api_key" in fields
        assert "secret" in fields

    def test_add_sensitive_fields(self) -> None:
        """Test adding new sensitive fields."""
        add_sensitive_fields(["custom_field", "another_field"])
        fields = get_sensitive_fields()
        assert "custom_field" in fields
        assert "another_field" in fields

    def test_add_sensitive_fields_normalized(self) -> None:
        """Test that added fields are normalized to lowercase."""
        add_sensitive_fields(["UPPER_CASE", "  spaces  "])
        fields = get_sensitive_fields()
        assert "upper_case" in fields
        assert "spaces" in fields

    def test_add_empty_fields_ignored(self) -> None:
        """Test that empty fields are ignored."""
        initial_count = len(get_sensitive_fields())
        add_sensitive_fields(["", "   ", None])  # type: ignore
        assert len(get_sensitive_fields()) == initial_count

    def test_remove_sensitive_fields(self) -> None:
        """Test removing sensitive fields."""
        add_sensitive_fields(["temp_field"])
        assert "temp_field" in get_sensitive_fields()

        remove_sensitive_fields(["temp_field"])
        assert "temp_field" not in get_sensitive_fields()

    def test_remove_nonexistent_field(self) -> None:
        """Test removing non-existent field doesn't raise."""
        remove_sensitive_fields(["nonexistent_field_xyz"])
        # Should not raise

    def test_get_sensitive_fields_immutable(self) -> None:
        """Test that returned fields set is immutable."""
        fields = get_sensitive_fields()
        assert isinstance(fields, frozenset)


class TestSensitivePattern:
    """Tests for sensitive pattern regex."""

    def test_pattern_matches_password(self) -> None:
        """Test pattern matches password field."""
        pattern = get_sensitive_pattern()
        text = "password: secret123"
        match = pattern.search(text)
        assert match is not None
        assert match.group(1).lower() == "password"

    def test_pattern_matches_token(self) -> None:
        """Test pattern matches token field."""
        pattern = get_sensitive_pattern()
        text = "token=abc123xyz"
        match = pattern.search(text)
        assert match is not None
        assert match.group(1).lower() == "token"

    def test_pattern_matches_quoted_value(self) -> None:
        """Test pattern matches quoted values."""
        pattern = get_sensitive_pattern()
        text = 'api_key: "mykey123"'
        match = pattern.search(text)
        assert match is not None

    def test_pattern_case_insensitive(self) -> None:
        """Test pattern is case-insensitive."""
        pattern = get_sensitive_pattern()

        assert pattern.search("PASSWORD: secret") is not None
        assert pattern.search("Password: secret") is not None
        assert pattern.search("password: secret") is not None

    def test_pattern_cached(self) -> None:
        """Test that pattern is cached."""
        pattern1 = get_sensitive_pattern()
        pattern2 = get_sensitive_pattern()
        assert pattern1 is pattern2

    def test_pattern_invalidated_on_add(self) -> None:
        """Test pattern cache is invalidated when fields are added."""
        pattern1 = get_sensitive_pattern()
        add_sensitive_fields(["new_test_field"])
        pattern2 = get_sensitive_pattern()
        # Pattern should be recompiled
        assert pattern1 is not pattern2

    def test_pattern_invalidated_on_remove(self) -> None:
        """Test pattern cache is invalidated when fields are removed."""
        add_sensitive_fields(["removable_field"])
        pattern1 = get_sensitive_pattern()
        remove_sensitive_fields(["removable_field"])
        pattern2 = get_sensitive_pattern()
        assert pattern1 is not pattern2


class TestThreadSafety:
    """Tests for thread safety of sensitive field operations."""

    def test_concurrent_add_fields(self) -> None:
        """Test concurrent field additions."""
        errors: list = []

        def add_fields(prefix: str) -> None:
            try:
                for i in range(10):
                    add_sensitive_fields([f"{prefix}_field_{i}"])
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_fields, args=(f"thread_{i}",)) for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_concurrent_pattern_access(self) -> None:
        """Test concurrent pattern access."""
        errors: list = []
        patterns: list = []

        def get_pattern() -> None:
            try:
                for _ in range(10):
                    p = get_sensitive_pattern()
                    patterns.append(p)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=get_pattern) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All patterns should be valid regex
        for p in patterns:
            assert isinstance(p, re.Pattern)

    def test_concurrent_add_and_invalidate(self) -> None:
        """Concurrent add + pattern access must not corrupt the cache or raise."""
        import re as _re

        errors: list = []

        def add_and_read(prefix: str) -> None:
            try:
                for i in range(20):
                    add_sensitive_fields([f"{prefix}_inv_{i}"])
                    p = get_sensitive_pattern()
                    assert isinstance(p, _re.Pattern)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=add_and_read, args=(f"t{i}",)) for i in range(6)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors in concurrent add+invalidate: {errors}"
        # Pattern must still be a valid, usable regex after all the churn
        final_pattern = get_sensitive_pattern()
        assert isinstance(final_pattern, _re.Pattern)
        assert final_pattern.search("password: secret") is not None
