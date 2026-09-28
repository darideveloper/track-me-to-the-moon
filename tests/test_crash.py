"""Automated equivalent of manual 5.1 kill-9 pass: SIGKILL mid-drain against a
stub backend, then verify DB integrity and no dupes/partial marks on restart."""
import json
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from moon_tracker import store

STUB_DELAY = 0.1
ROOT = Path(__file__).resolve().parent.parent

CHILD = r"""
import sys
from pathlib import Path
from moon_tracker import store, sync
db, base = sys.argv[1], sys.argv[2]
con = store.connect(Path(db))
store.set_setting(con, "api_base", base)
store.set_setting(con, "api_token", "t")
store.set_setting(con, "user_id", "u")
import time
for _ in range(60):
    sync.drain(con, {}, reason="tick", notify_fn=lambda *a: False)
    if sum(store.pending_counts(con).values()) == 0:
        break
    time.sleep(0.05)
"""

SEEN: list = []


class _Handler(BaseHTTPRequestHandler):
    def _ack(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw or b"{}")
            ids = [r.get("client_id", "") for r in body.get("items", [])]
        except Exception:
            ids = []  # e.g. multipart screenshot: all-or-nothing ack
        time.sleep(STUB_DELAY)
        payload = json.dumps({"ok": True, "accepted": ids}).encode()
        if not ids:
            payload = json.dumps({"ok": True}).encode()
        else:
            SEEN.extend(ids)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_POST = _ack

    def log_message(self, *a):
        pass


def _serve():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_kill9_mid_drain_no_dupes(tmp_path):
    db = tmp_path / "crash.db"
    con = store.connect(db)
    sid = store.start_session(con, "2026-01-01T00:00:00+00:00")
    for i in range(500):
        store.add_activity(con, sid, f"2026-01-01T00:00:{i % 60:02d}+00:00", "A", f"t{i}", 0)
    con.close()

    server = _serve()
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(db), f"http://127.0.0.1:{server.server_port}"],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        # Wait until drain is provably in-flight (some marked, some pending).
        deadline = time.time() + 20
        while time.time() < deadline:
            time.sleep(0.1)
            c = sqlite3.connect(str(db))
            try:
                marked = c.execute("SELECT COUNT(*) FROM activities WHERE uploaded=1").fetchone()[0]
                pending = c.execute("SELECT COUNT(*) FROM activities WHERE uploaded=0").fetchone()[0]
            finally:
                c.close()
            if 0 < marked < 500 and pending > 0:
                break
        else:
            raise AssertionError("drain never reached in-flight state")
        child.send_signal(signal.SIGKILL)
        child.wait(timeout=10)
    finally:
        server.server_close()
    assert child.returncode == -signal.SIGKILL

    # Restart: integrity + exact accounting (no dupes, no partial marks).
    # NOTE: the killed run may have zero ledger rows (SIGKILL can land before
    # the end-of-drain insert) — the ledger is best-effort, the outbox is not.
    c = sqlite3.connect(str(db))
    try:
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        marked = c.execute("SELECT COUNT(*) FROM activities WHERE uploaded=1").fetchone()[0]
        pending = c.execute("SELECT COUNT(*) FROM activities WHERE uploaded=0").fetchone()[0]
        assert marked + pending == 500
        assert c.execute(
            "SELECT COUNT(*) FROM activities WHERE uploaded=1 AND uploaded_at IS NULL"
        ).fetchone()[0] == 0
    finally:
        c.close()

    # Resume to completion: nothing lost. Redelivery after kill is safe because
    # every payload carries a stable client_id the backend dedupes on
    # (at-least-once delivery, exactly-once effect). SEEN keeps pre-kill sends,
    # so the union must cover all rows.
    server2 = _serve()
    try:
        from moon_tracker import sync

        con2 = store.connect(db)
        store.set_setting(con2, "api_base", f"http://127.0.0.1:{server2.server_port}")
        for _ in range(30):
            sync.drain(con2, {}, reason="resume", notify_fn=lambda *a: False)
            if sum(store.pending_counts(con2).values()) == 0:
                break
        assert sum(store.pending_counts(con2).values()) == 0
        assert con2.execute("SELECT COUNT(*) FROM sync_runs").fetchone()[0] >= 1
        con2.close()
    finally:
        server2.server_close()
    assert len({i for i in SEEN if i.startswith("activity:")}) == 500  # full coverage
    assert {i for i in SEEN if i.startswith("activity:")} == {
        f"activity:{i}" for i in range(1, 501)}  # stable ids, safe redelivery
