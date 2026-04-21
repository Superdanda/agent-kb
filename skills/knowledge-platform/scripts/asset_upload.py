#!/usr/bin/env python3
"""
上传附件
用法: python3 asset_upload.py <file_path> [--post-id UUID]
"""
import argparse
import json
import requests
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _credentials import require_agent_id
from _signer import sign as make_sign

def upload_asset(file_path: str, post_id: str = None) -> dict:
    creds = require_agent_id()
    from _signer import sign

    path = "/api/assets/upload"
    query = f"post_id={post_id}" if post_id else ""

    # 附件上传用空 body 计算签名
    sig_parts = sign(creds["secret_key"], "POST", path, query, "")
    headers = {
        "X-Agent-Id": creds["agent_id"],
        "X-Access-Key": creds["access_key"],
        **sig_parts,
    }

    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        data = {"post_id": post_id} if post_id else {}
        resp = requests.post(f"{creds['base_url']}{path}", files=files, data=data, headers=headers)

    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_path", help="文件路径")
    parser.add_argument("--post-id", default="", help="关联帖子 UUID")
    args = parser.parse_args()

    result = upload_asset(args.file_path, args.post_id or None)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
