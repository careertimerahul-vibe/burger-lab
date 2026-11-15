"""Sanitise the daily queue: drop blocklisted items, retarget to today, renumber slots."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import day_gate  # noqa: E402  (same-dir helper: copy must not claim another weekday)

Q = "/opt/data/projects/burger-lab/data/today_messages.json"
B = "/opt/data/projects/burger-lab/data/menu_blocklist.json"
IST = timezone(timedelta(hours=5, minutes=30))

q = json.load(open(Q))
blocked = [i.lower() for i in json.load(open(B)).get("blocked_items", [])]
today = datetime.now(IST).strftime("%Y-%m-%d")
slots = ["17:00", "20:00", "21:30"]

changed = []
for m in q["messages"]:
    keep = [ln for ln in m["text"].split("\n") if not any(b in ln.lower() for b in blocked)]
    if len(keep) != len(m["text"].split("\n")):
        changed.append(m["id"])
    m["text"] = "\n".join(keep)
    if m.get("not_before"):
        m["not_before"] = f"{today} {m['slot']}"

q["date"] = today
for m, s in zip(q["messages"], slots):
    m["slot"] = s
    m["not_before"] = f"{today} {s}"
    m["status"] = "pending"

# Copy that claims a different weekday ("…testing in the lab this Friday") is blocked here so
# the 16:30 draft can replace it, and the scheduler refuses it anyway as a second gate.
now = datetime.now(IST)
day_blocked = []
for m in q["messages"]:
    lock = day_gate.mismatch(m.get("text", ""), now)
    if lock:
        m["status"] = "blocked"
        m["block_reason"] = f"day_lock={lock}"
        day_blocked.append((m.get("id"), lock))

json.dump(q, open(Q, "w"), indent=1, ensure_ascii=False)
print(f"date={today} sanitised_messages={changed}")
for m in q["messages"]:
    print(f"#{m['id']} {m['slot']} {m['status']} lines={len(m['text'].splitlines())}")
if day_blocked:
    print("DAY-LOCK BLOCKED (redraft these from non-day copy): "
          + ", ".join(f"#{i}={day}" for i, day in day_blocked), file=sys.stderr)
