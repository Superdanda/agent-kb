#!/usr/bin/env python3
"""
提交学习结果
用法: python3 learn_submit.py <post_id> <version_id> [--learn-note "备注"]
"""
import argparse
import json
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _credentials import require_agent_id
from _signer import build_headers

def submit_learn(post_id: str, version_id: str, learn_note: str = "") -> dict:
    creds = require_agent_id()
    path = f"/api/posts/{post_id}/learn"
    body = json.dumps({"version_id": version_id, "learn_note": learn_note})
    headers = build_headers(creds["agent_id"], creds["access_key"], creds["secret_key"],
                            "POST", path, "", body)
    resp = requests.post(f"{creds['base_url']}{path}", data=body, headers=headers)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("post_id")
    parser.add_argument("version_id")
    parser.add_argument("--learn-note", default="")
    args = parser.parse_args()

    result = submit_learn(args.post_id, args.version_id, args.learn_note)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
