"""TokenHarbor Suite - 9router Integration.

TokenHarbor adalah first-class built-in provider di 9router dengan ID 'tokenharbor'.
Modul ini menambahkan koneksi akun dan API key ke 9router via REST API atau SQLite fallback.
"""
import json
import os
import re
import sqlite3
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from .config import NINE_ROUTER_URL, NINE_ROUTER_PASS

DEFAULT_BASE = "http://127.0.0.1:20127"
SQLITE_DB = os.path.expanduser("~/.9router/db/data.sqlite")


def _base() -> str:
    b = NINE_ROUTER_URL or DEFAULT_BASE
    m = re.match(r"(https?://[^/]+)", b)
    return m.group(1) if m else DEFAULT_BASE


def login(base: str = None) -> Optional[str]:
    """Login ke 9router, return cookie 'auth_token=...'."""
    base = base or _base()
    try:
        req = urllib.request.Request(
            f"{base}/api/auth/login",
            data=json.dumps({"password": NINE_ROUTER_PASS}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            sc = resp.headers.get("Set-Cookie") or ""
            for part in sc.split(";"):
                if "auth_token=" in part:
                    return part.strip()
    except Exception:
        return None
    return None


def sync_connection(api_key: str, email: str, base: str = None) -> bool:
    """Sinkronkan koneksi TokenHarbor ke 9router."""
    cookie = login(base)
    base = base or _base()

    if cookie:
        try:
            req = urllib.request.Request(
                f"{base}/api/providers",
                data=json.dumps({
                    "provider": "tokenharbor",
                    "apiKey": api_key,
                    "name": f"tokenharbor {email.split('@')[0][:12]}",
                    "priority": 1
                }).encode(),
                headers={"Cookie": cookie, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    return True
        except Exception:
            pass

    # Fallback to direct SQLite injection
    if os.path.exists(SQLITE_DB):
        try:
            conn = sqlite3.connect(SQLITE_DB)
            cur = conn.cursor()
            cur.execute("SELECT id FROM providerConnections WHERE provider='tokenharbor' AND email=?", (email,))
            row = cur.fetchone()

            now = datetime.now(timezone.utc).isoformat()
            conn_data = json.dumps({
                "apiKey": api_key,
                "defaultModel": "mimo-v2.6-flash:free",
                "testStatus": "active",
                "lastError": None,
                "lastErrorAt": None,
                "errorCode": None,
                "rateLimitedUntil": None,
                "backoffLevel": 0
            })

            if row:
                cur.execute("UPDATE providerConnections SET data=?, isActive=1, updatedAt=? WHERE id=?",
                            (conn_data, now, row[0]))
            else:
                conn_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt) VALUES (?, 'tokenharbor', 'api_key', ?, ?, 0, 1, ?, ?, ?)",
                    (conn_id, f"tokenharbor {email.split('@')[0][:12]}", email, conn_data, now, now)
                )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    return False
