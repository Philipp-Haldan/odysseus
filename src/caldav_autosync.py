"""Periodic CalDAV sync — keeps the local calendar fresh without the UI.

Before this loop, a CalDAV pull only happened when somebody opened the
calendar page (`static/js/calendar.js` fires one `/api/calendar/sync` on
first open) or pressed Sync in Settings. An event created on a phone was
therefore invisible to reminders, the agent, the CLI and the check-in
digest until a human opened the tab. In the other direction, a local
event whose push failed stayed flagged `caldav_sync_pending` until the
next manual sync.

This module ticks on its own cadence and calls the same
`sync_caldav_direction(owner, "both")` the route calls: push whatever is
still pending, then pull remote state.

Single small module, mirroring `src/cookbook_serve_lifecycle.py`. Delete
this file plus the registration line in app.py and the feature stops
doing anything — the calendar falls back to syncing on open.

Knobs in `data/settings.json`:
    caldav_auto_sync          bool, default True
    caldav_sync_interval_min  minutes, default 15, clamped to [5, 1440]

Both are re-read every tick, so changing them takes effect after the
current sleep without a restart. `ODYSSEUS_CALDAV_AUTOSYNC=0` disables
the loop regardless of the setting, for deployments that drive syncing
externally (mirrors `ODYSSEUS_INPROCESS_TASKS`).
"""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# Wait before the first tick so startup — and the browser's own first-open
# sync, if the user is already looking at the calendar — settles first.
_STARTUP_DELAY_SECONDS = 45

# Below 5 minutes we would hammer the remote server for nothing: CalDAV has
# no push channel, so freshness is bounded by the interval either way.
_MIN_INTERVAL_MINUTES = 5
_MAX_INTERVAL_MINUTES = 1440

# Mirrors FALLBACK_OWNER in routes/calendar_routes.py. Only used for the
# legacy flat prefs layout (no `_users` key), which is what single-user
# installs with auth disabled write.
_FALLBACK_OWNER = os.environ.get("ODYSSEUS_FALLBACK_OWNER", "owner@localhost")


def _enabled() -> bool:
    if os.environ.get("ODYSSEUS_CALDAV_AUTOSYNC", "1").strip().lower() in {"0", "false", "no", "off"}:
        return False
    try:
        from src.settings import get_setting
        return bool(get_setting("caldav_auto_sync", True))
    except Exception:
        return True


def _interval_seconds() -> int:
    try:
        from src.settings import get_setting
        minutes = int(get_setting("caldav_sync_interval_min", 15) or 15)
    except (TypeError, ValueError, ImportError):
        minutes = 15
    minutes = max(_MIN_INTERVAL_MINUTES, min(minutes, _MAX_INTERVAL_MINUTES))
    return minutes * 60


def _owners() -> list[str]:
    """Owners with at least one CalDAV account configured.

    Read from the prefs store rather than auth.json: an account that was
    never given CalDAV credentials has nothing to sync, and syncing for it
    would just log "CalDAV is not configured" every interval.
    """
    try:
        from routes.prefs_routes import _load
        raw = _load() or {}
    except Exception as e:
        logger.debug("caldav_autosync: prefs unreadable (%s)", e)
        return []

    if "_users" in raw:
        candidates = [name for name in (raw.get("_users") or {}) if name]
    else:
        candidates = [_FALLBACK_OWNER]

    owners = []
    for name in candidates:
        try:
            from src.caldav_sync import _load_caldav_accounts
            if _load_caldav_accounts(name):
                owners.append(name)
        except Exception as e:
            logger.debug("caldav_autosync: account scan failed for %s (%s)", name, e)
    return owners


async def _tick() -> None:
    if not _enabled():
        return
    owners = _owners()
    if not owners:
        return
    from src.caldav_sync import sync_caldav_direction
    for owner in owners:
        try:
            result = await sync_caldav_direction(owner, "both")
        except Exception as e:
            logger.warning("caldav_autosync: sync failed for %s: %s", owner, e)
            continue
        pulled = result.get("pull") or {}
        pushed = result.get("push") or {}
        errors = list(pulled.get("errors") or []) + list(pushed.get("errors") or [])
        if errors:
            logger.warning(
                "caldav_autosync: %s: %s",
                owner,
                "; ".join(str(err)[:160] for err in errors[:3]),
            )
        if pulled.get("events") or pulled.get("deleted") or pushed.get("events"):
            logger.info(
                "caldav_autosync: %s pulled %s event(s), deleted %s, pushed %s",
                owner,
                pulled.get("events", 0),
                pulled.get("deleted", 0),
                pushed.get("events", 0),
            )


async def caldav_autosync_loop() -> None:
    """Forever-loop. Registered as a startup task in app.py.

    Deliberately a plain startup task, not a scheduled task: the
    foreground gate cancels everything the task scheduler is executing as
    soon as the user touches the app (see
    `task_scheduler.stop_background_tasks_for_foreground`), and a calendar
    sync that dies whenever Odysseus is in use is exactly the sync we
    already have.
    """
    await asyncio.sleep(_STARTUP_DELAY_SECONDS)
    while True:
        try:
            await _tick()
        except Exception as e:
            logger.warning("caldav_autosync tick failed: %s", e)
        await asyncio.sleep(_interval_seconds())
