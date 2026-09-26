"""The urgent-email push can be switched off without losing the triage.

The reminder channel (ntfy, browser, email) is shared with calendar and todo
reminders. Users who route that channel to their phone may want it reserved
for those, while still getting the inbox urgency dots. `urgent_email_push`
gates only the dispatch; upstream behaviour (push on) stays the default.
"""
import inspect

from src.settings import DEFAULT_SETTINGS


def test_push_defaults_on():
    assert DEFAULT_SETTINGS["urgent_email_push"] is True


def test_dispatch_is_gated_by_setting():
    from src.builtin_actions import action_check_email_urgency

    src = inspect.getsource(action_check_email_urgency)
    gate = src.index('settings.get("urgent_email_push", True)')
    dispatch = src.index("dispatch_reminder(")
    tagging = src.index("INSERT INTO email_tags")
    # Tagging runs before the gate; the push itself sits behind it.
    assert tagging < gate < dispatch
