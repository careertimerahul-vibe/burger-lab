#!/usr/bin/env python3
"""Tests for the Burger Lab day gate (scripts/day_gate.py + the scheduler block).

Why: the copy bank still holds day-named hooks (#57 "…testing in the lab this Friday") and the
daily draft is written by an agent, so a Friday hook can land in a Tuesday queue. The gate must
stop only real claims about the current day — evergreen jokes that mention a weekday must stay
usable, or the block silently costs posting slots.

Run: python3 scripts/tests/test_day_gate.py
"""
import importlib.util
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dg = load("day_gate", os.path.join(SCRIPTS, "day_gate.py"))
gm = load("group_scheduler", os.path.join(SCRIPTS, "group_scheduler.py"))

FRI = datetime(2026, 11, 20, 20, 0, tzinfo=gm.IST)
TUE = datetime(2026, 11, 17, 20, 0, tzinfo=gm.IST)

HOOK_57 = ("57. Only people inside the WhatsApp group know what we’re testing in the lab "
           "this Friday.")
HOOK_76 = "76. Your diet starts on Monday. Today is for scientific burger research."
HOOK_66 = "66. Warning: Leaving this group may result in severe FOMO every weekend evening."


def test_bank_hooks_are_read_correctly():
    assert dg.day_claim(HOOK_57) == "friday"
    assert dg.day_claim(HOOK_76) is None, "an evergreen joke must not be treated as a claim"
    assert dg.day_claim(HOOK_66) is None, "'every weekend evening' is not a Friday claim"
    assert dg.day_claim("IT'S FRIDAY NIGHT, people!") == "friday"
    assert dg.day_claim("🍔 It’s a lazy Sunday, order in.") == "sunday"
    assert dg.day_claim("Aaj Friday hai — kitchen band, order karo!") == "friday"
    assert dg.day_claim("Fresh paneer burgers from 5 PM, no weekday talk here.") is None


def test_mismatch_only_blocks_the_wrong_day():
    assert dg.mismatch(HOOK_57, FRI) is None
    assert dg.mismatch(HOOK_57, TUE) == "friday"
    assert dg.mismatch(HOOK_76, TUE) is None


def test_scheduler_blocks_foreign_day_copy():
    group = {"jid": "g1@g.us", "name": "T", "slots": ["20:00"], "min_gap_min": 16,
             "own_post_spacing_min": 60, "max_late_min": 600, "max_per_day": 3,
             "allow_links": True, "allow_group_link": True}
    msg = {"id": 1, "slot": "20:00", "status": "approved", "text": HOOK_57, "image": None}
    gm.posts_today = lambda jid, day: 0
    gm.last_post_time = lambda jid, day: None
    gm.api = lambda path: (200, {"connected": True, "age_sec": 5000})
    action, detail = gm.evaluate(group, msg, TUE)
    assert (action, detail) == ("block", "day_lock=friday"), (action, detail)
    action, detail = gm.evaluate(group, msg, FRI)
    assert action == "send", (action, detail)

    msg["text"] = HOOK_76  # evergreen Monday joke is postable on a Tuesday
    assert gm.evaluate(group, msg, TUE)[0] == "send"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as exc:
                fails += 1
                print(f"FAIL {name}: {exc}")
    raise SystemExit(1 if fails else 0)
