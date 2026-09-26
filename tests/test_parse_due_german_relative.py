"""Regression: German relative due dates must parse instead of being stored raw.

A de-DE agent wrote reminders with due_date "heute 19:00". Both parsers only
knew English keywords, so the value raised, manage_notes stored the literal
string, and the note never fired and never appeared in "Mein Tag" or
"Meine Woche" (the frontend's `new Date("heute 19:00")` is Invalid Date).
"""
from datetime import datetime, timezone

import pytest

import routes.calendar_routes as calendar_routes
from src.user_time import clear_user_time_context, set_user_tz_name, set_user_tz_offset


class _FixedNow(datetime):
    """Freeze server clock at 2026-06-07T10:00:00 UTC for deterministic tests."""
    @classmethod
    def now(cls, tz=None):
        value = datetime(2026, 6, 7, 10, 0, 0, tzinfo=timezone.utc)
        if tz is not None:
            return value.astimezone(tz)
        return value.replace(tzinfo=None)


def setup_function():
    clear_user_time_context()
    set_user_tz_offset(0)
    set_user_tz_name("UTC")


def teardown_function():
    clear_user_time_context()


@pytest.mark.parametrize("raw,expected", [
    ("heute 19:00", "2026-06-07T19:00:00"),
    ("heute um 20:30", "2026-06-07T20:30:00"),
    ("heute 19 Uhr", "2026-06-07T19:00:00"),
    ("heute abend 21:00", "2026-06-07T21:00:00"),
    ("morgen 9:00", "2026-06-08T09:00:00"),
    ("morgen um 9 Uhr", "2026-06-08T09:00:00"),
    ("morgen früh 8:00", "2026-06-08T08:00:00"),
    ("19:00 heute", "2026-06-07T19:00:00"),
    ("gestern 18:00", "2026-06-06T18:00:00"),
    ("morgen", "2026-06-08T00:00:00"),
])
def test_parse_due_for_user_reads_german_relative(monkeypatch, raw, expected):
    monkeypatch.setattr(calendar_routes, "datetime", _FixedNow)
    assert calendar_routes.parse_due_for_user(raw).startswith(expected)


@pytest.mark.parametrize("raw,expected", [
    ("heute 19:00", (2026, 6, 7, 19, 0)),
    ("morgen um 9 Uhr", (2026, 6, 8, 9, 0)),
])
def test_parse_dt_reads_german_relative(monkeypatch, raw, expected):
    monkeypatch.setattr(calendar_routes, "datetime", _FixedNow)
    d = calendar_routes._parse_dt(raw)
    assert (d.year, d.month, d.day, d.hour, d.minute) == expected


def test_english_phrasing_unchanged(monkeypatch):
    monkeypatch.setattr(calendar_routes, "datetime", _FixedNow)
    assert calendar_routes.parse_due_for_user("tomorrow at 9am").startswith("2026-06-08T09:00:00")
