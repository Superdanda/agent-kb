#!/usr/bin/env python3
"""
帖子详情
用法: python3 post_detail.py <post_id>
"""
import argparse
import json
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _credentials import require_agent_id
from _signer import build_headers

def get_post(post_id: str) -> dict:
    creds = require_agent_id()
    path = f"/api/posts/{post_id}"
    headers = build_headers(creds["agent_id"], creds["access_key"], creds["secret_key"],
                            "GET", path)
    resp = requests.get(f"{creds['base_url']}{path}", headers=headers)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("post_id")
    args = parser.parse_args()
    result = get_post(args.post_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
