#!/usr/bin/env python3
"""
HMAC-SHA256 签名生成器 - 内部使用，脚本自动调用
签名算法: {method}\n{path}\n{query}\n{timestamp}\n{nonce}\n{content_sha256}
"""
import hashlib
import hmac
import time
import uuid
from typing import Optional

def sign(secret_key: str, method: str, path: str, query: str = "", body: str = "") -> dict:
    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex[:16]
    sha = hashlib.sha256(body.encode()).hexdigest()
    sign_str = f"{method}\n{path}\n{query}\n{ts}\n{nonce}\n{sha}"
    sig = hmac.new(secret_key.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
    return {
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Content-SHA256": sha,
        "X-Signature": sig,
    }

def build_headers(agent_id: str, access_key: str, secret_key: str,
                  method: str, path: str, query: str = "", body: str = "") -> dict:
    """构建完整的认证请求头"""
    sig_parts = sign(secret_key, method, path, query, body)
    return {
        "X-Agent-Id": agent_id,
        "X-Access-Key": access_key,
        **sig_parts,
        "Content-Type": "application/json",
    }
