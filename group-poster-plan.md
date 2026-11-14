# Group Auto-Poster — plan v2 (answers locked)

Plan only, no build. Updated 2 Nov 2026, 19:30 IST.

## Target

- Group: **FOODIES OF GHKW 🍔🍟** → `120363425132405603@g.us` (number already a member)
- Sender: `9205491224` (linked companion device)
- Activity: 330 msgs in sync window, last 19:10 IST — busy, so the gate will slide often

## Rules as confirmed by Rahul

- Gate: the **last message of any kind** must be ≥ 15 min old. Buffer to 16 min for clock skew.
- **No time limit on lateness** — post at the first quiet moment, however late. Only hard stop: nothing after **23:30 IST** (store closes 00:00).
- Links allowed: **menu link (native landing page), phone number, address**. The **WhatsApp group invite link is banned**.
- 3 messages/day, drafted with the Burger Lab promo rules.

## Slot + queue model

Nominal slots 17:00 / 20:00 / 21:30, but they are *queued, not scheduled*:

1. Message 1 becomes eligible at 17:00. Posts at the first moment the gate passes.
2. Message 2 becomes eligible at `max(20:00, post1 + 60 min)` — spacing rule so three promos never bunch up if the group goes quiet at 21:00.
3. Message 3 same: `max(21:30, post2 + 60 min)`.
4. Anything still unposted at 23:30 is dropped and logged `expired`. No rollover to the next day — stale offers are worse than no post.

Gate loop: `age = now − last_group_msg_ts`; if `age ≥ 16 min` send; else poll every 60s, and every inbound group message resets the clock for free.

## Content

- Source of truth: `/opt/data/projects/burger-lab/promo-kit.md` (Burger Lab rules — **not** the Golf Homes food-court skill; that one explicitly excludes Burger Lab).
- Every message: native landing page `https://theburgerlabnoida.netlify.app/` + `wa.me/919205491224` + address when it fits. No group invite. 100% veg + air-fried framing, combo prices pulled live from `menu_items` kitchen_id=5.
- 16:30 generation → `data/today_messages.json`. If missing at slot time → `data/template_bank.json` fallback.
- Preview goes to Rahul on Telegram at 16:30 for eyes-on; posting proceeds regardless (he asked for automated posting). Anytime veto = create `data/group_bot.pause`.

## Multi-group from day one

Groups are config, not code — `data/groups.yaml`:

```yaml
- jid: 120363425132405603@g.us
  name: FOODIES OF GHKW
  enabled: true
  slots: ["17:00", "20:00", "21:30"]
  min_gap_min: 16          # quiet time required before posting
  own_post_spacing_min: 60 # gap between our own posts
  cutoff: "23:30"
  max_per_day: 3
  allow_group_link: false  # this group bans it
  allow_links: true
  content_rules: burger-lab-promo
  tone: casual             # per-group guideline hook
```

Adding a group later = one block + its own guidelines. A group with different rules (no links, 1 post/day, different tone, different cutoff) is a config change, not a new build.

## Components

1. `scripts/wa_group_bot.mjs` — persistent Baileys socket on the existing session; tracks `last_group_msg_ts` per group into `data/group_state.json` on every inbound message; local HTTP 127.0.0.1:8631, token-guarded: `GET /status`, `POST /send` (refuses when the gate fails unless `force=true`), `GET /log`. Reconnect with backoff + heartbeat file.
2. `scripts/group_scheduler.py` — no LLM. Owns the queue, gate loop, spacing rule, cutoff, sends, and logs `date, group, slot, scheduled_at, sent_at, age_at_send, message_id, status` to `data/group_posts.csv`. Telegram alert on post / expire / failure.
3. 16:30 generation step → `today_messages.json` + Telegram preview.
4. Keepalive: start script + existing keepalive cron so both processes return after restart.

## Rails

- Pause file stops everything; checked before every send.
- Max 3 posts/day/group, ±2–4 min jitter inside the gate window, one message per gate pass.
- Two failed sends → drop the slot, alert, no retry loop.
- Offline > 10 min → mark the queue stale, don't post on reconnect if the slot is past cutoff.
- Deletion detection: if the group gets new messages within 60s of our post, twice in one day → auto-disable that group and alert.
- Post-send verification: message id returned + our message is the newest in the group, both logged.

## ToS reality (unchanged)

One group, ≤3 posts/day, from a genuine member number, human-ish timing: low but non-zero restriction risk. Official Cloud API cannot post to this group at all. Pause file is the mitigation.

## Still open

- Which of the three daily messages carries the link vs text-only (current default: all three carry menu + phone; drop to 1-in-3 if the group starts moderating).
- Build order when Rahul says go: socket bot → scheduler → content hook → 3-day supervised run before it's left alone.

## BUILT — 2 Nov 2026

| Piece | Path |
|---|---|
| Socket bot (state + send API, port 8631) | `/opt/data/scripts/whatsapp-bridge/wa_group_bot.mjs` |
| Scheduler (queue, gate, approvals, log) | `/opt/data/projects/burger-lab/scripts/group_scheduler.py` |
| Start / restart | `scripts/start_group_bot.sh` |
| Watchdog (silent when healthy) | `scripts/keepalive_group_bot.sh` → cron `be37348ec3a3` every 10m |
| Draft cron (16:30 IST = 11:00 UTC) | cron `e6333b3ca06f` |
| Group config | `data/groups.json` |
| Today's queue | `data/today_messages.json` |
| Post log | `data/group_posts.csv` |
| Gate state | `data/group_state.json` |
| Pause switch | `touch data/group_bot.pause` |

Runbook
```
python scripts/group_scheduler.py status          # queue + live gate age
python scripts/group_scheduler.py approve 1,3     # arm messages
python scripts/group_scheduler.py reject 2
python scripts/group_scheduler.py post-now 1 --dry-run
scripts/start_group_bot.sh                        # restart socket bot
touch data/group_bot.pause                        # emergency stop
```

Verified: gate refuses at 92s quiet (409 `gate_not_met`), `--force` dry-run passes, real text send + real image+caption send both returned message ids to the number's own chat.

Images: photos go in `data/content_inbox/`; the 16:30 draft run picks unused ones, views them, and attaches the best fit (caption never claims anything the photo doesn't show).

