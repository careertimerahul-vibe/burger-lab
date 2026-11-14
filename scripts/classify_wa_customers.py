#!/usr/bin/env python3
"""Classify Burger Lab WhatsApp chats into customer / lead / vendor / spam / personal.

Input : JSON dump from /opt/data/scripts/whatsapp-bridge/link_export.mjs
Output: CSV with verdict + confidence + quoted evidence, plus a counts summary.

Rules-first: deterministic scoring, no LLM call. Report writes itself so it can
be re-run after every sync without spending tokens.
"""
import json
import re
import sys
import csv
from collections import Counter

SRC = sys.argv[1] if len(sys.argv) > 1 else "/opt/data/projects/burger-lab/data/wa_burgerlab_full.json"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/opt/data/projects/burger-lab/data/wa_customers.csv"

FOOD = r"(burger|fries|combo|sandwich|paneer|peri peri|jalapeno|tandoori|lava cake|cheese|cheesy|loaded|menu|momos|wrap|shake|coke|pepsi|thali|snack|patty|tikki|air ?fried)"
ORDER = r"(order|chahiye|chaiye|bhej|parcel|pickup|pick up|deliver|delivery|address|kitna|kitne|rate|price|available|open|timing|khula|de do|dega|send kar|book)"
PAY = r"(₹|rs\.? ?\d|\d{2,4} ?rupees|upi|gpay|phonepe|paytm|paid|cash)"
VENDOR = r"(wholesale|supplier|distributor|invoice|bill|stock|bulk rate|crate|packet|kg rate|dealer|purchase order|gst|firm)"
LOGISTICS = r"(swiggy|zomato|blinkit|zepto|delivery boy|rider|dunzo|porter)"
SPAM = r"(loan|credit card|insurance|policy|job opening|hiring|salary|work from home|click here|limited period offer|congratulation|you have won|lucky draw|recharge|casino|betting|forex|trading tips|real estate|plot|flat for sale)"
PERSONAL = r"(happy birthday|shaadi|marriage|bhaiya ji|mummy|papa|bhabhi|dost|bday|anniversary)"
ORDER_FORM = r"(would like to place an order|place an order|order confirm|order placed)"


def score_chat(chat):
    """Return (verdict, confidence, evidence, flags)."""
    if chat.get("is_group"):
        return "group", "", "", ""

    inbound = [m["x"] for m in chat.get("messages", []) if not m.get("me") and m.get("x")]
    outbound = [m["x"] for m in chat.get("messages", []) if m.get("me") and m.get("x")]
    blob_in = " ".join(inbound).lower()
    blob_out = " ".join(outbound).lower()

    if not inbound:
        return "no_inbound", "", "business sent, no reply", ""

    s = Counter()
    ev = {}

    def hit(pattern, bucket, weight, texts, label):
        for t in texts:
            m = re.search(pattern, t, re.I)
            if m:
                s[bucket] += weight
                ev.setdefault(bucket, t[:160])
                ev.setdefault(f"{bucket}_word", m.group(0).lower())
                return True
        return False

    hit(FOOD, "customer", 3, inbound, "food")
    hit(ORDER, "customer", 2, inbound, "order")
    hit(PAY, "customer", 2, inbound, "pay")
    # A website/menu order form submission is a definite order, not a signal.
    ordered = any(re.search(ORDER_FORM, t, re.I) for t in inbound)
    # Business replied with a menu/price => real order conversation
    if re.search(FOOD, blob_out) and re.search(PAY + "|" + ORDER, blob_out):
        s["customer"] += 2
        ev.setdefault("customer", "business quoted menu/price")
    if len(inbound) >= 3 and chat.get("msg_count", 0) >= 6:
        s["customer"] += 1

    hit(VENDOR, "vendor", 3, inbound, "vendor")
    hit(LOGISTICS, "logistics", 3, inbound, "logistics")
    hit(SPAM, "spam", 3, inbound, "spam")
    hit(PERSONAL, "personal", 1, inbound, "personal")

    ranked = s.most_common()
    if ordered:
        return "ordered", "high", ev.get("customer", inbound[0][:160]), ""
    if not ranked or ranked[0][1] == 0:
        return "unknown", "low", ev.get("customer", inbound[0][:160]), "no signal"

    top, top_score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0
    verdict = {
        "customer": "customer",
        "vendor": "vendor",
        "logistics": "logistics",
        "spam": "spam",
        "personal": "personal",
    }[top]
    margin = top_score - second
    conf = "high" if margin >= 3 else "medium" if margin >= 1 else "low"
    flags = ""
    if verdict != "customer" and s["customer"] > 0:
        flags = f"also_customer_signal={s['customer']}"
    return verdict, conf, ev.get(top, ""), flags


def main():
    data = json.load(open(SRC))
    rows = []
    for chat in data:
        verdict, conf, evidence, flags = score_chat(chat)
        rows.append({
            "phone": chat.get("phone", ""),
            "name": chat.get("name", ""),
            "verdict": verdict,
            "confidence": conf,
            "last_activity": chat.get("last_activity", ""),
            "msg_count": chat.get("msg_count", 0),
            "evidence": evidence.replace("\n", " ")[:160],
            "flags": flags,
        })

    order = {"ordered": 0, "customer": 1, "unknown": 2, "personal": 3, "vendor": 4, "logistics": 5, "spam": 6, "no_inbound": 7, "group": 8}
    rows.sort(key=lambda r: (order.get(r["verdict"], 9), -int(r["msg_count"] or 0)))

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else
                           ["phone", "name", "verdict", "confidence", "last_activity", "msg_count", "evidence", "flags"])
        w.writeheader()
        w.writerows(rows)

    counts = Counter(r["verdict"] for r in rows)
    confs = Counter((r["verdict"], r["confidence"]) for r in rows)
    print(f"OUT {OUT} total={len(rows)}")
    for k, v in counts.most_common():
        print(f"  {k}: {v}")
    print("confidence customer:", dict((c, n) for (v, c), n in confs.items() if v == "customer"))


if __name__ == "__main__":
    main()
