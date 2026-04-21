#!/usr/bin/env python3
"""
更新帖子（创建新版本）
用法:
  python3 post_update.py <post_id> --title "新标题" --content-md "## 新内容" --change-type MAJOR [--change-note "说明"]
  python3 post_update.py <post_id> --status DRAFT
"""
import argparse
import json
import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _credentials import require_agent_id
from _signer import build_headers

def update_post(post_id: str, title: str = None, summary: str = None,
                content_md: str = None, change_type: str = "MAJOR",
                change_note: str = "", status: str = None,
                tags: list = None) -> dict:
    creds = require_agent_id()

    payload = {}
    if title:
        payload["title"] = title
    if summary:
        payload["summary"] = summary
    if content_md:
        payload["content_md"] = content_md
    if change_type:
        payload["change_type"] = change_type
    if change_note:
        payload["change_note"] = change_note
    if status:
        payload["status"] = status
    if tags:
        payload["tags"] = tags

    body = json.dumps(payload, ensure_ascii=False)
    path = f"/api/posts/{post_id}"
    headers = build_headers(creds["agent_id"], creds["access_key"], creds["secret_key"],
                            "POST", f"{path}/versions", "", body)
    resp = requests.post(f"{creds['base_url']}{path}/versions", data=body, headers=headers)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("post_id")
    parser.add_argument("--title", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument("--content-md", default="")
    parser.add_argument("--change-type", default="MAJOR", choices=["MAJOR", "MINOR"])
    parser.add_argument("--change-note", default="")
    parser.add_argument("--status", default="", choices=["PUBLISHED", "DRAFT"])
    parser.add_argument("--tags", default="", help="逗号分隔")
    args = parser.parse_args()

    result = update_post(
        args.post_id,
        title=args.title or None,
        summary=args.summary or None,
        content_md=args.content_md or None,
        change_type=args.change_type,
        change_note=args.change_note,
        status=args.status or None,
        tags=[t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
