"""FHIR date/datetime parsing utilities.

FHIR dates can have varying precision (year, year-month, full date, datetime).
For search indexing, each date is expanded to a range [low, high] that covers
the entire precision window.
"""

from datetime import datetime, timezone, timedelta
import re

# Patterns for FHIR date precisions
_YEAR = re.compile(r"^(\d{4})$")
_YEAR_MONTH = re.compile(r"^(\d{4})-(\d{2})$")
_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DATETIME = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})"
    r"(?::(\d{2})(?:\.(\d+))?)?"
    r"(Z|[+-]\d{2}:\d{2})?$"
)


def parse_fhir_date_to_range(value):
    """Parse a FHIR date/dateTime string into a (low, high) datetime range.

    Returns (datetime, datetime) tuple in UTC, or (None, None) if unparseable.
    """
    if not value:
        return None, None

    value = value.strip()

    m = _YEAR.match(value)
    if m:
        year = int(m.group(1))
        low = datetime(year, 1, 1, tzinfo=timezone.utc)
        high = datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return low, high

    m = _YEAR_MONTH.match(value)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        low = datetime(year, month, 1, tzinfo=timezone.utc)
        # Last day of month
        if month == 12:
            high = datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=timezone.utc)
        else:
            high = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(microseconds=1)
        return low, high

    m = _DATE.match(value)
    if m:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        low = datetime(year, month, day, tzinfo=timezone.utc)
        high = datetime(year, month, day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return low, high

    m = _DATETIME.match(value)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        hour = int(m.group(4))
        minute = int(m.group(5))
        second = int(m.group(6)) if m.group(6) else 0
        micro = 0
        if m.group(7):
            frac = m.group(7)[:6].ljust(6, "0")
            micro = int(frac)

        tz_str = m.group(8)
        if tz_str and tz_str != "Z":
            sign = 1 if tz_str[0] == "+" else -1
            tz_parts = tz_str[1:].split(":")
            tz_offset = timedelta(
                hours=sign * int(tz_parts[0]),
                minutes=sign * int(tz_parts[1]),
            )
            tz = timezone(tz_offset)
        else:
            tz = timezone.utc

        dt = datetime(year, month, day, hour, minute, second, micro, tzinfo=tz)
        # Convert to UTC
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc, dt_utc

    return None, None


def parse_fhir_date(value):
    """Parse a FHIR date/dateTime to a single UTC datetime (the low bound)."""
    low, _ = parse_fhir_date_to_range(value)
    return low
