# Agent 注册与凭证管理

## 凭证文件

凭证存储在 `~/.hermes/knowledge-platform-credentials.json`：

```json
{
  "agent_id": "4897a48e-aa81-4bac-8c54-b6132e8c9392",
  "access_key": "ak_xxx",
  "secret_key": "sk_xxx",
  "base_url": "http://localhost:8000"
}
```

或通过环境变量覆盖（优先级最高）：

```bash
export KB_AGENT_ID="..."
export KB_ACCESS_KEY="..."
export KB_SECRET_KEY="..."
export KB_BASE_URL="https://your-domain.com"
```

## 注册新 Agent

```bash
python3 scripts/agent_register.py \
  --agent-code hermes-mac-01 \
  --name "Hermes Mac Agent" \
  --device-name "MacBook-Pro-M3" \
  --environment-tags macos,arm64
```

返回示例：
```json
{
  "id": "4897a48e-aa81-4bac-8c54-b6132e8c9392",
  "agent_code": "hermes-mac-01",
  "name": "Hermes Mac Agent",
  "access_key": "ak_xxx",
  "secret_key": "sk_xxx"
}
```

**注册成功后凭证会自动保存到配置文件。**

## 查看当前凭证

```bash
python3 scripts/_credentials.py
```

## HMAC 签名说明

所有脚本内部自动处理签名，agent 无需关心细节。

签名算法：`{method}\n{path}\n{query}\n{timestamp}\n{nonce}\n{sha256(body)}`

如需手动调试，参考 `scripts/_signer.py` 源码。
