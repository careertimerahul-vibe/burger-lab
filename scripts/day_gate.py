"""Block queue copy that claims today is a specific weekday.

Why: the copy bank carries hooks like #57 "…we're testing in the lab this Friday" and the
Burger Lab draft is written fresh every afternoon by an agent, so a Friday hook can land in
a Tuesday queue and read wrong to every group.

Rule: only a *claim about the current day* is locked — "this Friday", "tonight is Friday",
"IT'S FRIDAY". Evergreen jokes that merely mention a weekday stay usable any day
("Your diet starts on Monday" is fine on a Wednesday), because over-blocking silently costs
a posting slot.

Used by group_scheduler.evaluate() (hard gate before send) and sanitize_queue.py (flags the
message when the queue is prepared).
"""
import re

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_DAY = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
_NEAR = r"(this|today|tonight|tonite|aaj|abhi)"

# "this Friday", "tonight is Friday night", "aaj Friday hai"
_NEAR_THEN_DAY = re.compile(rf"\b{_NEAR}\b(?:\W+\w+){{0,2}}?\W+{_DAY}\b", re.I)
# "IT'S FRIDAY NIGHT", "it is Sunday", "its Friday"
_ITS_DAY = re.compile(rf"\b(it['’]?s|it\s+is)\s+(?:a\s+|an\s+)?(?:\w+\s+){{0,2}}?{_DAY}\b", re.I)


def day_claim(text):
    """Weekday the copy claims it is today, or None when it makes no such claim."""
    flat = (text or "")
    for q in ("’", "‘", "`", "´"):
        flat = flat.replace(q, "'")
    for rx in (_ITS_DAY, _NEAR_THEN_DAY):
        m = rx.search(flat)
        if m:
            return m.group(2).lower()
    return None


def mismatch(text, when):
    """The claimed weekday when it is not `when`'s weekday — i.e. the reason to block."""
    lock = day_claim(text)
    if lock and lock != WEEKDAYS[when.weekday()]:
        return lock
    return None
