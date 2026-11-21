"""
Burger Lab POS API — PostgreSQL backend with REST API
"""
import json, os, psycopg2, psycopg2.extras
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Local cluster (port 5433) owned by this app; override with DB_URL in the environment.
DB_URL = os.environ.get("DB_URL", "host=127.0.0.1 port=5433 dbname=burgerlab_pos user=burgerlab password=burgerlab_pos_2024")
API_KEY = os.environ.get("API_KEY", "burgerlab_pos_2024")
# Served under a path prefix when the tunnel routes e.g. /burgerlab-api/* here.
BASE_PATH = os.environ.get("BASE_PATH", "")


def api_path(raw):
    p = urlparse(raw).path
    if BASE_PATH and p.startswith(BASE_PATH):
        p = p[len(BASE_PATH):] or "/"
    return p

def get_db():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    return conn

class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _check_auth(self):
        return self.headers.get("Authorization", "") == f"Bearer {API_KEY}"

    def do_OPTIONS(self):
        self._send_json({})

    def do_GET(self):
        if not self._check_auth():
            self._send_json({"error": "unauthorized"}, 401)
            return
        path = api_path(self.path)
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if path == "/api/orders":
            params = parse_qs(urlparse(self.path).query)
            from_date = params.get("from", [None])[0]
            to_date = params.get("to", [None])[0]
            limit = int(params.get("limit", [200])[0])

            query = "SELECT * FROM orders"
            conditions = []
            vals = []
            if from_date:
                conditions.append("timestamp >= %s")
                vals.append(from_date)
            if to_date:
                conditions.append("timestamp <= %s")
                vals.append(to_date + "T23:59:59")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY id DESC LIMIT %s"
            vals.append(limit)

            cur.execute(query, vals)
            self._send_json(cur.fetchall())

        elif path == "/api/visits":
            params = parse_qs(urlparse(self.path).query)
            days = int(params.get("days", [30])[0])
            cur.execute(
                "SELECT ts, path, source, content, ref FROM visits "
                "WHERE ts >= now() - (%s || ' days')::interval ORDER BY ts DESC",
                (days,)
            )
            self._send_json(cur.fetchall())

        elif path == "/api/costs":
            cur.execute("SELECT * FROM costs ORDER BY menuKey")
            self._send_json(cur.fetchall())

        else:
            self._send_json({"error": "not found"}, 404)
        cur.close(); conn.close()

    def do_POST(self):
        if not self._check_auth():
            self._send_json({"error": "unauthorized"}, 401)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}
        path = api_path(self.path)
        conn = get_db()
        cur = conn.cursor()

        if path == "/api/orders":
            cur.execute(
                "INSERT INTO orders (timestamp, items, totalSell, totalCost, totalProfit, margin, source, delivery, spice) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (body.get("timestamp", ""), json.dumps(body.get("items", [])),
                 body.get("totalSell", 0), body.get("totalCost", 0),
                 body.get("totalProfit", 0), body.get("margin", 0),
                 body.get("source", "manual"), json.dumps(body.get("delivery", {})),
                 body.get("spice", ""))
            )
            new_id = cur.fetchone()[0]
            self._send_json({"id": new_id, "status": "created"}, 201)

        elif path == "/api/visit":
            # Menu-open tracking: the group posts carry ?utm_source=<group>&utm_content=<slot>,
            # so one row per page load answers "is anyone opening the menu, from where, when".
            # Nothing else on the site reported this, so orders alone could not tell a quiet
            # night from an untracked one.
            cur.execute(
                "INSERT INTO visits (path, source, content, ref, ua) VALUES (%s,%s,%s,%s,%s)",
                ((body.get("path") or "/")[:300], (body.get("source") or "")[:40],
                 (body.get("content") or "")[:20], (body.get("ref") or "")[:300],
                 (body.get("ua") or "")[:200])
            )
            self._send_json({"status": "logged"}, 201)

        elif path == "/api/costs":
            menuKey = body.get("menuKey")
            cur.execute("SELECT id FROM costs WHERE menuKey = %s", (menuKey,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE costs SET sellPrice=%s, costPrice=%s, ingredients=%s WHERE menuKey=%s",
                    (body.get("sellPrice", 0), body.get("costPrice", 0), json.dumps(body.get("ingredients", [])), menuKey)
                )
            else:
                cur.execute(
                    "INSERT INTO costs (menuKey, sellPrice, costPrice, ingredients) VALUES (%s,%s,%s,%s)",
                    (menuKey, body.get("sellPrice", 0), body.get("costPrice", 0), json.dumps(body.get("ingredients", [])))
                )
            self._send_json({"status": "saved"})

        else:
            self._send_json({"error": "not found"}, 404)
        cur.close(); conn.close()

    def do_DELETE(self):
        if not self._check_auth():
            self._send_json({"error": "unauthorized"}, 401)
            return
        path = api_path(self.path)
        conn = get_db()
        cur = conn.cursor()

        if path.startswith("/api/orders/"):
            order_id = int(path.split("/")[-1])
            cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))
            self._send_json({"status": "deleted"})
        else:
            self._send_json({"error": "not found"}, 404)
        cur.close(); conn.close()

    def log_message(self, format, *args):
        pass

def init_db():
    """Create the visits table on boot so a fresh cluster needs no manual migration."""
    conn = get_db(); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS visits (
        id serial PRIMARY KEY,
        ts timestamptz NOT NULL DEFAULT now(),
        path text, source text, content text, ref text, ua text)""")
    cur.execute("CREATE INDEX IF NOT EXISTS visits_ts_idx ON visits (ts)")
    cur.close(); conn.close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8901))
    init_db()
    server = HTTPServer(("0.0.0.0", port), APIHandler)
    print(f"Burger Lab POS API running on port {port}")
    server.serve_forever()
