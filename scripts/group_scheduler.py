#!/usr/bin/env python3
"""Burger Lab group auto-poster — queue, 15-min quiet gate, approvals, logging.

The socket process (wa_group_bot.mjs) owns WhatsApp state and delivery.
This process owns policy: which message, when, whether it is approved.

Commands
  run [--dry-run]     daemon loop (default)
  status              show today's queue + live gate ages
  approve 1,2         mark messages approved (posts at next eligible moment)
  reject 1            mark rejected
  post-now 2          send immediately (still respects the 15-min gate unless --force)
  test-gate           print gate state for each configured group
"""
import csv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("GROUP_POSTER_BASE", "/opt/data/projects/burger-lab")
DATA = f"{BASE}/data"
GROUPS = f"{DATA}/groups.json"
QUEUE = f"{DATA}/today_messages.json"
POSTS = f"{DATA}/group_posts.csv"
PAUSE = f"{DATA}/group_bot.pause"
TOKEN_FILE = f"{DATA}/bot_token.txt"
API = os.environ.get("GROUP_BOT_API", "http://127.0.0.1:8631")
IST = timezone(timedelta(hours=5, minutes=30))

POLL_SEC = 30


# ---------- helpers ----------
def now_ist():
    return datetime.now(IST)


def load_groups():
    if not os.path.exists(GROUPS):
        return []
    return [g for g in json.load(open(GROUPS)) if g.get("enabled", True)]


def load_queue():
    if not os.path.exists(QUEUE):
        return {"date": now_ist().strftime("%Y-%m-%d"), "messages": []}
    return json.load(open(QUEUE))


def save_queue(q):
    tmp = QUEUE + ".tmp"
    json.dump(q, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, QUEUE)


def token():
    return open(TOKEN_FILE).read().strip() if os.path.exists(TOKEN_FILE) else ""


def api(path, payload=None, method=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"x-bot-token": token(), "Content-Type": "application/json"},
        method=method or ("POST" if payload is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {"error": "unreadable"}
    except Exception as e:
        return 0, {"error": str(e)}


def hhmm_today(s):
    h, m = [int(x) for x in s.split(":")]
    return now_ist().replace(hour=h, minute=m, second=0, microsecond=0)


def append_post(row):
    new = not os.path.exists(POSTS)
    with open(POSTS, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "group", "msg_id", "slot", "eligible_at", "sent_at", "age_at_send", "message_id", "status", "error"])
        if new:
            w.writeheader()
        w.writerow(row)


def last_post_time(group_jid, today):
    """Latest successful post for this group today (for the spacing rule)."""
    if not os.path.exists(POSTS):
        return None
    latest = None
    with open(POSTS, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("group") == group_jid and row.get("date") == today and row.get("status") == "sent":
                try:
                    t = datetime.strptime(row["sent_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
                except Exception:
                    continue
                if latest is None or t > latest:
                    latest = t
    return latest


def posts_today(group_jid, today):
    if not os.path.exists(POSTS):
        return 0
    with open(POSTS, newline="", encoding="utf-8") as fh:
        return sum(1 for r in csv.DictReader(fh) if r.get("group") == group_jid and r.get("date") == today and r.get("status") == "sent")


# ---------- core ----------
def eligible_at(msg, group, today):
    """When this message may post: its slot, its not_before floor, pushed by our spacing rule."""
    slot = hhmm_today(msg.get("slot") or group["slots"][0])
    floor = slot
    nb = msg.get("not_before")
    if nb:
        try:
            floor = max(floor, datetime.strptime(nb, "%Y-%m-%d %H:%M").replace(tzinfo=IST))
        except Exception:
            pass
    last = last_post_time(group["jid"], today)
    if last:
        spacing = last + timedelta(minutes=group.get("own_post_spacing_min", 60))
        return max(floor, spacing)
    return floor


def evaluate(group, msg, now, dry_run=False):
    """Return (action, detail)."""
    today = now.strftime("%Y-%m-%d")
    gate_sec = int(group.get("min_gap_min", 16) * 60)
    cutoff = hhmm_today(group.get("cutoff", "23:30"))

    if posts_today(group["jid"], today) >= group.get("max_per_day", 3):
        return "skip", "daily_cap"

    elig = eligible_at(msg, group, today)
    if now < elig:
        return "wait", f"eligible {elig:%d %b %H:%M}"
    if now > cutoff:
        return "expire", "past_cutoff"

    code, st = api(f"/status?jid={group['jid']}")
    if code != 200 or not st.get("connected"):
        return "wait", f"bot_unreachable({code})"

    age = st.get("age_sec")
    if age is None:
        return "wait", "no_group_state"
    age = int(age)
    if age < gate_sec:
        return "wait", f"group_active age={age}s need>={gate_sec}s"

    return "send", f"age={age}s"


def do_send(group, msg, dry_run=False):
    today = now_ist().strftime("%Y-%m-%d")
    payload = {
        "jid": group["jid"],
        "text": msg["text"],
        "image_path": msg.get("image"),
        "min_age_sec": int(group.get("min_gap_min", 16) * 60),
        "dry_run": dry_run,
    }
    code, res = api("/send", payload)
    row = {
        "date": today,
        "group": group["jid"],
        "msg_id": msg.get("id"),
        "slot": msg.get("slot"),
        "eligible_at": "",
        "sent_at": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
        "age_at_send": res.get("age_sec", ""),
        "message_id": res.get("message_id", ""),
        "status": ("dry_run" if dry_run else "sent") if code == 200 else "failed",
        "error": "" if code == 200 else str(res.get("error"))[:120],
    }
    append_post(row)
    return code, res


def run(dry_run=False):
    print(f"scheduler up (dry_run={dry_run}) — IST {now_ist():%Y-%m-%d %H:%M:%S}")
    while True:
        try:
            if os.path.exists(PAUSE):
                time.sleep(POLL_SEC)
                continue
            groups = load_groups()
            queue = load_queue()
            if not groups or not queue.get("messages"):
                time.sleep(POLL_SEC)
                continue
            now = now_ist()
            for g in groups:
                for msg in queue["messages"]:
                    if msg.get("status") != "approved":
                        continue
                    if msg.get("group") and msg["group"] != g["jid"]:
                        continue
                    action, detail = evaluate(g, msg, now, dry_run)
                    if action == "send":
                        code, res = do_send(g, msg, dry_run)
                        print(f"[{now:%H:%M:%S}] {g['name']} msg#{msg.get('id')} SEND -> {code} {res.get('message_id') or res.get('error')} ({detail})")
                        if code == 200 and not dry_run:
                            msg["status"] = "sent"
                            msg["message_id"] = res.get("message_id")
                            save_queue(queue)
                        elif code == 409:
                            msg["status"] = "approved"  # gate closed in between; retry next tick
                    elif action == "expire" and msg.get("status") == "approved":
                        msg["status"] = "expired"
                        save_queue(queue)
                        append_post({"date": now.strftime("%Y-%m-%d"), "group": g["jid"], "msg_id": msg.get("id"), "slot": msg.get("slot"), "eligible_at": "", "sent_at": "", "age_at_send": "", "message_id": "", "status": "expired", "error": detail})
                        print(f"[{now:%H:%M:%S}] {g['name']} msg#{msg.get('id')} EXPIRED ({detail})")
        except Exception as e:
            print("loop_error", e)
        time.sleep(POLL_SEC)


def status():
    groups = load_groups()
    queue = load_queue()
    now = now_ist()
    print(f"IST now: {now:%Y-%m-%d %H:%M:%S}   queue date: {queue.get('date')}   pause: {os.path.exists(PAUSE)}")
    for g in groups:
        code, st = api(f"/status?jid={g['jid']}")
        age = st.get("age_sec") if code == 200 else None
        print(f"\n{g['name']}  ({g['jid']})  connected={st.get('connected')}")
        print(f"  gate: need >={int(g.get('min_gap_min',16)*60)}s quiet | current age: {age}s | last: {(st.get('last_text') or '')[:50]}")
        print(f"  posts today: {posts_today(g['jid'], now.strftime('%Y-%m-%d'))}/{g.get('max_per_day',3)} | cutoff {g.get('cutoff','23:30')}")
        for m in queue.get("messages", []):
            if m.get("group") and m["group"] != g["jid"]:
                continue
            act, detail = evaluate(g, m, now)
            print(f"   #{m.get('id')} slot {m.get('slot')} [{m.get('status')}] -> {act} ({detail})")
            print(f"      {(m.get('text') or '')[:90]}...")


def mark(ids, new_status):
    queue = load_queue()
    wanted = {int(i) for i in ids.replace(" ", "").split(",") if i}
    hit = 0
    for m in queue.get("messages", []):
        if m.get("id") in wanted:
            m["status"] = new_status
            hit += 1
    save_queue(queue)
    print(f"{hit} message(s) -> {new_status}")


def post_now(mid, force=False, dry_run=False):
    queue = load_queue()
    groups = {g["jid"]: g for g in load_groups()}
    for m in queue.get("messages", []):
        if m.get("id") != int(mid):
            continue
        g = groups.get(m.get("group")) or list(groups.values())[0]
        payload = {"jid": g["jid"], "text": m["text"], "image_path": m.get("image"),
                   "min_age_sec": int(g.get("min_gap_min", 16) * 60), "force": force, "dry_run": dry_run}
        code, res = api("/send", payload)
        print(code, json.dumps(res)[:300])
        if code == 200 and not dry_run:
            m["status"] = "sent"
            m["message_id"] = res.get("message_id")
            save_queue(queue)
        return
    print("message not found")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    args = sys.argv[2:]
    if cmd == "run":
        run(dry_run="--dry-run" in args)
    elif cmd == "status":
        status()
    elif cmd == "approve":
        mark(args[0], "approved")
    elif cmd == "reject":
        mark(args[0], "rejected")
    elif cmd == "post-now":
        post_now(args[0], force="--force" in args, dry_run="--dry-run" in args)
    else:
        print(__doc__)
