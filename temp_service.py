#!/usr/bin/env python3
"""
ThermalWatch - Temperature Monitor Service
Reads CPU temperature every 30 seconds, stores in SQLite, serves a web dashboard.
Designed for Raspberry Pi 4B running Raspberry Pi OS.
"""

import sqlite3
import time
import os
import json
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
DB_PATH = Path("/var/lib/tempmonitor/temps.db")
PORT = 8765
READ_INTERVAL = 30  # seconds

# ── Database Setup ─────────────────────────────────────────────────────────────
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      INTEGER NOT NULL,
            temp_c  REAL    NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON readings(ts)")
    conn.commit()
    conn.close()

# ── Temperature Reading ────────────────────────────────────────────────────────
def read_cpu_temp() -> float:
    """Read CPU temperature from the Pi thermal zone."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000.0, 2)
    except Exception:
        # Fallback: try vcgencmd
        try:
            import subprocess
            out = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
            return float(out.replace("temp=", "").replace("'C\n", ""))
        except Exception:
            return -1.0

def record_loop():
    """Background thread: take a reading every READ_INTERVAL seconds."""
    print(f"[tempmonitor] Recording loop started (every {READ_INTERVAL}s)")
    while True:
        temp = read_cpu_temp()
        ts = int(time.time())
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO readings (ts, temp_c) VALUES (?, ?)", (ts, temp))
            conn.commit()
            conn.close()
            print(f"[tempmonitor] {datetime.fromtimestamp(ts).isoformat()} → {temp}°C")
        except Exception as e:
            print(f"[tempmonitor] DB write error: {e}")
        time.sleep(READ_INTERVAL)

# ── Data Queries ───────────────────────────────────────────────────────────────
def query_stats(hours_back: int):
    """Return per-bucket stats: {ts, min, avg, max}"""
    since = int(time.time()) - hours_back * 3600
    conn = sqlite3.connect(DB_PATH)
    # Bucket by 5 minutes for 24h, by 1 hour for 7 weeks
    bucket_secs = 300 if hours_back <= 24 else 3600
    rows = conn.execute("""
        SELECT
            (ts / ?) * ? AS bucket,
            MIN(temp_c)  AS t_min,
            AVG(temp_c)  AS t_avg,
            MAX(temp_c)  AS t_max
        FROM readings
        WHERE ts >= ?
        GROUP BY bucket
        ORDER BY bucket
    """, (bucket_secs, bucket_secs, since)).fetchall()
    conn.close()
    return [
        {"ts": r[0], "min": round(r[1], 2), "avg": round(r[2], 2), "max": round(r[3], 2)}
        for r in rows
    ]

def query_current():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT ts, temp_c FROM readings ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return {"ts": row[0], "temp_c": row[1]}
    return {"ts": 0, "temp_c": read_cpu_temp()}

def query_total_readings():
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    oldest = conn.execute("SELECT MIN(ts) FROM readings").fetchone()[0]
    conn.close()
    return count, oldest

# ── Web Dashboard (embedded HTML) ─────────────────────────────────────────────
DASHBOARD_HTML = open(Path(__file__).parent / "dashboard.html").read()

# ── HTTP Handler ───────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence default logs

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/":
            body = DASHBOARD_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/current":
            self.send_json(query_current())

        elif path == "/api/24h":
            self.send_json(query_stats(24))

        elif path == "/api/7w":
            self.send_json(query_stats(7 * 24))

        elif path == "/api/info":
            count, oldest = query_total_readings()
            self.send_json({
                "total_readings": count,
                "oldest_ts": oldest,
                "db_path": str(DB_PATH),
                "interval_seconds": READ_INTERVAL,
            })

        else:
            self.send_json({"error": "not found"}, 404)


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()

    # Start background recorder
    t = threading.Thread(target=record_loop, daemon=True)
    t.start()

    # Start HTTP server
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[tempmonitor] Dashboard → http://0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[tempmonitor] Stopped.")
