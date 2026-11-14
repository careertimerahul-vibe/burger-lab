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
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

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
    return [g for g in json.load(open(GROUPS)) if g.get("enabled", True) and g.get("jid")]


def load_queue():
    if not os.path.exists(QUEUE):
        return {"date": now_ist().strftime("%Y-%m-%d"), "messages": []}
    return json.load(open(QUEUE))


def save_queue(q):
    tmp = QUEUE + ".tmp"
    json.dump(q, open(tmp, "w"), indent=1, ensure_ascii=False)
    os.replace(tmp, QUEUE)


def load_config():
    """Poster-level switches (data/poster_config.json). Missing file = manual approval."""
    p = f"{DATA}/poster_config.json"
    if not os.path.exists(p):
        return {}
    try:
        return json.load(open(p))
    except Exception:
        return {}


def auto_approve(queue):
    """Promote pending drafts to approved when the poster runs hands-off.

    Rahul's standing instruction (2026-11-14): nothing waits for him any more. Drafting and
    posting still stay separate — the 16:30 job writes the copy, this promotes it — so the
    three-part stack and the send-time checks are unchanged.
    """
    if not load_config().get("auto_approve"):
        return 0
    hit = 0
    for m in queue.get("messages", []):
        if m.get("status") == "pending":
            m["status"] = "approved"
            hit += 1
    if hit:
        save_queue(queue)
    return hit


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


# ---------- per-group link tagging ----------
# One approved copy is reused in every group, so the links are templated: the scheduler
# swaps {menu_url} / {order_url} for a version stamped with that group's utm_source.
# That is the only way to tell afterwards which group sent the visit or the WhatsApp chat.
MENU_BASE = "https://theburgerlabnoida.netlify.app/"
ORDER_BASE = "https://wa.me/919205491224"
INVITE_URL = "https://chat.whatsapp.com/ITnN3ll8cBiIFnEQysWuLu"


def _group_slug(group):
    return group.get("utm_source") or re.sub(r"[^a-z0-9]+", "_", group.get("name", "group").lower()).strip("_")


def render_text(msg, group, when=None):
    """Message text for THIS group: menu link and WhatsApp link carry the group's UTMs."""
    when = when or now_ist()
    slot = msg.get("slot") or (group.get("slots") or ["17:00"])[0]
    # Two params only — group code + post time. Everything else is noise in a chat bubble.
    query = urlencode({"utm_source": _group_slug(group), "utm_content": slot.replace(":", "")})
    menu = f"{MENU_BASE}?{query}"
    # WhatsApp cannot carry UTMs to the server, so the tag travels as the prefilled first
    # message: every chat that starts from a group post is labelled with that group.
    label = group.get("tag") or group.get("label") or group.get("name") or _group_slug(group)
    prefill = f"Hi! Saw your {label} post ({slot}). My order:"
    order = f"{ORDER_BASE}?text={quote(prefill)}"

    text = msg.get("text") or ""
    text = text.replace("{menu_url}", menu).replace("{order_url}", order)
    # Per-group policy: the invite only goes where the group allows it. Foodies and the
    # buy/sell group ban it outright, and our own group gains nothing from it.
    if group.get("append_invite") and group.get("allow_group_link"):
        text += f"\n\U0001F449 Offers & new drops first: {INVITE_URL}"
    if "{menu_url}" not in (msg.get("text") or ""):
        text = text.replace(MENU_BASE, menu)  # hand-written plain link -> still tagged
    if "{order_url}" not in (msg.get("text") or ""):
        text = re.sub(r"https?://wa\.me/919205491224(?!\?)", order.replace("\\", "\\\\"), text)
    return text


def append_post(row):
    new = not os.path.exists(POSTS)
    with open(POSTS, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "group", "utm_source", "msg_id", "slot", "eligible_at", "sent_at", "age_at_send", "message_id", "status", "error"])
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
def blocked_hits(text):
    """Fail-closed check: any blocklisted item name in the message cancels the send."""
    p = f"{DATA}/menu_blocklist.json"
    if not os.path.exists(p):
        return ""
    try:
        items = json.load(open(p)).get("blocked_items", [])
    except Exception:
        return ""
    t = (text or "").lower()
    for i in items:
        if i.lower() in t:
            return i
    return ""


def item_names_in(text):
    """Caption discipline: when a photo is attached the caption stays item-agnostic,
    so any specific menu item name is a hard block."""
    p = f"{DATA}/menu_item_names.json"
    if not os.path.exists(p):
        return ""
    try:
        names = json.load(open(p)).get("names", [])
    except Exception:
        return ""
    t = (text or "").lower()
    for n in names:
        if n.lower() in t:
            return n
    return ""


def is_crowd_photo(image_path):
    """True only when the photo actually shows people/queue — 'no people visible' does not count."""
    if not image_path:
        return False
    p = f"{DATA}/image_descriptions.json"
    if not os.path.exists(p):
        return False
    try:
        d = json.load(open(p))
    except Exception:
        return False
    desc = (d.get(os.path.basename(image_path), {}) or {}).get("desc", "").lower()
    desc = re.sub(r"no\s+(people|persons?|customers?|crowd|one)\b", " ", desc)
    desc = desc.replace("nobody", " ")
    positive = ("crowd", "queue", "customers", "people standing", "people waiting",
                "people visible", "several people", "multiple people", "backs turned",
                "people, backs", "persons")
    return any(k in desc for k in positive) or bool(re.search(r"\bpeople\b", desc))


def missing_crowd_line(text):
    """Crowd photos need a line about the crowd; a caption that ignores them wastes the shot."""
    t = (text or "").lower()
    cues = ("crowd", "queue", "fans", "waiting", "rush", "regulars", "doesn't lie",
            "does not lie", "that's the review", "thats the review")
    if any(c in t for c in cues):
        return False
    return not re.search(r"\bline\b", t)


def link_violation(text, group):
    """Invite links are allowed by DEFAULT; only groups that ban them block the send."""
    t = (text or "").lower()
    invites = ("chat.whatsapp.com", "whatsapp.com/channel", "wa.me/message")
    if not group.get("allow_group_link", True):
        for i in invites:
            if i in t:
                return f"group_invite_link({i})"
    if not group.get("allow_links", True):
        if "http://" in t or "https://" in t:
            return "links_not_allowed"
    return ""


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
    text = render_text(msg, group, now)
    gate_sec = int(group.get("min_gap_min", 16) * 60)
    cutoff = hhmm_today(group.get("cutoff", "23:30"))

    if posts_today(group["jid"], today) >= group.get("max_per_day", 3):
        return "skip", "daily_cap"

    # A slot that missed its window must expire, not slide for hours: a paused queue used to
    # flush breakfast posts at lunchtime. Checked before the spacing wait so a stale message
    # expires now instead of holding a "wait" slot. Allowance is our own spacing rule plus a
    # margin, so a normal gate/spacing delay never self-expires.
    max_late = group.get("max_late_min") or (group.get("own_post_spacing_min", 60) + 30)
    slot_at = hhmm_today(msg.get("slot") or group["slots"][0])
    late_min = int((now - slot_at).total_seconds() // 60)
    if late_min > max_late:
        return "expire", f"stale_slot(+{late_min}m>max{max_late}m)"

    elig = eligible_at(msg, group, today)
    if now < elig:
        return "wait", f"eligible {elig:%d %b %H:%M}"
    if now > cutoff:
        return "expire", "past_cutoff"

    code, st = api(f"/status?jid={group['jid']}")
    if code != 200 or not st.get("connected"):
        return "wait", f"bot_unreachable({code})"

    bad = blocked_hits(text)
    if bad:
        return "block", f"blocked_item={bad}"

    lv = link_violation(text, group)
    if lv:
        return "block", lv

    if msg.get("image"):
        named = item_names_in(text)
        if named:
            return "block", f"caption_not_agnostic names={named}"
        if is_crowd_photo(msg.get("image")) and missing_crowd_line(text):
            return "block", "crowd_photo_needs_crowd_line"

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
        "text": render_text(msg, group),
        "image_path": msg.get("image"),
        "min_age_sec": int(group.get("min_gap_min", 16) * 60),
        "dry_run": dry_run,
    }
    code, res = api("/send", payload)
    row = {
        "date": today,
        "group": group["jid"],
        "utm_source": _group_slug(group),
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


def ensure_standing(queue, groups, today):
    """Inject each group's fixed daily messages (e.g. The Burger Lab's last-orders post).

    The copy lives in a template file, not in the queue, so nobody re-types it and the model
    never paraphrases it. Idempotent: keyed on group + source label + date.
    """
    added = 0
    # Yesterday's queue must not block today's injection, so only same-day entries count.
    have = ({(m.get("group"), m.get("source")) for m in queue.get("messages", [])}
            if queue.get("date") == today else set())
    next_id = max([m.get("id") for m in queue["messages"] if isinstance(m.get("id"), int)] or [0]) + 1
    for g in groups:
        for s in g.get("standing_messages") or []:
            tpl = s.get("template")
            if not tpl or not os.path.exists(tpl):
                continue
            key = (g["jid"], s.get("label") or f"standing-{s.get('slot')}")
            if key in have:
                continue
            text = open(tpl, encoding="utf-8").read().rstrip("\n")
            queue["messages"].append({
                "id": next_id,
                "group": g["jid"],
                "slot": s["slot"],
                "not_before": f"{today} {s['slot']}",
                "status": "approved",
                "lang": "en",
                "image": s.get("image"),
                "text": text,
                "source": s.get("label") or f"standing-{s['slot']}",
            })
            print(f"injected standing message #{next_id} for {g.get('name')} at {s['slot']}", flush=True)
            next_id += 1
            added += 1
    if added:
        save_queue(queue)
    return added


def run(dry_run=False):
    # Single-instance lock: two schedulers would double-post.
    import fcntl
    lock_path = os.path.join(DATA, "group_scheduler.lock")
    # 'a+' so a losing instance cannot truncate the winner's pid before failing.
    lock_fh = open(lock_path, "a+")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another scheduler already holds the lock — exiting")
        return
    lock_fh.seek(0)
    lock_fh.truncate()
    lock_fh.write(str(os.getpid()))
    lock_fh.flush()
    print(f"scheduler up (dry_run={dry_run}) — IST {now_ist():%Y-%m-%d %H:%M:%S}")
    while True:
        try:
            if os.path.exists(PAUSE):
                time.sleep(POLL_SEC)
                continue
            groups = load_groups()
            today = now_ist().strftime("%Y-%m-%d")
            queue = load_queue()
            if queue.get("date") != today:
                # A new day: yesterday's leftovers must never fire against today's slots.
                queue = {"date": today, "note": "new day — awaiting the 16:30 draft", "messages": []}
                save_queue(queue)
            promoted = auto_approve(queue)
            if promoted:
                print(f"[{now_ist():%H:%M:%S}] auto-approved {promoted} pending message(s)", flush=True)
            ensure_standing(queue, groups, today)
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
                    # A broadcast belongs to a slot: a group that does not run that slot
                    # (own-group = 17:00 + 23:00 only) is not a target for it.
                    if not msg.get("group") and msg.get("slot") and g.get("slots") \
                            and msg["slot"] not in g["slots"]:
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
                        append_post({"date": now.strftime("%Y-%m-%d"), "group": g["jid"], "utm_source": _group_slug(g), "msg_id": msg.get("id"), "slot": msg.get("slot"), "eligible_at": "", "sent_at": "", "age_at_send": "", "message_id": "", "status": "expired", "error": detail})
                        print(f"[{now:%H:%M:%S}] {g['name']} msg#{msg.get('id')} EXPIRED ({detail})")
                    elif action == "block":
                        msg["status"] = "blocked"
                        save_queue(queue)
                        append_post({"date": now.strftime("%Y-%m-%d"), "group": g["jid"], "utm_source": _group_slug(g), "msg_id": msg.get("id"), "slot": msg.get("slot"), "eligible_at": "", "sent_at": "", "age_at_send": "", "message_id": "", "status": "blocked", "error": detail})
                        print(f"[{now:%H:%M:%S}] {g['name']} msg#{msg.get('id')} BLOCKED ({detail})")
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
            if not m.get("group") and m.get("slot") and g.get("slots") and m["slot"] not in g["slots"]:
                continue  # broadcast for a slot this group does not run
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


def gate_is_hard(group):
    """The quiet gate is a promise made to the group, not a suggestion.

    Every group posts only after `min_gap_min` minutes of silence. Nothing in this
    scheduler may override that — an ad dropped into a live conversation is what gets a
    number muted or reported. --force therefore refuses on a hard-gated group.
    """
    return group.get("hard_gate", True)


def post_now(mid, force=False, dry_run=False):
    queue = load_queue()
    groups = {g["jid"]: g for g in load_groups()}
    for m in queue.get("messages", []):
        if m.get("id") != int(mid):
            continue
        g = groups.get(m.get("group")) or list(groups.values())[0]
        if force and gate_is_hard(g):
            print(f"REFUSED: {g.get('name')} is hard-gated — post waits for "
                  f"{int(g.get('min_gap_min', 16))} min of quiet. --force cannot override it.")
            return
        bad = blocked_hits(m.get("text", ""))
        if bad and not force:
            print(f"BLOCKED: message mentions '{bad}' (blocklisted). Use --force to override.")
            return
        lv = link_violation(m.get("text", ""), g)
        if lv and not force:
            print(f"BLOCKED: {lv} — this group bans invite links. Use --force only if the group allows it.")
            return
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
