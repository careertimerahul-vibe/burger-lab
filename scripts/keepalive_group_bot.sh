#!/usr/bin/env bash
# Shim: the watchdog logic lives in keepalive_group_bot.py (tested by
# scripts/tests/test_keepalive.py). Kept as .sh so existing callers and the
# Hermes cron job keep working unchanged.
set -u
BASE="$(cd "$(dirname "$0")/.." && pwd)"
PY="${BL_PY:-/opt/data/venvs/crypto/bin/python}"
exec "$PY" "$BASE/scripts/keepalive_group_bot.py" "$@"
