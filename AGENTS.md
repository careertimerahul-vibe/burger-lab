# AGENTS.md — The Burger Lab

> Shared rules (tools, safety, output, paths): `/opt/data/projects/_shared/AGENTS.md`

## Project
100% vegetarian food cart/brand in Greater Noida focused on flavorful, late-evening food, WhatsApp marketing, Google Business Profile, and local growth.

## Goals
- Create punchy WhatsApp/social content.
- Maintain Google Business Profile and digital presence assets.
- Highlight air-fried options and local Greater Noida appeal when relevant.

## Hard Rules
- The brand is strictly vegetarian. Avoid all non-veg references completely.
- Do not publish/send customer-facing messages without Rahul approval unless explicitly asked.
- Avoid generic template-like marketing.
- Keep content evergreen unless a dated campaign is requested.

## Default Workflows
- WhatsApp messages should be creative, short, pun-filled, and ready to send.
- Prefer local hooks: evening cravings, weather, weekend mood, student/office crowd.
- For cron changes: update ./cron docs and convert UTC schedules to IST in responses.
- For business facts like phone/hours/address/prices, update the canonical file first and avoid duplicate hardcoding.

## Important Paths
- Project root: /opt/data/projects/burger-lab
- Promo kit & message drafting rules: /opt/data/projects/burger-lab/promo-kit.md
- Social publishing config (Instagram t_burger_lab + WhatsApp groups): /opt/data/projects/burger-lab/social.config.yaml — contract in /opt/data/projects/social-media/README.md
- Cron docs: /opt/data/projects/burger-lab/cron
- WhatsApp script: /opt/data/projects/burger-lab/scripts/whatsapp_messages.py
- Digital presence docs: README.md and related setup docs in root

## Commands
- Inspect README.md before changing business info.
- For cron/script edits, run the script or a safe dry run where possible.
- Watchdog tests: `python3 -m unittest discover -s scripts/tests -p "test_*.py"`.
- This project may be a separate git repo/submodule; commit from inside the project root if needed.

## POS app — backend & analytics

`pos/` is the cart-side POS (Netlify site `theburgerlabnoida`). Its data path, in order:

    browser /api/* → netlify/functions/api.js → https://foodcourt.superllm.cloud/burgerlab-api
    → bridge route in amrapali-food-app backend/api.py → supervisor `burgerlab-api` :8901
    → own PG cluster :5433 (data dir /opt/data/pgdata-pos, db burgerlab_pos)

- The old setup (Postgres on Rahul's PC behind a throwaway trycloudflare tunnel) is what produced
  the multi-day 502s. Both halves now run on this box under supervisor (`burgerlab-pg`, priority 20;
  `burgerlab-api`, priority 30); supervisord itself is revived by the AGH keepalive cron.
- The `/burgerlab-api` prefix exists because the shared tunnel has no spare DNS slot we can create.
  An ingress rule for `pos.superllm.cloud` is already staged in `/opt/data/home/.cloudflared/config.yml`;
  it goes live on the next restart of the root-owned tunnel, at which point set Netlify env
  `BURGERLAB_API_URL=https://pos.superllm.cloud` and the bridge stops being used. No code change.
- Analytics lives in `pos/analytics.js` (tab `📊 Analytics`): KPIs vs previous period, revenue trend,
  peak hours, weekday split, top/thinnest items, category + source/delivery/spice mix, CSV export.
  All bucketing is Asia/Kolkata on purpose — never switch it to viewer-local time.
- Costs are empty until cost prices are entered in the Costs tab, so margin reads 100% or "—" and
  the dashboard shows a costing-gap warning. That is missing data, not a bug.

Verify:
```bash
/opt/data/venvs/supervisor/bin/supervisorctl -c /opt/data/supervisor/supervisord.conf status
curl -s -H 'Authorization: Bearer burgerlab_pos_2024' http://127.0.0.1:8901/api/orders
curl -s -H 'Authorization: Bearer burgerlab_pos_2024' https://theburgerlabnoida.netlify.app/api/orders
```
DB backup: cron `09e30595d19d` (02:00 IST daily) → `/opt/data/backups/burgerlab`, 14-day retention,
script `/opt/data/scripts/burgerlab_pg_backup.sh`.

## Monitoring (do not weaken)
- The group poster is watched by two layers — `scripts/keepalive_group_bot.py` (heals
  sender :8631 + scheduler, writes `data/watchdog.heartbeat.json`) and
  `scripts/watchdog_guard.py` (alerts and revives the watchdog). Contract, cron IDs and
  test commands: `cron/README.md`.
- Never identify a process with `pgrep -f "group_scheduler.py run"` — Food Court runs the
  same script name. Use the flock in `data/group_scheduler.lock` plus cmdline **and** cwd.
- Cron entry points must exist in `/opt/data/scripts/` (that is where Hermes resolves
  `no_agent` scripts); the logic stays in this repo behind a thin wrapper.
- A heal that is not verified (process still alive after the settle window) is not a heal.

