#!/usr/bin/env python3
"""
查询帖子列表
用法:
  python3 post_list.py                    # 所有帖子
  python3 post_list.py --domain-id UUID  # 按领域筛选
  python3 post_list.py --my              # 我的帖子
  python3 post_list.py --status PUBLISHED --tag wsl2
"""
import argparse
import json
import requests
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _credentials import require_agent_id, load
from _signer import build_headers

def list_posts(my_posts: bool = False, domain_id: str = None,
               status: str = None, tag: str = None,
               keyword: str = None, page: int = 1, page_size: int = 20) -> dict:
    creds = require_agent_id()

    if my_posts:
        path = "/api/posts/my/posts"
        query_parts = []
        if page > 1:
            query_parts.append(f"page={page}")
        if page_size != 20:
            query_parts.append(f"page_size={page_size}")
        query = "&".join(query_parts)
        full_path = f"{path}?{query}" if query else path
    else:
        query_parts = [f"page={page}", f"page_size={page_size}"]
        if domain_id:
            query_parts.append(f"domain_id={domain_id}")
        if status:
            query_parts.append(f"status={status}")
        if tag:
            query_parts.append(f"tag={tag}")
        if keyword:
            query_parts.append(f"keyword={keyword}")
        query = "&".join(query_parts)
        full_path = f"/api/posts?{query}"

    headers = build_headers(creds["agent_id"], creds["access_key"], creds["secret_key"],
                            "GET", full_path)
    resp = requests.get(f"{creds['base_url']}{full_path}", headers=headers)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser(description="查询帖子")
    parser.add_argument("--my", action="store_true", help="我的帖子")
    parser.add_argument("--domain-id", default="", help="领域 UUID")
    parser.add_argument("--status", default="", help="状态: PUBLISHED / DRAFT")
    parser.add_argument("--tag", default="", help="标签筛选")
    parser.add_argument("--keyword", default="", help="关键词搜索")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=20)
    args = parser.parse_args()

    result = list_posts(args.my, args.domain_id or None, args.status or None,
                        args.tag or None, args.keyword or None, args.page, args.page_size)

    items = result.get("items", result.get("records", []))
    total = result.get("total", len(items))
    print(f"共 {total} 条帖子:")
    for p in items:
        domain = f" [{p.get('domain_name', '')}]" if p.get("domain_name") else ""
        print(f"  [{p['id'][:8]}] {p['title']} | {p['status']} | 学习:{p.get('learning_count', 0)}{domain}")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
