#!/usr/bin/env python3
"""Watchdog for The Burger Lab WhatsApp group poster.

Self-heals the WhatsApp sender (:8631) and the group scheduler, verifies every
heal, and alerts Telegram when it cannot fix things. Writes a heartbeat that
the meta-guard job (burgerlab_watchdog_guard.py) reads, so a watchdog that
never runs is itself detected.

Scheduler identity comes from the process's own lock file plus /proc (cmdline
AND cwd) — never a bare `pgrep -f "group_scheduler.py run"`, which used to
match Food Court's scheduler and report a dead Burger Lab scheduler as alive.

Silent and exit 0 when healthy. Prints one line per action otherwise.
Exit 1 when something is still broken after healing — cron delivers stdout.
"""
import fcntl
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
SENDER_URL = os.environ.get("BL_SENDER_URL", "http://127.0.0.1:8631")
BOT_START = os.environ.get("BL_BOT_START", os.path.join(BASE, "scripts", "start_group_bot.sh"))
SCHED_SCRIPT = os.path.join(BASE, "scripts", "group_scheduler.py")
LOCK = os.path.join(DATA, "group_scheduler.lock")
LOG = os.path.join(DATA, "group_scheduler.out")
HEARTBEAT = os.path.join(DATA, "watchdog.heartbeat.json")
STATE = os.path.join(DATA, "watchdog.state.json")

ALERT_DRY = os.environ.get("BL_ALERT_DRY")          # write alerts here instead of Telegram
ALERT_CHAT = os.environ.get("BL_ALERT_CHAT", "427257056")
ALERT_PREFIX = os.environ.get("BL_ALERT_PREFIX", "")   # drills/tests only
ENV_FILE = os.environ.get("BL_ENV_FILE", "/opt/data/.env")

RESTART_WAIT = int(os.environ.get("BL_RESTART_WAIT_SEC", "25"))
RESTART_ATTEMPTS = int(os.environ.get("BL_RESTART_ATTEMPTS", "2"))
SETTLE = float(os.environ.get("BL_SETTLE_SEC", "3"))   # must survive this long to count as healed
FLAP_WINDOW = 1800          # 30 min
FLAP_LIMIT = 3             # restarts inside the window that count as flapping
ALERT_WINDOW = 1800        # never repeat the same alert inside 30 min

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


# ---------------------------------------------------------------- scheduler

def _scheduler_identity(pid):
    """True only if pid is OUR scheduler: cmdline matches and cwd is this project."""
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            cmd = f.read().replace(b"\0", b" ").decode(errors="replace")
    except OSError:
        return False
    if "group_scheduler.py" not in cmd or " run" not in cmd:
        return False
    try:
        cwd = os.readlink("/proc/%d/cwd" % pid)
    except OSError:
        return False
    return os.path.realpath(cwd) == os.path.realpath(BASE)


def scheduler_pid():
    """PID of the live Burger Lab scheduler, or None.

    The scheduler holds an flock on data/group_scheduler.lock and writes its pid
    there, so trying the lock tells us authoritatively whether it is up.
    """
    if os.path.exists(LOCK):
        try:
            fh = open(LOCK, "a+")
        except OSError:
            fh = None
        if fh is not None:
            try:
                try:
                    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    fh.seek(0)
                    raw = fh.read().strip()
                    try:
                        pid = int(raw)
                    except ValueError:
                        pid = 0
                    return pid if pid and _scheduler_identity(pid) else None
                else:
                    fcntl.flock(fh, fcntl.LOCK_UN)
            finally:
                fh.close()
    # Fallback: lock file missing or stale but our process is alive.
    for entry in os.listdir("/proc"):
        if entry.isdigit() and _scheduler_identity(int(entry)):
            return int(entry)
    return None


def start_scheduler():
    os.makedirs(DATA, exist_ok=True)
    log = open(LOG, "a")
    subprocess.Popen(
        [PY, os.path.relpath(SCHED_SCRIPT, BASE), "run"],
        cwd=BASE, stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True, close_fds=True,
    )
    log.close()
    deadline = time.time() + RESTART_WAIT
    pid = None
    while time.time() < deadline:
        pid = scheduler_pid()
        if pid:
            break
        time.sleep(0.25)
    if not pid:
        return None
    # A process that dies within seconds is not a heal — wait out the settle window.
    time.sleep(SETTLE)
    return pid if scheduler_pid() == pid else None


# ---------------------------------------------------------------- sender

def sender_ok(timeout=6):
    try:
        with urllib.request.urlopen(SENDER_URL + "/health", timeout=timeout) as r:
            if r.status != 200:
                return False
            try:
                return bool(json.loads(r.read().decode()).get("ok"))
            except ValueError:
                return True
    except (urllib.error.URLError, OSError):
        return False


def start_sender():
    try:
        subprocess.run([BOT_START], capture_output=True, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        pass
    deadline = time.time() + 45
    while time.time() < deadline:
        if sender_ok():
            return True
        time.sleep(1)
    return False


# ---------------------------------------------------------------- alerts

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
    """Send once per ALERT_WINDOW per key. Returns True when the text went out."""
    sent = state.setdefault("alerts", {})
    last = sent.get(key, 0)
    if time.time() - last < ALERT_WINDOW:
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


def recovered(state, key, text):
    """Announce a recovery only if we alerted about that key before."""
    if state.get("alerts", {}).pop(key, None):
        if ALERT_DRY:
            with open(ALERT_DRY, "a") as f:
                f.write(text + "\n---\n")
        else:
            telegram(text)
        return True
    return False


# ---------------------------------------------------------------- main

def main():
    os.makedirs(DATA, exist_ok=True)
    state = load_json(STATE, {})
    actions, problems = [], []

    pid = scheduler_pid()
    if pid is None:
        healed = None
        for attempt in range(1, RESTART_ATTEMPTS + 1):
            healed = start_scheduler()
            if healed:
                break
            if attempt < RESTART_ATTEMPTS:
                time.sleep(3)
        if healed:
            actions.append("scheduler restarted pid=%d" % healed)
            state.setdefault("restarts", []).append(time.time())
            if recovered(state, "scheduler_failed", "✅ Burger Lab: scheduler is back (pid %d)" % healed):
                actions.append("scheduler recovery announced")
        else:
            problems.append("scheduler")
            alert(state, "scheduler_failed",
                  "🔴 Burger Lab: scheduler is down and would not start after %d attempts (%s IST).\n"
                  "Group posts will not go out. Last log:\n%s"
                  % (RESTART_ATTEMPTS, now_ist().strftime("%d %b %H:%M"),
                     tail(LOG, 6)))

    if not sender_ok():
        if start_sender():
            actions.append("sender restarted on %s" % SENDER_URL)
            if recovered(state, "sender_failed", "✅ Burger Lab: WhatsApp sender is back (%s)" % SENDER_URL):
                actions.append("sender recovery announced")
        else:
            problems.append("sender")
            alert(state, "sender_failed",
                  "🔴 Burger Lab: WhatsApp sender is down on %s and would not start (%s IST)."
                  % (SENDER_URL, now_ist().strftime("%d %b %H:%M")))

    restarts = [t for t in state.get("restarts", []) if time.time() - t < FLAP_WINDOW]
    state["restarts"] = restarts
    if len(restarts) >= FLAP_LIMIT:
        problems.append("flapping")
        alert(state, "flapping",
              "🔴 Burger Lab: scheduler/sender restarted %d times in 30 min — something is killing it. "
              "Check %s" % (len(restarts), LOG))

    ok = not problems
    save_json(STATE, state)
    save_json(HEARTBEAT, {
        "ts": time.time(),
        "ist": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": ok,
        "actions": actions,
        "problems": problems,
        "restarts_last_30m": len(restarts),
        "checks": {
            "scheduler": {"up": scheduler_pid() is not None},
            "sender": {"up": sender_ok()},
        },
    })

    if actions:
        print("⚠️ Burger Lab watchdog: " + "; ".join(actions))
    if problems:
        print("❌ Burger Lab watchdog: still broken — " + ", ".join(problems))
    return 0 if ok else 1


def tail(path, lines):
    try:
        with open(path, errors="replace") as f:
            return "".join(f.readlines()[-lines:]).strip() or "(empty log)"
    except OSError:
        return "(no log)"


if __name__ == "__main__":
    sys.exit(main())
