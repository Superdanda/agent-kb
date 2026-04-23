#!/usr/bin/env python3
"""
统一凭证管理 - 读取 skill 目录下的 credentials.json

凭证文件位置：skills/knowledge-platform/credentials.json

环境变量优先级最高（KB_AGENT_ID, KB_ACCESS_KEY, KB_SECRET_KEY, KB_BASE_URL）。
"""
import json
import os
import sys
from pathlib import Path

# Skill 目录（向上找两级：scripts/ -> knowledge-platform/ -> skills/）
SKILL_DIR = Path(__file__).parent.parent
CREDENTIALS_PATH = SKILL_DIR / "credentials.json"
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
    """加载凭证，环境变量优先，文件兜底"""
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

    # 其次从配置文件读取（skill 目录下的 credentials.json）
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
        print(f"Hint: Run: python3 scripts/agent_register.py --agent-code <CODE> --name <NAME>", file=sys.stderr)
        print(f"Or create {CREDENTIALS_PATH} with: agent_id, access_key, secret_key, base_url", file=sys.stderr)
        sys.exit(1)
    return creds

def save(agent_id: str, access_key: str, secret_key: str, base_url: str = "http://localhost:8000", registration_code: str = "", agent_code: str = "", name: str = ""):
    """保存注册后的凭证到 skill 目录"""
    import time
    data = {
        "agent_id": agent_id,
        "access_key": access_key,
        "secret_key": secret_key,
        "base_url": base_url,
        "registration_code": registration_code,
        "agent_code": agent_code,
        "name": name,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Credentials saved to {CREDENTIALS_PATH}")

if __name__ == "__main__":
    import json
    creds = load()
    print(json.dumps(creds, indent=2))
