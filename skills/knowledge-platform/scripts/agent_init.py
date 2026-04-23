#!/usr/bin/env python3
"""
Agent 一键初始化脚本 - 启动心跳和任务拉取进程。

从 credentials.json 读取凭证，自动启动：
1. platform_heartbeat.py - 心跳保活（每30秒）
2. poll_platform_tasks.py - 任务拉取（每10秒）

Usage:
    cd skills/knowledge-platform
    python3 scripts/agent_init.py

要停止服务：
    pkill -f platform_heartbeat.py
    pkill -f poll_platform_tasks.py
"""
import os
import sys
import json
import subprocess
import signal
import time
import urllib.request
import urllib.error
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
CREDENTIALS_PATH = SKILL_DIR / "credentials.json"
HEARTBEAT_SCRIPT = SKILL_DIR / "scripts" / "platform_heartbeat.py"
POLL_SCRIPT = SKILL_DIR / "scripts" / "poll_platform_tasks.py"


def load_credentials():
    """加载凭证文件"""
    if not CREDENTIALS_PATH.exists():
        print(f"ERROR: 凭证文件不存在: {CREDENTIALS_PATH}")
        print("请先运行: python3 scripts/agent_register.py --agent-code <CODE> --name <NAME>")
        sys.exit(1)
    
    with open(CREDENTIALS_PATH) as f:
        creds = json.load(f)
    
    required = ["agent_id", "access_key", "secret_key", "base_url"]
    for k in required:
        if not creds.get(k):
            print(f"ERROR: 凭证文件缺少必要字段: {k}")
            sys.exit(1)
    
    return creds


def check_platform_health(base_url: str) -> bool:
    """检查平台是否可达"""
    try:
        req = urllib.request.Request(base_url + "/docs")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except:
        return False


def is_process_running(script_name: str) -> bool:
    """检查进程是否在运行"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", script_name],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except:
        return False


def stop_process(script_name: str):
    """停止指定进程"""
    try:
        subprocess.run(["pkill", "-f", script_name], stderr=subprocess.DEVNULL)
        time.sleep(1)
        print(f"  已停止: {script_name}")
    except:
        pass


def start_background(script_path: Path, env: dict):
    """后台启动脚本"""
    log_file = SKILL_DIR / "logs" / f"{script_path.stem}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, "a") as f:
        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            env=env,
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
    return proc.pid


def main():
    print("=" * 60)
    print("Hermes Agent 初始化")
    print("=" * 60)
    
    # 1. 加载凭证
    print("\n[1/4] 加载凭证...")
    creds = load_credentials()
    print(f"  Agent: {creds.get('name', 'unknown')} ({creds.get('agent_code', '?')})")
    print(f"  Agent ID: {creds['agent_id']}")
    print(f"  Base URL: {creds['base_url']}")
    
    # 2. 检查平台连接
    print("\n[2/4] 检查平台连接...")
    if not check_platform_health(creds["base_url"]):
        print(f"  错误: 无法连接到 {creds['base_url']}")
        print("  请确认平台服务正在运行")
        sys.exit(1)
    print("  平台连接正常")
    
    # 3. 检查并停止旧进程
    print("\n[3/4] 检查运行状态...")
    for script in ["platform_heartbeat.py", "poll_platform_tasks.py"]:
        if is_process_running(script):
            print(f"  发现旧进程: {script}，正在停止...")
            stop_process(script)
    
    # 4. 启动新进程
    print("\n[4/4] 启动后台服务...")
    env = os.environ.copy()
    env["PLATFORM_API_BASE"] = creds["base_url"]
    env["PLATFORM_AGENT_ID"] = creds["agent_id"]
    env["PLATFORM_ACCESS_KEY"] = creds["access_key"]
    env["PLATFORM_SECRET_KEY"] = creds["secret_key"]
    
    heartbeat_pid = start_background(HEARTBEAT_SCRIPT, env)
    print(f"  心跳服务已启动 (PID: {heartbeat_pid})")
    
    poll_pid = start_background(POLL_SCRIPT, env)
    print(f"  任务拉取服务已启动 (PID: {poll_pid})")
    
    print("\n" + "=" * 60)
    print("初始化完成！")
    print("=" * 60)
    print(f"  心跳进程: PID {heartbeat_pid} (每30秒)")
    print(f"  任务拉取: PID {poll_pid} (每10秒)")
    print(f"  日志文件: {SKILL_DIR / 'logs'}")
    print("\n停止服务:")
    print("  pkill -f platform_heartbeat.py")
    print("  pkill -f poll_platform_tasks.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
