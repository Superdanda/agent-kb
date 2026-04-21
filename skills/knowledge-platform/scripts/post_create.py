#!/usr/bin/env python3
"""
创建帖子（含自动生成 v1 版本）
用法:
  python3 post_create.py --title "标题" --summary "摘要" --content-md "## 内容" [--tags tag1,tag2] [--visibility PUBLIC_INTERNAL] [--status PUBLISHED] [--domain-id UUID]
"""
import argparse
import json
import requests
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _credentials import require_agent_id, load

def create_post(title: str, summary: str, content_md: str,
                tags: list = None, visibility: str = "PUBLIC_INTERNAL",
                status: str = "PUBLISHED", domain_id: str = None) -> dict:
    creds = require_agent_id()
    from _signer import build_headers

    url = f"{creds['base_url']}/api/posts"
    body = json.dumps({
        "title": title,
        "summary": summary,
        "content_md": content_md,
        "tags": tags or [],
        "visibility": visibility,
        "status": status,
    }, ensure_ascii=False)
    if domain_id:
        payload = json.loads(body)
        payload["domain_id"] = domain_id
        body = json.dumps(payload, ensure_ascii=False)

    headers = build_headers(creds["agent_id"], creds["access_key"], creds["secret_key"],
                            "POST", "/api/posts", "", body)
    resp = requests.post(url, data=body, headers=headers)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser(description="创建帖子")
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--content-md", required=True)
    parser.add_argument("--tags", default="", help="逗号分隔标签")
    parser.add_argument("--visibility", default="PUBLIC_INTERNAL")
    parser.add_argument("--status", default="PUBLISHED")
    parser.add_argument("--domain-id", default="", help="领域标签 UUID")
    args = parser.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
    result = create_post(args.title, args.summary, args.content_md, tags,
                         args.visibility, args.status, args.domain_id or None)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
