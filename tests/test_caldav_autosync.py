"""Coverage for the periodic CalDAV sync loop (src/caldav_autosync.py).

No live CalDAV server and no event loop sleeping: the tests drive `_tick`
directly and stub the sync entry point, so what's pinned is the loop's
own contract — who it syncs for, in which direction, and when it stays
quiet.
"""

import sys
import types

import src.caldav_autosync as autosync


def _stub_prefs(monkeypatch, raw):
    prefs_mod = types.ModuleType("routes.prefs_routes")
    prefs_mod._load = lambda: raw
    prefs_mod._load_for_user = lambda user=None: (raw.get("_users") or {}).get(user, {})
    monkeypatch.setitem(sys.modules, "routes.prefs_routes", prefs_mod)


def _stub_sync(monkeypatch, calls, accounts_for=lambda owner: [{"id": "a"}]):
    sync_mod = types.ModuleType("src.caldav_sync")
    sync_mod._load_caldav_accounts = accounts_for

    async def fake_sync(owner, direction="pull"):
        calls.append((owner, direction))
        return {"pull": {"events": 0, "deleted": 0, "errors": []},
                "push": {"events": 0, "errors": []}}

    sync_mod.sync_caldav_direction = fake_sync
    monkeypatch.setitem(sys.modules, "src.caldav_sync", sync_mod)


def test_owners_skips_users_without_caldav_credentials(monkeypatch):
    _stub_prefs(monkeypatch, {"_users": {"admin": {}, "guest": {}}})
    _stub_sync(
        monkeypatch,
        [],
        accounts_for=lambda owner: [{"id": "a"}] if owner == "admin" else [],
    )

    assert autosync._owners() == ["admin"]


def test_owners_falls_back_to_single_user_owner_on_legacy_prefs(monkeypatch):
    # Legacy flat prefs (auth disabled) have no `_users` key; calendar rows
    # are owned by FALLBACK_OWNER in that mode.
    _stub_prefs(monkeypatch, {"caldav_accounts": [{"id": "a"}]})
    _stub_sync(monkeypatch, [])

    assert autosync._owners() == [autosync._FALLBACK_OWNER]


async def test_tick_syncs_both_directions_for_each_configured_owner(monkeypatch):
    calls = []
    _stub_sync(monkeypatch, calls)
    monkeypatch.setattr(autosync, "_owners", lambda: ["admin", "other"])
    monkeypatch.setattr(autosync, "_enabled", lambda: True)

    await autosync._tick()

    # "both" pushes events whose earlier writeback failed before pulling,
    # so a stuck caldav_sync_pending row recovers on its own.
    assert calls == [("admin", "both"), ("other", "both")]


async def test_tick_does_nothing_when_disabled(monkeypatch):
    calls = []
    _stub_sync(monkeypatch, calls)
    monkeypatch.setattr(autosync, "_owners", lambda: ["admin"])
    monkeypatch.setattr(autosync, "_enabled", lambda: False)

    await autosync._tick()

    assert calls == []


async def test_tick_survives_one_owner_failing(monkeypatch):
    calls = []
    sync_mod = types.ModuleType("src.caldav_sync")

    async def fake_sync(owner, direction="pull"):
        calls.append(owner)
        if owner == "admin":
            raise RuntimeError("server unreachable")
        return {"pull": {"events": 1, "deleted": 0, "errors": []}, "push": {"events": 0, "errors": []}}

    sync_mod.sync_caldav_direction = fake_sync
    monkeypatch.setitem(sys.modules, "src.caldav_sync", sync_mod)
    monkeypatch.setattr(autosync, "_owners", lambda: ["admin", "other"])
    monkeypatch.setattr(autosync, "_enabled", lambda: True)

    await autosync._tick()

    assert calls == ["admin", "other"]


def test_env_override_disables_loop(monkeypatch):
    monkeypatch.setenv("ODYSSEUS_CALDAV_AUTOSYNC", "0")
    assert autosync._enabled() is False


def test_interval_is_clamped(monkeypatch):
    settings_mod = types.ModuleType("src.settings")
    values = {"caldav_sync_interval_min": 1}
    settings_mod.get_setting = lambda key, default=None: values.get(key, default)
    monkeypatch.setitem(sys.modules, "src.settings", settings_mod)

    assert autosync._interval_seconds() == autosync._MIN_INTERVAL_MINUTES * 60

    values["caldav_sync_interval_min"] = 99999
    assert autosync._interval_seconds() == autosync._MAX_INTERVAL_MINUTES * 60

    values["caldav_sync_interval_min"] = 30
    assert autosync._interval_seconds() == 1800


def test_app_registers_the_loop_as_a_startup_task():
    from pathlib import Path
    source = Path("app.py").read_text(encoding="utf-8")

    assert "from src.caldav_autosync import caldav_autosync_loop" in source
    assert "asyncio.create_task(caldav_autosync_loop())" in source
