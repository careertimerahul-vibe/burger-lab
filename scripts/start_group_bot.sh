#!/usr/bin/env bash
# Start (or restart) the WhatsApp group bot for The Burger Lab.
# Idempotent: kills the previous instance via pidfile, then starts a fresh one.
set -u

BASE=/opt/data/projects/burger-lab
DATA=$BASE/data
BRIDGE=/opt/data/scripts/whatsapp-bridge
PIDFILE=$DATA/group_bot.pid
LOG=$DATA/group_bot.out

if [ -f "$PIDFILE" ]; then
  OLD=$(cat "$PIDFILE" 2>/dev/null || true)
  if [ -n "${OLD:-}" ] && kill -0 "$OLD" 2>/dev/null; then
    kill "$OLD" 2>/dev/null || true
    sleep 2
  fi
fi

# Kill any stray listener on the API port (catches orphans with a lost pidfile).
if command -v fuser >/dev/null 2>&1; then
  fuser -k 8631/tcp >/dev/null 2>&1 || true
  sleep 1
fi

cd "$BRIDGE" || exit 1
nohup node wa_group_bot.mjs --session "$DATA/wa-session-8" --port 8631 >> "$LOG" 2>&1 &
echo $! > "$PIDFILE"
sleep 4
if curl -sf -m 5 http://127.0.0.1:8631/health >/dev/null; then
  echo "group bot UP pid=$(cat "$PIDFILE")"
else
  echo "group bot FAILED to start — last log:"
  tail -5 "$LOG"
  exit 1
fi
