# The Burger Lab — Cron Jobs

| Job ID | Name | Schedule | Description |
|--------|------|----------|-------------|
| e6333b3ca06f | Burger Lab group post drafts | 16:30 IST daily | Drafts the day's group queue (`data/today_messages.json`), left `pending` for approval |
| be37348ec3a3 | Group bot watchdog | every 10 min | Self-heals the sender (:8631) and the scheduler; silent when healthy |
| 260ad48c02bf | Watchdog guard | every 15 min | Watches the watchdog: stale heartbeat or a failing watchdog job → alert |
| bb3b2f1e6b39 | Burger Lab WhatsApp Messages | 17:00 IST daily | Generates 3 WhatsApp marketing messages (weather/day aware) |

## Monitoring: two layers, both self-healing

```
cron (10m) ──> keepalive_group_bot.py ──> sender :8631 + scheduler  (heals, verifies)
                       │
                       └─ writes data/watchdog.heartbeat.json
cron (15m) ──> watchdog_guard.py ──> heartbeat fresh? job healthy?  (alerts, revives)
```

**Layer 1 — `scripts/keepalive_group_bot.py`** (called from cron through the thin
wrapper `/opt/data/scripts/keepalive_group_bot.sh`)

- Scheduler identity = the process that holds the flock on `data/group_scheduler.lock`,
  cross-checked against `/proc/<pid>/cmdline` **and** `/proc/<pid>/cwd`. Never `pgrep -f`
  on the bare script name: Food Court runs the same script name and the old check
  reported a dead Burger Lab scheduler as alive.
- A restart only counts as healed if the new process is still alive after the settle
  window (default 3 s). A scheduler that dies instantly is a failure, not a heal.
- Alerts go straight to Telegram (token from `/opt/data/.env`), deduped per issue for
  30 min; ≥3 restarts in 30 min is reported as flapping.
- Writes `data/watchdog.heartbeat.json`. Silent, exit 0 when healthy; exit 1 + one line
  on stdout when something stays broken (cron delivers that line).

**Layer 2 — `scripts/watchdog_guard.py`** (wrapper `/opt/data/scripts/burgerlab_watchdog_guard.py`)

- Heartbeat missing or older than 25 min → runs the watchdog once, then reports whether
  it revived.
- Watchdog cron job's `last_status` is an error with `failure_streak >= 2` → alert with
  the real error text (a single transient error is ignored).
- Job hasn't run for 30 min → alert.
- Delivers via Telegram directly, not through the cron path that failed on 2–14 Nov 2026
  (job pointed at a script that did not exist → 1,675 silent failures).

**Engine-level failures** (script missing, timeout, crash) are covered by
`failure_deliver: telegram:427257056` on both jobs.

## Tests

```bash
cd /opt/data/projects/burger-lab
python3 -m unittest discover -s scripts/tests -p "test_*.py"    # 14 tests, ~25 s
```

They run the watchdog against throwaway project trees with stub processes: healthy
silence, scheduler heal, sender heal, decoy scheduler from another project, unhealable
state → alert + exit 1, alert dedupe, heartbeat freshness, guard stale/error paths.

## Approval flow (unchanged)

Drafts land `pending`; `python3 scripts/group_scheduler.py status` shows the queue and
`... approve 1,2` marks messages to post. The watchdog does not touch approvals.
