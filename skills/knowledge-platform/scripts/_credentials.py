#!/usr/bin/env python3
"""
统一凭证管理 - 读取 ~/.hermes/knowledge-platform-credentials.json
"""
import json
import os
import sys
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".hermes" / "knowledge-platform-credentials.json"
OVERRIDE_ENV_PREFIX = "KB_"

def _get_env(key: str):
    return os.environ.get(f"{OVERRIDE_ENV_PREFIX}{key}", "")

def _get_nested(data: dict, *keys, default=""):
    for k in keys:
        if isinstance(data, dict):
            data = data.get(k, default)
        else:
            return default
    return data if data != "" else default

def load():
    creds = {
        "agent_id": "",
        "access_key": "",
        "secret_key": "",
        "base_url": "http://localhost:8000",
    }

    # 环境变量优先级最高
    for k in creds:
        val = _get_env(k.upper())
        if val:
            creds[k] = val

    # 其次从配置文件读取（不覆盖已设置的环境变量值）
    if CREDENTIALS_PATH.exists():
        try:
            with open(CREDENTIALS_PATH) as f:
                data = json.load(f)
            if not creds["agent_id"]:
                creds["agent_id"] = _get_nested(data, "agent_id")
            if not creds["access_key"]:
                creds["access_key"] = _get_nested(data, "access_key")
            if not creds["secret_key"]:
                creds["secret_key"] = _get_nested(data, "secret_key")
            if not _get_env("BASE_URL"):
                creds["base_url"] = _get_nested(data, "base_url", default=creds["base_url"])
        except Exception as e:
            print(f"[WARN] Failed to load credentials from {CREDENTIALS_PATH}: {e}", file=sys.stderr)

    return creds

def require_agent_id():
    """确保已配置 agent_id，否则退出并提示注册流程"""
    creds = load()
    if not creds["agent_id"]:
        print("ERROR: Agent ID not configured.", file=sys.stderr)
        print("Run: python3 scripts/agent_register.py --agent-code <CODE> --name <NAME> [--device-name <NAME>] [--environment-tags tag1,tag2]", file=sys.stderr)
        print(f"Or create {CREDENTIALS_PATH} with: agent_id, access_key, secret_key, base_url", file=sys.stderr)
        sys.exit(1)
    return creds

def save(agent_id: str, access_key: str, secret_key: str, base_url: str = "http://localhost:8000"):
    """保存注册后的凭证到配置文件"""
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump({
            "agent_id": agent_id,
            "access_key": access_key,
            "secret_key": secret_key,
            "base_url": base_url,
        }, f, indent=2)
    print(f"Credentials saved to {CREDENTIALS_PATH}")

if __name__ == "__main__":
    import json
    creds = load()
    print(json.dumps(creds, indent=2))
