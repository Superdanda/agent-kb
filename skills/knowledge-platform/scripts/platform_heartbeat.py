#!/usr/bin/env python3
"""Platform heartbeat script for Hermes Agent cron job.

Usage:
    PLATFORM_AGENT_ID=xxx PLATFORM_ACCESS_KEY=xxx PLATFORM_SECRET_KEY=xxx \
        PLATFORM_API_BASE=http://localhost:18000 python3 platform_heartbeat.py

Outputs JSON for easy parsing by cron or logging systems:
    {"wakeAgent": true, "pending_tasks": 3, "agent_code": "...", ...}
    {"wakeAgent": false, "error": "..."}
"""

import os
import hmac
import hashlib
import time
import random
import string
import json
import urllib.request
import urllib.error


def generate_auth_headers(
    agent_id: str,
    access_key: str,
    secret_key: str,
    method: str,
    path: str,
    query: str = "",
    body: str = "",
) -> dict:
    """Generate HMAC-SHA256 authentication headers.

    If path contains a query string (e.g. '/path?foo=bar'), it is automatically
    split into path and query components.
    """
    if "?" in path and not query:
        path, query = path.split("?", 1)

    timestamp = str(int(time.time()))
    nonce = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    content_sha256 = (
        hashlib.sha256(body.encode()).hexdigest()
        if body
        else "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )

    string_to_sign = (
        f"{method}\n{path}\n{query}\n{timestamp}\n{nonce}\n{content_sha256}"
    )
    signature = hmac.new(
        secret_key.encode(),
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()

    return {
        "x-agent-id": agent_id,
        "x-access-key": access_key,
        "x-timestamp": timestamp,
        "x-nonce": nonce,
        "x-content-sha256": content_sha256,
        "x-signature": signature,
    }


def main():
    api_base = os.environ.get("PLATFORM_API_BASE", "http://localhost:18000")
    agent_id = os.environ.get("PLATFORM_AGENT_ID", "")
    access_key = os.environ.get("PLATFORM_ACCESS_KEY", "")
    secret_key = os.environ.get("PLATFORM_SECRET_KEY", "")

    if not agent_id or not access_key or not secret_key:
        print(
            json.dumps(
                {
                    "wakeAgent": False,
                    "error": "Missing PLATFORM_AGENT_ID, PLATFORM_ACCESS_KEY, or PLATFORM_SECRET_KEY",
                }
            )
        )
        return

    path = "/api/agent/heartbeat"
    headers = generate_auth_headers(
        agent_id, access_key, secret_key, "POST", path
    )
    headers["Content-Type"] = "application/json"

    try:
        req = urllib.request.Request(
            api_base + path, method="POST", headers=headers
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            pending = data.get("pending_tasks", 0)
            print(
                json.dumps(
                    {
                        "wakeAgent": pending > 0,
                        "pending_tasks": pending,
                        "agent_code": data.get("agent_code"),
                        "last_seen_at": data.get("last_seen_at"),
                        "server_time": data.get("server_time"),
                    }
                )
            )
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        print(json.dumps({"wakeAgent": False, "error": f"HTTP {e.code}: {body}"}))
    except urllib.error.URLError as e:
        print(json.dumps({"wakeAgent": False, "error": f"URLError: {e}"}))
    except Exception as e:
        print(json.dumps({"wakeAgent": False, "error": str(e)}))


if __name__ == "__main__":
    main()
