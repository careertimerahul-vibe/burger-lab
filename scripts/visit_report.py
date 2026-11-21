"""Menu-open report for Burger Lab.

The site logs one row per page load with the group's UTM attached (api/server.py POST
/api/visit). This prints opens by group, by hour and by slot, and pairs each slot with the
number of groups that actually received that post (data/group_posts.csv) so a slot's opens
can be read against its reach.

Usage: python3 scripts/visit_report.py [--days 7]
"""
import argparse, csv, os, collections, datetime
import psycopg2, psycopg2.extras

DB_URL = os.environ.get("DB_URL", "host=127.0.0.1 port=5433 dbname=burgerlab_pos user=burgerlab password=burgerlab_pos_2024")
POSTS = os.path.join(os.path.dirname(__file__), "..", "data", "group_posts.csv")
NAMES = {"fg": "FOODIES GHKW", "ag": "Buy/sell", "gm": "Golf Homes & Kingswood",
         "gp": "Golf Homes Business", "mc": "GH Marketplace Community",
         "ka": "Amrapali Kingswood ad", "bl": "The Burger Lab", "gh": "Golf homes"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT ts AT TIME ZONE 'Asia/Kolkata' AS ist, source, content, path, ref FROM visits "
        "WHERE ts >= now() - (%s || ' days')::interval ORDER BY ts", (args.days,))
    rows = cur.fetchall()
    print(f"Menu opens, last {args.days} day(s): {len(rows)}")
    if not rows:
        print("No opens logged yet — either nobody opened the link, or the beacon is not deployed.")
        return

    by_src = collections.Counter(r["source"] or "(direct)" for r in rows)
    print("\nOpens by group")
    for src, n in by_src.most_common():
        print(f"  {NAMES.get(src, src):24} {n:4}  {n * 100 // len(rows):3}%")

    by_hour = collections.Counter(r["ist"].hour for r in rows)
    print("\nOpens by hour (IST)")
    for h in range(24):
        if by_hour[h]:
            print(f"  {h:02d}:00  {'█' * by_hour[h]} {by_hour[h]}")

    by_day = collections.Counter(r["ist"].date().isoformat() for r in rows)
    print("\nOpens by day")
    for d in sorted(by_day)[-10:]:
        print(f"  {d}  {by_day[d]}")

    # Reach per slot from the delivery ledger, so opens can be read against how many groups got it.
    reached = collections.Counter()
    if os.path.exists(POSTS):
        for r in csv.DictReader(open(POSTS, encoding="utf-8")):
            cutoff = (datetime.date.today() - datetime.timedelta(days=args.days)).isoformat()
            if r["status"] == "sent" and r["date"] >= cutoff:
                reached[r["slot"].replace(":", "")] += 1
    by_slot = collections.Counter(r["content"] or "-" for r in rows)
    print("\nOpens by slot (vs groups that received that slot)")
    for slot, n in sorted(by_slot.items()):
        print(f"  {slot:>5}  opens={n:3}  posts_sent={reached.get(slot, 0):3}  opens/post={n / max(reached.get(slot, 1), 1):.2f}")


if __name__ == "__main__":
    main()
