"""Sanitise the daily queue: drop blocklisted items, retarget to today, renumber slots."""
import json
from datetime import datetime, timedelta, timezone

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

json.dump(q, open(Q, "w"), indent=1, ensure_ascii=False)
print(f"date={today} sanitised_messages={changed}")
for m in q["messages"]:
    print(f"#{m['id']} {m['slot']} {m['status']} lines={len(m['text'].splitlines())}")
