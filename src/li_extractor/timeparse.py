# src/li_extractor/timeparse.py
"""Time parsing utilities for LinkedIn relative timestamps."""

import re
from datetime import datetime, timedelta, timezone

from dateutil import parser as date_parser


class TimeParser:
    """Parse LinkedIn relative timestamps to ISO-8601 UTC."""

    # Regex patterns for relative time parsing
    # FIXED: Made patterns more specific to avoid conflicts
    PATTERNS = {
        "just_now": re.compile(r"just now", re.IGNORECASE),
        # More specific patterns to avoid conflicts
        "months": re.compile(
            r"(\d+)\s*mo(?:nth)?s?(?:\s+ago)?(?![a-z])", re.IGNORECASE
        ),  # Must not be followed by letters
        "minutes": re.compile(
            r"(\d+)\s*m(?:in(?:ute)?s?)?(?:\s+ago)?(?![a-z])", re.IGNORECASE
        ),  # Must not be followed by letters
        "seconds": re.compile(
            r"(\d+)\s*s(?:ec(?:ond)?s?)?(?:\s+ago)?(?![a-z])", re.IGNORECASE
        ),
        "hours": re.compile(r"(\d+)\s*h(?:our)?s?(?:\s+ago)?(?![a-z])", re.IGNORECASE),
        "days": re.compile(r"(\d+)\s*d(?:ay)?s?(?:\s+ago)?(?![a-z])", re.IGNORECASE),
        "weeks": re.compile(r"(\d+)\s*w(?:eek)?s?(?:\s+ago)?(?![a-z])", re.IGNORECASE),
        "years": re.compile(r"(\d+)\s*y(?:ear)?s?(?:\s+ago)?(?![a-z])", re.IGNORECASE),
        "days_word": re.compile(r"(\d+)\s+days?\s+ago", re.IGNORECASE),
        "weeks_word": re.compile(r"(\d+)\s+weeks?\s+ago", re.IGNORECASE),
    }

    def parse_relative_time(
        self, time_str: str, reference_time: datetime | None = None
    ) -> datetime | None:
        """Parse relative time string to UTC datetime."""
        if not time_str:
            return None

        # Use provided reference_time or current UTC time
        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        # Ensure reference time is in UTC
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
        elif reference_time.tzinfo != timezone.utc:
            reference_time = reference_time.astimezone(timezone.utc)

        time_str = time_str.strip()

        # Parse relative times FIRST, before trying absolute parsing
        # This prevents dateutil from incorrectly parsing "30s" as absolute time

        # Parse relative times - ALL of these represent times in the PAST
        if self.PATTERNS["just_now"].search(time_str):
            return reference_time

        # CRITICAL FIX: Check months BEFORE minutes to avoid "1mo" matching "1m"
        # Months ago (approximate as 30 days)
        match = self.PATTERNS["months"].search(time_str)
        if match:
            months = int(match.group(1))
            return reference_time - timedelta(days=months * 30)

        # Years ago (approximate as 365 days)
        match = self.PATTERNS["years"].search(time_str)
        if match:
            years = int(match.group(1))
            return reference_time - timedelta(days=years * 365)

        # Weeks ago
        match = self.PATTERNS["weeks"].search(time_str) or self.PATTERNS[
            "weeks_word"
        ].search(time_str)
        if match:
            weeks = int(match.group(1))
            return reference_time - timedelta(weeks=weeks)

        # Days ago
        match = self.PATTERNS["days"].search(time_str) or self.PATTERNS[
            "days_word"
        ].search(time_str)
        if match:
            days = int(match.group(1))
            return reference_time - timedelta(days=days)

        # Hours ago
        match = self.PATTERNS["hours"].search(time_str)
        if match:
            hours = int(match.group(1))
            return reference_time - timedelta(hours=hours)

        # Minutes ago (check AFTER months to avoid conflict)
        match = self.PATTERNS["minutes"].search(time_str)
        if match:
            minutes = int(match.group(1))
            return reference_time - timedelta(minutes=minutes)

        # Seconds ago
        match = self.PATTERNS["seconds"].search(time_str)
        if match:
            seconds = int(match.group(1))
            return reference_time - timedelta(seconds=seconds)

        # ONLY try absolute datetime parsing if no relative patterns matched
        # This prevents dateutil from misinterpreting relative time strings
        try:
            parsed = date_parser.parse(time_str)
            # Convert to UTC if timezone aware, otherwise assume UTC
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass

        # If nothing matches, return None
        return None
