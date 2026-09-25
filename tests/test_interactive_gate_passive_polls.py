"""An idle-but-open browser tab must not count as foreground activity.

The tab polls three endpoints on a 60s timer. Any one of them being tracked
turns a quiet tab into a foreground-activity heartbeat, which cancels running
background jobs (app.py `_InteractiveActivityMiddleware`). A scheduled
research task runs up to 600s, so a single tracked 60s poll makes it
impossible to ever finish.
"""

from src.interactive_gate import should_track_interactive_request


IDLE_TAB_POLLS = [
    "/api/research/active",
    "/api/email/urgency-state",
    "/api/email/unread-state",
]


def test_idle_tab_polls_are_not_foreground_activity():
    for path in IDLE_TAB_POLLS:
        assert not should_track_interactive_request(path, "GET"), (
            f"{path} is polled by an idle tab; tracking it cancels background tasks"
        )


def test_real_user_requests_are_still_tracked():
    assert should_track_interactive_request("/api/chat/send", "POST")
    assert should_track_interactive_request("/api/email/send", "POST")
