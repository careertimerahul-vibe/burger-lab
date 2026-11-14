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
- Cron docs: /opt/data/projects/burger-lab/cron
- WhatsApp script: /opt/data/projects/burger-lab/scripts/whatsapp_messages.py
- Digital presence docs: README.md and related setup docs in root

## Commands
- Inspect README.md before changing business info.
- For cron/script edits, run the script or a safe dry run where possible.
- Watchdog tests: `python3 -m unittest discover -s scripts/tests -p "test_*.py"`.
- This project may be a separate git repo/submodule; commit from inside the project root if needed.

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

