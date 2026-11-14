#!/usr/bin/env python3
"""Tests for the Burger Lab group-poster watchdog (scripts/keepalive_group_bot.py).

Each test builds a throwaway project tree, runs the watchdog as a subprocess and
asserts on real process state — no mocking of the watchdog's own logic.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
WATCHDOG = os.path.join(os.path.dirname(HERE), "keepalive_group_bot.py")
PY = sys.executable

SCHED_STUB = textwrap.dedent(
    """
    import fcntl, os, sys, time
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lock = open(os.path.join(base, "data", "group_scheduler.lock"), "a+")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        sys.exit(9)
    lock.seek(0); lock.truncate(); lock.write(str(os.getpid())); lock.flush()
    print("stub scheduler up", flush=True)
    while True:
        time.sleep(1)
    """
)

BOT_STUB = textwrap.dedent(
    """
    #!/usr/bin/env bash
    set -u
    BASE="$(cd "$(dirname "$0")/.." && pwd)"
    PORT="$(cat "$BASE/data/stub_port.txt")"
    nohup "__PY__" "$BASE/scripts/health_server.py" "$PORT" >> "$BASE/data/bot.out" 2>&1 &
    echo $! > "$BASE/data/bot.pid"
    sleep 1
    """.replace("__PY__", PY).lstrip()
)

HEALTH_STUB = textwrap.dedent(
    """
    import http.server, json, sys
    port = int(sys.argv[1])
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"ok": True, "connected": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *a):
            pass
    http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
    """
)


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Sandbox:
    def __init__(self, scheduler=bool(SCHED_STUB), bot=BOT_STUB):
        self.root = tempfile.mkdtemp(prefix="bl-watchdog-")
        self.base = os.path.join(self.root, "burger-lab")
        for d in ("data", "scripts"):
            os.makedirs(os.path.join(self.base, d), exist_ok=True)
        self.port = free_port()
        self.alert_file = os.path.join(self.root, "alerts.txt")
        self.procs = []
        self._write(self.base + "/scripts/group_scheduler.py", SCHED_STUB)
        self._write(self.base + "/scripts/health_server.py", HEALTH_STUB)
        self._write(self.base + "/scripts/start_group_bot.sh", BOT_STUB, mode=0o755)
        self._write(self.base + "/data/stub_port.txt", str(self.port))

    def _write(self, path, content, mode=0o644):
        with open(path, "w") as f:
            f.write(content)
        os.chmod(path, mode)

    def start_scheduler(self, cwd=None):
        """Start the stub scheduler; returns the Popen."""
        cwd = cwd or self.base
        p = subprocess.Popen(
            [PY, os.path.join(cwd, "scripts/group_scheduler.py"), "run"],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.procs.append(p)
        self._wait_for(os.path.join(cwd, "data", "group_scheduler.lock"), 5)
        return p

    def start_decoy_scheduler(self):
        """Same relative cmdline, but cwd is an unrelated project."""
        other = os.path.join(self.root, "other-project")
        for d in ("data", "scripts"):
            os.makedirs(os.path.join(other, d), exist_ok=True)
        self._write(os.path.join(other, "scripts/group_scheduler.py"), SCHED_STUB)
        return self.start_scheduler(cwd=other), other

    def start_sender(self):
        subprocess.run([os.path.join(self.base, "scripts/start_group_bot.sh")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        self._wait_for_port(self.port, 5)

    def _wait_for(self, path, timeout):
        end = time.time() + timeout
        while time.time() < end:
            if os.path.exists(path) and os.path.getsize(path):
                return True
            time.sleep(0.05)
        return False

    def _wait_for_port(self, port, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                    return True
            except OSError:
                time.sleep(0.05)
        return False

    def run_watchdog(self, extra_env=None, timeout=60):
        env = {
            **os.environ,
            "BL_BASE": self.base,
            "BL_PY": PY,
            "BL_SENDER_URL": "http://127.0.0.1:%d" % self.port,
            "BL_BOT_START": os.path.join(self.base, "scripts/start_group_bot.sh"),
            "BL_ALERT_DRY": self.alert_file,
            "BL_RESTART_WAIT_SEC": "10",
            "BL_RESTART_ATTEMPTS": "1",
            "BL_SETTLE_SEC": "1",
        }
        env.update(extra_env or {})
        return subprocess.run([PY, WATCHDOG], env=env, capture_output=True, text=True,
                              timeout=timeout)

    def heartbeat(self):
        with open(os.path.join(self.base, "data", "watchdog.heartbeat.json")) as f:
            return json.load(f)

    def alerts(self):
        if not os.path.exists(self.alert_file):
            return ""
        with open(self.alert_file) as f:
            return f.read()

    def live_scheduler_pid(self):
        lock = os.path.join(self.base, "data", "group_scheduler.lock")
        if not os.path.exists(lock):
            return None
        pid = int(open(lock).read().strip() or 0)
        if pid and os.path.exists("/proc/%d" % pid):
            return pid
        return None

    def cleanup(self):
        for p in self.procs:
            p.kill()
        pidfile = os.path.join(self.base, "data", "bot.pid")
        if os.path.exists(pidfile):
            try:
                with open(pidfile) as f:
                    os.kill(int(f.read().strip()), 9)
            except (ValueError, OSError):
                pass
        # Anything the watchdog spawned lives with cwd inside this sandbox.
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                cwd = os.readlink("/proc/%s/cwd" % entry)
            except OSError:
                continue
            if cwd.startswith(self.root):
                try:
                    os.kill(int(entry), 9)
                except OSError:
                    pass
        shutil.rmtree(self.root, ignore_errors=True)


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox()

    def tearDown(self):
        self.sb.cleanup()

    def test_silent_when_everything_is_healthy(self):
        self.sb.start_scheduler()
        self.sb.start_sender()
        res = self.sb.run_watchdog()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout.strip(), "", "healthy run must print nothing")
        self.assertEqual(self.sb.alerts(), "", "healthy run must not alert")
        hb = self.sb.heartbeat()
        self.assertTrue(hb["ok"])
        self.assertEqual(hb["actions"], [])

    def test_starts_scheduler_when_it_is_down(self):
        self.sb.start_sender()
        self.assertIsNone(self.sb.live_scheduler_pid())
        res = self.sb.run_watchdog()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("scheduler", res.stdout.lower())
        self.assertIsNotNone(self.sb.live_scheduler_pid(), "scheduler must be running after heal")
        self.assertEqual(self.sb.alerts(), "")
        self.assertTrue(self.sb.heartbeat()["ok"])

    def test_ignores_decoy_scheduler_from_another_project(self):
        """The old pgrep check passed on Food Court's scheduler. That must not count."""
        decoy, _ = self.sb.start_decoy_scheduler()
        self.sb.start_sender()
        self.assertIsNone(self.sb.live_scheduler_pid())
        res = self.sb.run_watchdog()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIsNotNone(self.sb.live_scheduler_pid(),
                             "our own scheduler must be started despite the decoy")
        self.assertTrue(decoy.poll() is None, "decoy must be left alone")

    def test_starts_sender_when_health_is_down(self):
        self.sb.start_scheduler()
        res = self.sb.run_watchdog()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("sender", res.stdout.lower())
        self.assertTrue(self.sb._wait_for_port(self.sb.port, 3), "sender must be listening after heal")
        self.assertEqual(self.sb.alerts(), "")

    def test_alerts_and_fails_when_scheduler_cannot_be_healed(self):
        # A scheduler that dies immediately: restart attempts cannot succeed.
        self.sb._write(self.sb.base + "/scripts/group_scheduler.py", "import sys; sys.exit(1)")
        self.sb.start_sender()
        res = self.sb.run_watchdog()
        self.assertEqual(res.returncode, 1, "unhealable state must exit non-zero")
        self.assertIn("scheduler", res.stdout.lower())
        self.assertIn("scheduler is down", self.sb.alerts())
        self.assertFalse(self.sb.heartbeat()["ok"])

    def test_alerts_once_per_window_when_flapping(self):
        self.sb._write(self.sb.base + "/scripts/group_scheduler.py", "import sys; sys.exit(1)")
        self.sb.start_sender()
        for _ in range(3):
            self.sb.run_watchdog()
        alerts = self.sb.alerts()
        self.assertEqual(alerts.count("scheduler is down"), 1,
                         "repeated failures inside the alert window must not spam:\n" + alerts)

    def test_heartbeat_is_fresh_and_names_checks(self):
        self.sb.start_scheduler()
        self.sb.start_sender()
        before = time.time()
        self.sb.run_watchdog()
        hb = self.sb.heartbeat()
        self.assertGreaterEqual(hb["ts"], before - 1)
        self.assertIn("scheduler", hb["checks"])
        self.assertIn("sender", hb["checks"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
