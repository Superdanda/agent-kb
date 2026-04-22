#!/usr/bin/env python3
"""
Agent 注册
用法: python3 agent_register.py --agent-code <CODE> --name <NAME> [--device-name <NAME>] [--environment-tags tag1,tag2]
"""
import argparse
import json
import requests
import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from _credentials import save

def register(agent_code: str, name: str, device_name: str = "", environment_tags: list = None) -> dict:
    base_url = os.environ.get("KB_BASE_URL", "http://localhost:8000")
    url = f"{base_url}/api/agents/register"
    payload = {
        "agent_code": agent_code,
        "name": name,
    }
    if device_name:
        payload["device_name"] = device_name
    if environment_tags:
        payload["environment_tags"] = environment_tags

    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()

def main():
    parser = argparse.ArgumentParser(description="注册新 Agent")
    parser.add_argument("--agent-code", required=True, help="Agent 唯一标识")
    parser.add_argument("--name", required=True, help="Agent 显示名称")
    parser.add_argument("--device-name", default="", help="设备名称")
    parser.add_argument("--environment-tags", default="", help="环境标签，逗号分隔")
    args = parser.parse_args()

    tags = [t.strip() for t in args.environment_tags.split(",") if t.strip()] if args.environment_tags else []

    result = register(args.agent_code, args.name, args.device_name, tags)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 自动保存凭证
    if result.get("id") and result.get("access_key") and result.get("secret_key"):
        save(
            agent_id=result["id"],
            access_key=result["access_key"],
            secret_key=result["secret_key"],
            base_url=os.environ.get("KB_BASE_URL", "http://localhost:8000"),
        )
        print("\n[OK] 凭证已自动保存到 ~/.hermes/knowledge-platform-credentials.json")

if __name__ == "__main__":
    main()
