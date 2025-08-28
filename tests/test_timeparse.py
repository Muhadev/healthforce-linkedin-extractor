# tests/test_timeparse.py
"""Tests for time parsing utilities."""

from datetime import datetime, timedelta, timezone

from li_extractor.timeparse import TimeParser


class TestTimeParser:
    """Test cases for TimeParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = TimeParser()
        self.reference_time = datetime(2025, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

    def test_just_now(self):
        """Test 'just now' parsing."""
        result = self.parser.parse_relative_time("just now", self.reference_time)
        assert result == self.reference_time

        result = self.parser.parse_relative_time("Just Now", self.reference_time)
        assert result == self.reference_time

    def test_seconds_ago(self):
        """Test seconds parsing."""
        test_cases = [
            ("30s", 30),
            ("45 seconds", 45),
            ("5 sec", 5),
            ("1s ago", 1),
        ]

        for time_str, expected_seconds in test_cases:
            result = self.parser.parse_relative_time(time_str, self.reference_time)
            expected = self.reference_time - timedelta(seconds=expected_seconds)
            assert result == expected, f"Failed for '{time_str}'"

    def test_minutes_ago(self):
        """Test minutes parsing."""
        test_cases = [
            ("5m", 5),
            ("30 minutes", 30),
            ("1 min", 1),
            ("45m ago", 45),
        ]

        for time_str, expected_minutes in test_cases:
            result = self.parser.parse_relative_time(time_str, self.reference_time)
            expected = self.reference_time - timedelta(minutes=expected_minutes)
            assert result == expected, f"Failed for '{time_str}'"

    def test_hours_ago(self):
        """Test hours parsing."""
        test_cases = [
            ("2h", 2),
            ("12 hours", 12),
            ("1 hour", 1),
            ("6h ago", 6),
        ]

        for time_str, expected_hours in test_cases:
            result = self.parser.parse_relative_time(time_str, self.reference_time)
            expected = self.reference_time - timedelta(hours=expected_hours)
            assert result == expected, f"Failed for '{time_str}'"

    def test_days_ago(self):
        """Test days parsing."""
        test_cases = [
            ("1d", 1),
            ("7 days", 7),
            ("2 days ago", 2),
            ("14d ago", 14),
        ]

        for time_str, expected_days in test_cases:
            result = self.parser.parse_relative_time(time_str, self.reference_time)
            expected = self.reference_time - timedelta(days=expected_days)
            assert result == expected, f"Failed for '{time_str}'"

    def test_weeks_ago(self):
        """Test weeks parsing."""
        test_cases = [
            ("1w", 1),
            ("3 weeks", 3),
            ("2 weeks ago", 2),
        ]

        for time_str, expected_weeks in test_cases:
            result = self.parser.parse_relative_time(time_str, self.reference_time)
            expected = self.reference_time - timedelta(weeks=expected_weeks)
            assert result == expected, f"Failed for '{time_str}'"

    def test_months_ago(self):
        """Test months parsing (approximate)."""
        test_cases = [
            ("1mo", 1),
            ("3 months", 3),
            ("6mo ago", 6),
        ]

        for time_str, expected_months in test_cases:
            result = self.parser.parse_relative_time(time_str, self.reference_time)
            expected = self.reference_time - timedelta(days=expected_months * 30)
            assert result == expected, f"Failed for '{time_str}'"

    def test_years_ago(self):
        """Test years parsing (approximate)."""
        test_cases = [
            ("1y", 1),
            ("2 years", 2),
            ("3y ago", 3),
        ]

        for time_str, expected_years in test_cases:
            result = self.parser.parse_relative_time(time_str, self.reference_time)
            expected = self.reference_time - timedelta(days=expected_years * 365)
            assert result == expected, f"Failed for '{time_str}'"

    def test_absolute_datetime(self):
        """Test absolute datetime parsing."""
        test_cases = [
            "2025-08-27T10:30:00Z",
            "2025-08-27 10:30:00",
            "Aug 27, 2025",
        ]

        for time_str in test_cases:
            result = self.parser.parse_relative_time(time_str, self.reference_time)
            assert result is not None, f"Failed to parse '{time_str}'"
            assert isinstance(result, datetime)

    def test_invalid_input(self):
        """Test invalid input handling."""
        invalid_cases = [
            "",
            None,
            "invalid",
            "xyz ago",
            "not a time",
        ]

        for time_str in invalid_cases:
            result = self.parser.parse_relative_time(time_str, self.reference_time)
            assert result is None, f"Should return None for '{time_str}'"

    def test_timezone_handling(self):
        """Test timezone handling."""
        # Test with naive reference time
        naive_ref = datetime(2025, 8, 27, 12, 0, 0)
        result = self.parser.parse_relative_time("1h", naive_ref)

        assert result is not None
        assert result.tzinfo == timezone.utc

        # Test with different timezone reference
        import pytz

        est = pytz.timezone("US/Eastern")
        est_ref = datetime(2025, 8, 27, 8, 0, 0, tzinfo=est)
        result = self.parser.parse_relative_time("2h", est_ref)

        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result is not None
        assert result.tzinfo == timezone.utc
