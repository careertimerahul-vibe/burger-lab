#!/usr/bin/env bash
# Watchdog: restarts the WhatsApp group bot or its scheduler if either is down.
# Silent when healthy (no output = no cron message). Prints only on a restart.
set -u

BASE=/opt/data/projects/burger-lab
PY=/opt/data/venvs/crypto/bin/python
MSG=""

if ! curl -sf -m 6 http://127.0.0.1:8631/health >/dev/null 2>&1; then
  OUT=$("$BASE/scripts/start_group_bot.sh" 2>&1 | tail -1)
  MSG="group bot was down -> $OUT"
fi

if ! pgrep -f "group_scheduler.py run" >/dev/null 2>&1; then
  cd "$BASE" || exit 0
  nohup "$PY" scripts/group_scheduler.py run >> data/group_scheduler.out 2>&1 &
  MSG="${MSG:+$MSG; }scheduler restarted pid=$!"
fi

if [ -n "$MSG" ]; then
  echo "⚠️ Burger Lab group bot: $MSG"
fi
exit 0
