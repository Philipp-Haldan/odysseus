#!/usr/bin/env python3
"""check-wochenbericht — did the weekly research task actually deliver?

Read-only. Talks to the SQLite DB directly and never to the HTTP API,
because loading any Odysseus page is itself foreground activity and would
cancel the very run you are checking (app.py `_InteractiveActivityMiddleware`).

    python scripts/check-wochenbericht.py [TASK_ID] [--weeks N]

Verdict per scheduled slot:
    OK        status=success and a non-empty result  -> the mail went out
    ABGEBROCHEN  the foreground gate killed it       -> nothing was delivered
    FEHLER    the run itself or SMTP failed
    FEHLT     no run row at all for that slot        -> PC off, or the
              dispatcher silently deferred it (task_scheduler.py:711)
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("ODYSSEUS_DB", REPO_ROOT / "data" / "app.db"))
DEFAULT_TASK = os.environ.get("ODYSSEUS_TASK_ID", "")
# Below this the "report" is a DeepResearcher placeholder, not content.
MIN_USEFUL_CHARS = 500


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id", nargs="?", default=DEFAULT_TASK,
                    help="task id, or set ODYSSEUS_TASK_ID; "
                         "`odysseus-tasks list` prints them")
    ap.add_argument("--weeks", type=int, default=2)
    args = ap.parse_args()
    if not args.task_id:
        sys.stderr.write(
            "error: no task id given.\n"
            "hint: python scripts/odysseus-tasks list  -> pick the id\n")
        return 2

    if not DB_PATH.exists():
        sys.stderr.write(f"error: no database at {DB_PATH}\n")
        return 2

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    row = con.execute(
        "select name, schedule, scheduled_time, scheduled_day, output_target,"
        "       status, run_count, last_run, next_run"
        "  from scheduled_tasks where id = ?",
        (args.task_id,),
    ).fetchone()
    if not row:
        sys.stderr.write(f"error: no task {args.task_id}\n")
        return 2
    name, sched, at, day, target, status, run_count, last_run, next_run = row

    print(f"Auftrag   : {name}")
    print(f"Plan      : {sched} Tag={day} {at} UTC  (= {_local_hint(at)})")
    print(f"Ziel      : {target}")
    print(f"Status    : {status}")
    print(f"Zugestellt: {run_count}   (run_count zaehlt NUR ausgelieferte Laeufe)")
    print(f"Zuletzt   : {last_run or '-'}")
    print(f"Naechster : {next_run or '-'}")
    print()

    now_utc = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    since = (now_utc - dt.timedelta(weeks=args.weeks)).isoformat()
    runs = con.execute(
        "select started_at, finished_at, status, coalesce(error,''),"
        "       length(coalesce(result,''))"
        "  from task_runs where task_id = ? and started_at > ?"
        " order by started_at desc",
        (args.task_id, since),
    ).fetchall()

    if not runs:
        print(f"Keine Laeufe in den letzten {args.weeks} Wochen -> FEHLT")
        return 1

    ok = 0
    print(f"{'Start (UTC)':20} {'Dauer':>8}  {'Urteil':12} Detail")
    print("-" * 78)
    for started, finished, st, err, chars in runs:
        dur = "?"
        if finished:
            try:
                dur = f"{(dt.datetime.fromisoformat(finished) - dt.datetime.fromisoformat(started)).total_seconds():.0f}s"
            except ValueError:
                pass
        if st in ("running", "queued"):
            verdict, detail = "LAEUFT", f"seit {started[:19]} UTC, {chars} Zeichen bisher"
        elif st == "success" and chars < MIN_USEFUL_CHARS:
            # DeepResearcher returns a one-line "No information could be
            # gathered" string when query generation produces nothing. The run
            # is marked success and the mail goes out, so only the length
            # betrays that the report is empty.
            verdict, detail = "LEER", f"nur {chars} Zeichen — Bericht ohne Inhalt"
        elif st == "success":
            verdict, detail = "OK", f"{chars} Zeichen zugestellt"
            ok += 1
        elif st == "aborted":
            # The run row says "Stopped by user" even when the foreground gate
            # did it — stop_background_tasks_for_foreground passes its `reason`
            # only to the logger, not to _mark_run_aborted.
            verdict, detail = "ABGEBROCHEN", f"{err} (meist der Vordergrund-Gate, nicht du)"
        else:
            verdict, detail = "FEHLER", err or f"status={st}"
        print(f"{started[:19]:20} {dur:>8}  {verdict:12} {detail}")

    print()
    pending = sum(1 for r in runs if r[2] in ("running", "queued"))
    tail = f" ({pending} laeuft gerade)" if pending else ""
    print(f"Ergebnis: {ok} von {len(runs)} Laeufen zugestellt.{tail}")
    return 0 if ok else 1


def _local_hint(at: str) -> str:
    try:
        h, m = (int(x) for x in at.split(":"))
    except (ValueError, AttributeError):
        return "?"
    return (f"{(h + 2) % 24:02d}:{m:02d} Sommerzeit / "
            f"{(h + 1) % 24:02d}:{m:02d} Winterzeit deutscher Zeit")


if __name__ == "__main__":
    sys.exit(main())
