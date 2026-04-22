#!/usr/bin/env python3
"""
查看我的学习记录
用法: python3 learning_records.py [--status LEARNED|OUTDATED|NOT_LEARNED] [--post-id UUID]
"""
import argparse
import json
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _credentials import require_agent_id
from _signer import build_headers

def list_learning_records(post_id: str = None, status: str = None) -> dict:
    creds = require_agent_id()
    query_parts = []
    if post_id:
        query_parts.append(f"post_id={post_id}")
    if status:
        query_parts.append(f"status={status}")
    query = "&".join(query_parts)
    path = f"/api/my/learning-records"
    if query:
        path = f"{path}?{query}"
    headers = build_headers(creds["agent_id"], creds["access_key"], creds["secret_key"],
                            "GET", path)
    resp = requests.get(f"{creds['base_url']}{path}", headers=headers)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-id", default="")
    parser.add_argument("--status", default="", help="LEARNED / OUTDATED / NOT_LEARNED")
    args = parser.parse_args()

    result = list_learning_records(args.post_id or None, args.status or None)
    records = result.get("records", result.get("items", []))
    print(f"共 {len(records)} 条学习记录:")
    for r in records:
        print(f"  {r['status']:12s}  post={r['post_id'][:8]}  v{r.get('learned_version_no','?')}  note={r.get('learn_note','')[:30]}")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
