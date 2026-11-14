#!/usr/bin/env python3
"""Queue a "send now" message without ever skipping a group.

A group that is still mid-conversation must not be dropped — it must be waited for. So this
does not send anything itself: it appends one approved queue message per target group, and
the running scheduler polls that group every tick until its quiet gate clears, then posts.
The only way a queued message dies unsent is the group's own cutoff (23:30) or daily cap.

Usage:
  send_now.py --text-file copy.txt --image data/content_inbox/<day>/<file>.jpg --missing-today
  send_now.py --text-file copy.txt --image ... --to fg,ag,gh
  send_now.py --text-file copy.txt --image ... --to all

The copy may contain {menu_url} / {order_url}; the scheduler stamps each group's version at
send time. Inside text: line breaks are kept.
"""
import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("gs", os.path.join(HERE, "group_scheduler.py"))
gs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--image", default=None)
    ap.add_argument("--to", default="", help="comma-separated group codes, or 'all'")
    ap.add_argument("--missing-today", action="store_true",
                    help="target every enabled group that has not posted today")
    ap.add_argument("--label", default="send-now")
    a = ap.parse_args()

    text = open(a.text_file, encoding="utf-8").read().rstrip("\n")
    groups = gs.load_groups()
    today = gs.now_ist().strftime("%Y-%m-%d")

    if a.missing_today:
        targets = [g for g in groups if gs.posts_today(g["jid"], today) == 0]
    elif a.to.strip().lower() == "all":
        targets = groups
    else:
        codes = {c.strip() for c in a.to.split(",") if c.strip()}
        targets = [g for g in groups if g.get("utm_source") in codes]

    if not targets:
        print("no target groups"); sys.exit(1)

    queue = gs.load_queue()
    if queue.get("date") != today:
        queue = {"date": today, "note": "queued by send_now.py", "messages": []}
    next_id = max([m.get("id") for m in queue["messages"] if isinstance(m.get("id"), int)] or [0]) + 1
    slot = gs.now_ist().strftime("%H:%M")

    for g in targets:
        n = gs.posts_today(g["jid"], today)
        if n >= g.get("max_per_day", 3):
            print(f"{g['utm_source']:>3} at daily cap ({n}/{g.get('max_per_day')}) — queued anyway? no; skipped by cap")
            continue
        queue["messages"].append({
            "id": next_id,
            "group": g["jid"],
            "slot": slot,
            "not_before": f"{today} {slot}",
            "status": "approved",          # auto-approve is on; the scheduler still gates it
            "lang": "en",
            "image": a.image,
            "text": text,
            "source": a.label,
        })
        print(f"{g['utm_source']:>3} queued as msg #{next_id} (slot {slot}) — scheduler will post when its gate clears")
        next_id += 1

    gs.save_queue(queue)


if __name__ == "__main__":
    main()
