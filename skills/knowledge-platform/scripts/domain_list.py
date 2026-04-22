#!/usr/bin/env python3
"""
查询所有领域标签（公开接口，无需认证）
用法: python3 domain_list.py
"""
import argparse
import json
import requests
import sys
import os
from pathlib import Path

def list_domains() -> dict:
    base_url = os.environ.get("KB_BASE_URL", "http://localhost:8000")
    resp = requests.get(f"{base_url}/api/domains")
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser(description="查询所有领域标签（公开）")
    parser.add_argument("--field", choices=["name", "code", "id"], default="name",
                       help="显示哪个字段（默认 name）")
    args = parser.parse_args()

    result = list_domains()
    items = result.get("items", result.get("domains", []))
    print(f"共 {len(items)} 个领域:")
    for d in items:
        print(f"  {d['icon']} {d['name']:10s}  code={d['code']:12s}  id={d['id']}")

    if args.field != "name":
        for d in items:
            val = d.get(args.field, "")
            print(val)
    else:
        # 完整 JSON
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
