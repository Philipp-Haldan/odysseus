"""Regression: German date phrasings must parse instead of being dropped.

Two separate defects, both silent:

1. `_parse_dt` fell straight through to dateutil, which is English-only and
   month-first. "30. Oktober 2026" raised, and the ambiguous "10.11.2026" was
   read as 11 October instead of 10 November — a wrong date, not an error.

2. `action_ping_notes._parse_due` accepted ISO only and returned None for
   anything else. A reminder whose due_date came from a de-DE agent as
   "30.10.2026" was stored happily and then never fired: the scanner skipped
   it every tick with no log line. `_parse_due` now falls back to `_parse_dt`,
   so the cases below are exactly what decides whether a reminder fires.

Dots are day-first in every locale that uses them, so the dotted branch is
unambiguous and runs before dateutil.
"""
import pytest

from tests.helpers.calendar_routes import import_calendar_routes

# (input, expected (year, month, day, hour, minute))
_GERMAN_DATES = [
    ("30.10.2026", (2026, 10, 30, 0, 0)),
    ("7.11.2026", (2026, 11, 7, 0, 0)),
    ("30.10.2026 14:30", (2026, 10, 30, 14, 30)),
    ("30. Oktober 2026", (2026, 10, 30, 0, 0)),
    ("7. November 2026", (2026, 11, 7, 0, 0)),
    ("1. Maerz 2027", (2027, 3, 1, 0, 0)),
    ("1. März 2027", (2027, 3, 1, 0, 0)),
    ("30. Okt 2026", (2026, 10, 30, 0, 0)),
    ("6. November 2026 14:30", (2026, 11, 6, 14, 30)),
]


@pytest.mark.parametrize("raw,expected", _GERMAN_DATES)
def test_parse_dt_reads_german_dates(raw, expected):
    cal = import_calendar_routes()
    d = cal._parse_dt(raw)
    assert (d.year, d.month, d.day, d.hour, d.minute) == expected
    assert d.tzinfo is None, f"{raw!r} leaked tz-aware: {d!r}"


def test_dotted_date_is_day_first_not_month_first():
    """The case dateutil silently got wrong: both halves are valid months."""
    cal = import_calendar_routes()
    d = cal._parse_dt("10.11.2026")
    assert (d.month, d.day) == (11, 10), "dotted dates must be day-first"


@pytest.mark.parametrize("raw", ["2026-10-30", "2026-10-30T14:00:00"])
def test_iso_still_takes_the_fast_path(raw):
    cal = import_calendar_routes()
    d = cal._parse_dt(raw)
    assert (d.year, d.month, d.day) == (2026, 10, 30)
    assert d.tzinfo is None


@pytest.mark.parametrize("raw", [
    "31.02.2026",            # day out of range for February
    "30. Krautmonat 2026",   # not a month
    "völliger unsinn",
])
def test_unparseable_input_still_raises(raw):
    cal = import_calendar_routes()
    with pytest.raises(ValueError):
        cal._parse_dt(raw)
