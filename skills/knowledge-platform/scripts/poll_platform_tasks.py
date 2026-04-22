#!/usr/bin/env python3
"""Platform task polling + claim script for Hermes Agent cron job.

Usage:
    PLATFORM_AGENT_ID=xxx PLATFORM_ACCESS_KEY=xxx PLATFORM_SECRET_KEY=xxx \
        PLATFORM_API_BASE=http://localhost:18000 python3 poll_platform_tasks.py

Outputs JSON for easy parsing by cron or logging systems.
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
import urllib.parse


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


def poll_tasks(api_base: str, agent_id: str, access_key: str, secret_key: str) -> dict:
    """Fetch pending tasks from the platform."""
    path = "/api/agent/tasks/pending?status_filter=PENDING,UNCLAIMED&limit=10"
    headers = generate_auth_headers(
        agent_id, access_key, secret_key, "GET", path
    )
    headers["Content-Type"] = "application/json"

    try:
        req = urllib.request.Request(
            api_base + path, method="GET", headers=headers
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"ok": True, "data": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"URLError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def claim_task(
    api_base: str, agent_id: str, access_key: str, secret_key: str, task_id: str
) -> dict:
    """Claim a task by ID."""
    path = f"/api/agent/tasks/{task_id}/claim"
    headers = generate_auth_headers(
        agent_id, access_key, secret_key, "POST", path
    )
    headers["Content-Type"] = "application/json"

    try:
        req = urllib.request.Request(
            api_base + path, method="POST", headers=headers
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"ok": True, "data": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"URLError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def submit_task(
    api_base: str,
    agent_id: str,
    access_key: str,
    secret_key: str,
    task_id: str,
    result_summary: str,
) -> dict:
    """Submit task result."""
    encoded_summary = urllib.parse.quote(result_summary)
    path = f"/api/agent/tasks/{task_id}/submit?result_summary={encoded_summary}"
    query = f"result_summary={result_summary}"
    headers = generate_auth_headers(
        agent_id, access_key, secret_key, "POST", path, query=query
    )
    headers["Content-Type"] = "application/json"

    try:
        req = urllib.request.Request(
            api_base + path, method="POST", headers=headers
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"ok": True, "data": json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"URLError: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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

    result = poll_tasks(api_base, agent_id, access_key, secret_key)
    if not result.get("ok"):
        print(json.dumps({"wakeAgent": False, "error": result.get("error")}))
        return

    data = result["data"]
    tasks = data.get("tasks", [])
    count = data.get("count", 0)

    if count == 0:
        print(json.dumps({"wakeAgent": False, "message": "No pending tasks"}))
        return

    print(
        json.dumps(
            {
                "wakeAgent": True,
                "task_count": count,
                "tasks": [
                    {
                        "id": t["id"],
                        "title": t.get("title"),
                        "priority": t.get("priority"),
                        "status": t.get("status"),
                        "deadline": t.get("deadline"),
                    }
                    for t in tasks
                ],
            }
        )
    )

    for task in tasks:
        claim_result = claim_task(
            api_base, agent_id, access_key, secret_key, task["id"]
        )
        if claim_result.get("ok"):
            print(
                json.dumps(
                    {
                        "claimed": task["id"],
                        "title": task.get("title"),
                        "status": "IN_PROGRESS",
                    }
                )
            )
        else:
            print(
                json.dumps(
                    {
                        "claim_failed": task["id"],
                        "error": claim_result.get("error"),
                    }
                )
            )


if __name__ == "__main__":
    main()
