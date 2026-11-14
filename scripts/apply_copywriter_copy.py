#!/usr/bin/env python3
"""Rewrite today's queue with copywriter-kit copy (Burger Lab).

Rules enforced here, then again by the scheduler at send time:
  - 3-part stack: hook / craving bridge / action block  (copywriter-kit.md)
  - 50-85 words, 2-4 emojis per message
  - captions stay item-agnostic (every slot has a photo) -> no menu item names
  - no group invite link: both enabled groups set allow_group_link=false
  - factual floors only (₹60 burger / ₹130 combo) from promo-kit.md

Usage: python3 scripts/apply_copywriter_copy.py [--dry-run]
"""
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

BASE = "/opt/data/projects/burger-lab"
Q = f"{BASE}/data/today_messages.json"
NAMES = f"{BASE}/data/menu_item_names.json"
BLOCK = f"{BASE}/data/menu_blocklist.json"
MENU = "https://theburgerlabnoida.netlify.app/"
ORDER = "wa.me/919205491224"
ADDRESS = "Gate No. 3, Amrapali Golf Homes Market"
INVITE = "chat.whatsapp.com"
IST = timezone(timedelta(hours=5, minutes=30))

FOODIES = "120363425132405603@g.us"
AGHKW = "120363407968758497@g.us"

TEXTS = {
    1: (
        "🕔 5 PM and the griddle's already hot\n"
        "First patties are down — thick, crisp-edged, cheese going molten, buns toasted till they crackle. "
        "Air-fried if you're watching the oil, classic golden if you're not.\n"
        "Burgers from ₹60, combos from ₹130\n"
        f"🍔 Menu: {MENU}\n"
        f"📱 Order: {ORDER}\n"
        f"{ADDRESS} · open till 12 AM"
    ),
    2: (
        "🍟 8 PM. Peak hour looks good on us\n"
        "Two patties, a slow cheese melt, a bun that still holds at the last bite. Nothing sits under a lamp here — "
        "it goes on the grill when you order it, and lands in your hand hot.\n"
        "Burgers from ₹60, combos from ₹130\n"
        f"🔥 Menu: {MENU}\n"
        f"📱 Order: {ORDER}\n"
        f"{ADDRESS} · open till 12 AM"
    ),
    3: (
        "🌙 9:30 PM and the grill's still on\n"
        "Stacked fresh, wrapped hot, handed over the counter at Gate 3 — no delivery box, no 25-minute wait, "
        "no platform markup. Air-fried or classic golden, whichever you're in the mood for.\n"
        "Burgers from ₹60, combos from ₹130\n"
        f"🍔 Menu: {MENU}\n"
        f"📱 Order: {ORDER}\n"
        f"{ADDRESS} · till 12 AM"
    ),
    4: (
        "🕕 6 PM, Sector 4 — dinner decisions start here\n"
        "Gourmet veg burgers built thick: crisp patty, molten cheese, house-made sauces, buns toasted to order. "
        "Air-fried options if you're counting oil, and no aggregator markup on the bill.\n"
        "Burgers from ₹60, combos from ₹130\n"
        f"🍔 Menu: {MENU}\n"
        f"📱 WhatsApp order: {ORDER}\n"
        f"{ADDRESS} · open till 12 AM"
    ),
    5: (
        "🌙 9 PM. Late-night cravings, sorted\n"
        "Patties hit the grill when you order, not at 6 PM. Thick, crisp, cheese-molten, sauces mixed in-house — "
        "and air-fried versions for the sensible ones. Ten minutes from craving to first bite.\n"
        "Burgers from ₹60, combos from ₹130\n"
        f"🍔 Menu: {MENU}\n"
        f"📱 Order: {ORDER}\n"
        f"{ADDRESS} · open till 12 AM"
    ),
}

LANGS = {1: "en", 2: "en", 3: "en", 4: "en", 5: "en"}

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def problems(mid, text, image):
    out = []
    words = len(text.split())
    if not 50 <= words <= 85:
        out.append(f"{words} words (need 50-85)")
    emojis = len(EMOJI.findall(text))
    if not 2 <= emojis <= 4:
        out.append(f"{emojis} emojis (need 2-4)")
    names = [n for n in json.load(open(NAMES)).get("names", []) if n.lower() in text.lower()]
    if names and image:
        out.append(f"menu item names in a photo caption: {names}")
    blocked = [b for b in json.load(open(BLOCK)).get("blocked_items", []) if b.lower() in text.lower()]
    if blocked:
        out.append(f"blocklisted: {blocked}")
    if INVITE in text:
        out.append("group invite link present (banned in both enabled groups)")
    for needle, label in ((MENU, "menu link"), (ORDER, "order link"), (ADDRESS, "address")):
        if needle not in text:
            out.append(f"missing {label}")
    if not re.search(r"12\s*(AM|baje)", text):
        out.append("missing hours")
    return out


def main():
    dry = "--dry-run" in sys.argv
    q = json.load(open(Q))
    failed = False
    for m in q["messages"]:
        mid = m.get("id")
        if mid not in TEXTS:
            continue
        text = TEXTS[mid]
        bad = problems(mid, text, m.get("image"))
        print(f"#{mid} {m.get('slot')} {m.get('group')[:20]} words={len(text.split())} "
              f"emojis={len(EMOJI.findall(text))} {'OK' if not bad else 'FAIL: ' + '; '.join(bad)}")
        if bad:
            failed = True
            continue
        if not dry:
            m["text"] = text
            m["lang"] = LANGS[mid]
    if dry:
        print("\n(dry run — queue untouched)")
        return 0 if not failed else 1
    if failed:
        print("\nnot writing: fix the failures above")
        return 1
    stamp = datetime.now(IST).strftime("%Y%m%d-%H%M")
    shutil.copy2(Q, Q.replace(".json", f".backup-{stamp}.json"))
    q["note"] = ("Copy from copywriter-kit.md (3-part stack, 50-85 words, 2-4 emojis, item-agnostic "
                 "captions). Messages 1-3 = FOODIES OF GHKW (17/20/21:30), 4-5 = AGHKW Advertising "
                 "(18/21). No group invite: both groups ban links. Price floors only.")
    json.dump(q, open(Q, "w"), indent=1, ensure_ascii=False)
    print(f"\nqueue updated, backup: data/today_messages.backup-{stamp}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
