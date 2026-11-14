#!/usr/bin/env python3
"""Tests for the meta-guard that watches the watchdog itself.

The 2 Nov–14 Nov failure mode was silent: the cron job pointed at a script that
did not exist and failed 1,675 times without a single alert. The guard exists to
make that impossible — stale heartbeat or an errored job must produce a message.
"""
import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_keepalive import PY, Sandbox, free_port  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(os.path.dirname(HERE), "watchdog_guard.py")
JOB_ID = "be37348ec3a3"


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()
        self.jobs = os.path.join(self.sb.root, "jobs.json")
        self._write_jobs(status="ok", age_s=60)
        self.sb.start_sender()
        self.sb.start_scheduler()

    def tearDown(self):
        self.sb.cleanup()

    def _write_jobs(self, status, age_s, error=None, streak=None):
        payload = [{
            "id": JOB_ID,
            "name": "Burger Lab group bot watchdog",
            "last_status": status,
            "last_error": error,
            "failure_streak": streak,
            "last_run_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00",
                                         time.gmtime(time.time() - age_s)),
        }]
        with open(self.jobs, "w") as f:
            json.dump(payload, f)

    def _write_heartbeat(self, age_s):
        payload = {"ts": time.time() - age_s, "ok": True, "actions": [],
                   "problems": [], "checks": {"scheduler": {"up": True},
                                              "sender": {"up": True}}}
        path = os.path.join(self.sb.base, "data", "watchdog.heartbeat.json")
        with open(path, "w") as f:
            json.dump(payload, f)

    def run_guard(self, extra_env=None):
        env = {
            **os.environ,
            "BL_BASE": self.sb.base,
            "BL_PY": PY,
            "BL_SENDER_URL": "http://127.0.0.1:%d" % self.sb.port,
            "BL_BOT_START": os.path.join(self.sb.base, "scripts/start_group_bot.sh"),
            "BL_WATCHDOG": os.path.join(os.path.dirname(HERE), "keepalive_group_bot.py"),
            "BL_ALERT_DRY": self.sb.alert_file,
            "BL_JOBS": self.jobs,
            "BL_JOB_ID": JOB_ID,
            "BL_RESTART_WAIT_SEC": "10",
            "BL_RESTART_ATTEMPTS": "1",
            "BL_SETTLE_SEC": "1",
            "BL_HEARTBEAT_STALE_SEC": "600",
        }
        env.update(extra_env or {})
        import subprocess
        return subprocess.run([PY, GUARD], env=env, capture_output=True, text=True, timeout=120)

    def test_silent_when_heartbeat_fresh_and_job_ok(self):
        self._write_heartbeat(30)
        res = self.run_guard()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout.strip(), "")
        self.assertEqual(self.sb.alerts(), "")

    def test_alerts_and_revives_when_heartbeat_is_stale(self):
        self._write_heartbeat(3600)
        res = self.run_guard()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("hasn't run", self.sb.alerts())
        self.assertIn("watchdog", res.stdout.lower())
        hb = self.sb.heartbeat()
        self.assertLess(time.time() - hb["ts"], 120, "guard must run the watchdog once")

    def test_alerts_when_the_cron_job_is_erroring(self):
        self._write_heartbeat(30)
        self._write_jobs(status="error", age_s=60,
                         error="Script not found: /opt/data/scripts/keepalive_group_bot.sh")
        res = self.run_guard()
        self.assertEqual(res.returncode, 0, res.stderr)
        alerts = self.sb.alerts()
        self.assertIn("cron job", alerts)
        self.assertIn("Script not found", alerts)

    def test_alerts_when_the_job_has_not_run_recently(self):
        self._write_heartbeat(30)
        self._write_jobs(status="ok", age_s=7200)
        self.run_guard()
        self.assertIn("hasn't run", self.sb.alerts())

    def test_ignores_a_single_transient_job_failure(self):
        """One error that the next tick cleared must not page anyone."""
        self._write_heartbeat(30)
        self._write_jobs(status="error", age_s=30, error="transient", streak=1)
        res = self.run_guard()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.sb.alerts(), "")

    def test_alerts_on_a_repeated_job_failure(self):
        self._write_heartbeat(30)
        self._write_jobs(status="error", age_s=60, error="Script not found: x", streak=4)
        self.run_guard()
        self.assertIn("Script not found", self.sb.alerts())

    def test_missing_heartbeat_counts_as_stale(self):
        res = self.run_guard()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("hasn't run", self.sb.alerts())


if __name__ == "__main__":
    unittest.main(verbosity=2)
