#!/usr/bin/env python3
"""Meta-guard: watches the watchdog.

The group-bot watchdog runs every 10 minutes from Hermes cron. When that cron
job itself breaks — the 2–14 Nov 2026 case: `Script not found`, 1,675 silent
failures — nothing else notices. This guard is the answer:

  1. heartbeat missing or older than BL_HEARTBEAT_STALE_SEC -> alert + run the
     watchdog once (self-heal),
  2. the cron job's last_status is an error -> alert with the real error text,
  3. the cron job hasn't run inside the window -> alert.

Silent and exit 0 when everything is healthy. Alerts go straight to Telegram,
not through the cron delivery path that failed in the first place.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.path.abspath(os.environ.get("BL_BASE", "/opt/data/projects/burger-lab"))
DATA = os.path.join(BASE, "data")
PY = os.environ.get("BL_PY", "/opt/data/venvs/crypto/bin/python")
WATCHDOG = os.environ.get("BL_WATCHDOG", os.path.join(BASE, "scripts", "keepalive_group_bot.py"))
HEARTBEAT = os.path.join(DATA, "watchdog.heartbeat.json")
STATE = os.path.join(DATA, "watchdog.guard.state.json")
JOBS = os.environ.get("BL_JOBS", "/opt/data/cron/jobs.json")
JOB_ID = os.environ.get("BL_JOB_ID", "be37348ec3a3")

STALE = int(os.environ.get("BL_HEARTBEAT_STALE_SEC", "1500"))   # 25 min
JOB_STALE = int(os.environ.get("BL_JOB_STALE_SEC", "1800"))      # 30 min
ALERT_WINDOW = 1800

ALERT_DRY = os.environ.get("BL_ALERT_DRY")
ALERT_CHAT = os.environ.get("BL_ALERT_CHAT", "427257056")
ALERT_PREFIX = os.environ.get("BL_ALERT_PREFIX", "")   # drills/tests only
ENV_FILE = os.environ.get("BL_ENV_FILE", "/opt/data/.env")

IST = timezone(timedelta(hours=5, minutes=30))


def now_ist():
    return datetime.now(IST)


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        try:
            with open(ENV_FILE) as f:
                for line in f:
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        token = line.split("=", 1)[1].strip()
                        break
        except OSError:
            token = ""
    if not token:
        return False
    payload = json.dumps({"chat_id": ALERT_CHAT, "text": ALERT_PREFIX + text,
                          "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(
        "https://api.telegram.org/bot%s/sendMessage" % token,
        data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except (urllib.error.URLError, OSError):
        return False


def alert(state, key, text):
    sent = state.setdefault("alerts", {})
    if time.time() - sent.get(key, 0) < ALERT_WINDOW:
        return False
    if ALERT_DRY:
        with open(ALERT_DRY, "a") as f:
            f.write(text + "\n---\n")
        ok = True
    else:
        ok = telegram(text)
    if ok:
        sent[key] = time.time()
    return ok


def job_entry():
    jobs = load_json(JOBS, [])
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs", [])
    if isinstance(jobs, dict):
        jobs = list(jobs.values())
    for j in jobs or []:
        if isinstance(j, dict) and j.get("id") == JOB_ID:
            return j
    return None


def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def run_watchdog():
    try:
        res = subprocess.run([PY, WATCHDOG], capture_output=True, text=True, timeout=180)
        return res.returncode, (res.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 99, "watchdog failed to run: %s" % e


def main():
    state = load_json(STATE, {})
    actions = []

    hb = load_json(HEARTBEAT, {})
    hb_ts = float(hb.get("ts") or 0)
    hb_age = time.time() - hb_ts if hb_ts else None

    if hb_age is None or hb_age > STALE:
        age_txt = "never" if hb_age is None else "%d min" % (hb_age / 60)
        age_phrase = "at all — no heartbeat file yet" if hb_age is None else "for " + age_txt
        actions.append("watchdog heartbeat stale (%s) — running it now" % age_txt)
        rc, out = run_watchdog()
        if out:
            actions.append(out)
        hb = load_json(HEARTBEAT, {})
        new_age = time.time() - float(hb.get("ts") or 0)
        revived = bool(hb.get("ts")) and new_age < STALE
        if revived:
            actions.append("watchdog revived")
            alert(state, "watchdog_stale",
                  "🟠 Burger Lab: group-bot watchdog hasn't run %s (%s IST) — the guard ran "
                  "it and it is healthy again." % (age_phrase, now_ist().strftime("%d %b %H:%M")))
        else:
            alert(state, "watchdog_dead",
                  "🔴 Burger Lab: the group-bot watchdog hasn't run %s and did not revive "
                  "(rc=%s, %s IST). Cron job %s may be failing — check `cronjob list`."
                  % (age_phrase, rc, now_ist().strftime("%d %b %H:%M"), JOB_ID))

    job = job_entry()
    if job is None:
        alert(state, "cron_missing",
              "🔴 Burger Lab: cron job %s is gone from jobs.json — nothing is watching the "
              "WhatsApp poster." % JOB_ID)
    else:
        status = (job.get("last_status") or "").lower()
        streak = job.get("failure_streak")
        # A single error that the next tick clears is noise, not an outage: page
        # only when the job has failed at least twice in a row.
        repeated = not isinstance(streak, int) or streak >= 2
        if status not in ("", "ok", "success", "silent", "running") and repeated:
            alert(state, "cron_error",
                  "🔴 Burger Lab: watchdog cron job %s is failing (%s IST).\n%s"
                  % (JOB_ID, now_ist().strftime("%d %b %H:%M"), job.get("last_error") or status))
            actions.append("cron job %s last_status=%s" % (JOB_ID, status))
        else:
            # Healthy again: clear the dedupe keys so the next real outage pages at once.
            state.get("alerts", {}).pop("cron_error", None)
            state.get("alerts", {}).pop("cron_stale", None)
        last = parse_ts(job.get("last_run_at"))
        if last and time.time() - last > JOB_STALE:
            mins = int((time.time() - last) / 60)
            alert(state, "cron_stale",
                  "🟠 Burger Lab: watchdog cron job %s hasn't run for %d min — scheduler is "
                  "still monitored? (%s IST)" % (JOB_ID, mins, now_ist().strftime("%d %b %H:%M")))
            actions.append("cron job hasn't run for %d min" % mins)

    save_json(STATE, state)
    if actions:
        print("⚠️ Burger Lab watchdog guard: " + "; ".join(actions))
    return 0


if __name__ == "__main__":
    sys.exit(main())
