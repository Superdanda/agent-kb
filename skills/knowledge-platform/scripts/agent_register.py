#!/usr/bin/env python3
"""
Agent 注册申请 - 向平台发起注册请求，等待管理员审批。

用法:
    python3 agent_register.py --agent-code <CODE> --name <NAME> \
        [--device-name <NAME>] [--environment-tags tag1,tag2] \
        [--base-url http://localhost:8000]

注册成功后：
1. 打印 registration_code
2. 提示联系管理员审批
3. 审批后运行 agent_init.py 启动心跳和任务拉取
"""
import argparse
import json
import requests
import sys
import time
from pathlib import Path

# Skill 目录 - credentials.json 保存在此
SKILL_DIR = Path(__file__).parent.parent
CREDENTIALS_PATH = SKILL_DIR / "credentials.json"


def register(agent_code: str, name: str, device_name: str = "", environment_tags: list = None, base_url: str = "http://localhost:8000") -> dict:
    """发起注册申请"""
    url = f"{base_url}/api/agent-registrations/register"
    payload = {
        "agent_code": agent_code,
        "name": name,
    }
    if device_name:
        payload["device_name"] = device_name
    if environment_tags:
        payload["environment_tags"] = environment_tags

    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def check_registration_status(registration_code: str, base_url: str) -> dict:
    """查询注册状态"""
    url = f"{base_url}/api/agent-registrations/{registration_code}/status"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_credentials(registration_code: str, base_url: str) -> dict:
    """获取审批后的凭证"""
    url = f"{base_url}/api/agent-registrations/{registration_code}/credentials"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def save_credentials(creds: dict):
    """保存凭证到 skill 目录"""
    data = {
        "agent_id": creds["agent_id"],
        "access_key": creds["access_key"],
        "secret_key": creds["secret_key"],
        "base_url": creds.get("base_url", "http://localhost:8000"),
        "registration_code": creds.get("registration_code", ""),
        "agent_code": creds.get("agent_code", ""),
        "name": creds.get("name", ""),
        "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  凭证已保存到: {CREDENTIALS_PATH}")


def main():
    parser = argparse.ArgumentParser(description="注册新 Agent（发起注册申请）")
    parser.add_argument("--agent-code", required=True, help="Agent 唯一标识")
    parser.add_argument("--name", required=True, help="Agent 显示名称")
    parser.add_argument("--device-name", default="", help="设备名称")
    parser.add_argument("--environment-tags", default="", help="环境标签，逗号分隔")
    parser.add_argument("--base-url", default="http://localhost:8000", help="平台地址")
    parser.add_argument("--wait", action="store_true", help="等待审批（轮询状态直到 APPROVED）")
    args = parser.parse_args()

    tags = [t.strip() for t in args.environment_tags.split(",") if t.strip()]

    print("=" * 60)
    print("Hermes Agent 注册申请")
    print("=" * 60)
    print(f"  Agent Code: {args.agent_code}")
    print(f"  Name: {args.name}")
    print(f"  Base URL: {args.base_url}")
    print()

    # 发起注册申请
    print("[1/2] 发起注册申请...")
    try:
        result = register(args.agent_code, args.name, args.device_name, tags, args.base_url)
        registration_code = result.get("registration_code")
        print(f"  注册申请已提交!")
        print(f"  Registration Code: {registration_code}")
    except requests.exceptions.HTTPError as e:
        print(f"  注册失败: {e}")
        if e.response is not None:
            print(f"  响应: {e.response.text[:200]}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("请登录管理后台审批此注册申请:")
    print(f"  URL: {args.base_url}/admin/agent-registrations")
    print(f"  Registration Code: {registration_code}")
    print("=" * 60)
    print()

    if args.wait:
        print("[2/2] 等待审批...")
        while True:
            time.sleep(5)
            status = check_registration_status(registration_code, args.base_url)
            st = status.get("status", "UNKNOWN")
            print(f"  当前状态: {st} ({status.get('status_text', '')})")
            if st == "APPROVED":
                print("  注册已审批！正在获取凭证...")
                creds = get_credentials(registration_code, args.base_url)
                save_credentials(creds)
                print("\n  接下来运行以下命令启动心跳和任务拉取:")
                print("    python3 scripts/agent_init.py")
                break
            elif st == "REJECTED":
                print("  注册被拒绝!")
                reason = status.get("rejection_reason", "")
                if reason:
                    print(f"  原因: {reason}")
                sys.exit(1)
            else:
                print("  等待中... (Ctrl+C 退出)")
    else:
        print("审批通过后，运行以下命令:")
        print("  python3 scripts/agent_register.py --wait --agent-code", args.agent_code, "--name", args.name)
        print()
        print("或者手动获取凭证后直接运行:")
        print("  python3 scripts/agent_init.py")


if __name__ == "__main__":
    main()
