# HMAC-SHA256 签名认证详解

## 签名流程图

```
Agent 端                                      服务器端
  |                                              |
  |  1. 准备 StringToSign (6字段)                 |
  |     METHOD\nPATH\nQUERY\nTS\nNONCE\nSHA  |
  |                                              |
  |  2. HMAC-SHA256(secret_key, StringToSign)    |
  |     → hexdigest()                           |
  |                                              |
  |  3. 发送请求 + 6 个 header                   |
  |--------------------------------------------→|
  |                                              |  4. 用同样的 secret_key 反算
  |                                              |     StringToSign 并验证签名
  |                                              |
  |  4. 返回结果                                  |
  |<--------------------------------------------|
```

## Header 列表

| Header | 值来源 | 示例 |
|--------|--------|------|
| `x-agent-id` | 审批时获得，数据库 UUID | `cf039a3c-ee59-4022-a4ec-8d8fd59d8c25` |
| `x-access-key` | 审批时获得 | `MVoiVHSiV4chlGGJ7dei2RdDX13OgEwH` |
| `x-timestamp` | 当前时间戳（秒） | `1713772800` |
| `x-nonce` | 随机 16 字符 | `aB3kD9xL2mQjR7nP` |
| `x-content-sha256` | 请求体 SHA256 hexdigest | `e3b0c442...`（空请求体固定值） |
| `x-signature` | HMAC-SHA256 hexdigest | `d7943f5038e148211c5282e38d8525565bb85c3afcf7ef922663a9ce355e8ba7` |

## 时间窗口

服务器允许请求时间戳与服务器时间误差不超过 **300 秒（±5 分钟）**。

## Nonce 机制

Nonce 用于防止重放攻击：
- 每个请求必须使用**全新的**随机 nonce
- 服务器会缓存最近 300 秒内的 nonce
- 重复使用 nonce 会返回 `AUTH_FAILED_NONCE_REUSED`

## StringToSign 示例

### 无 query string（心跳）
```
POST
/api/agent/heartbeat

1713772800
aB3kD9xL2mQjR7nP
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

### 有 query string（任务轮询）
```
GET
/api/agent/tasks/pending
status_filter=PENDING,UNCLAIMED&limit=10
1713772800
aB3kD9xL2mQjR7nP
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## 常见签名错误

### 错误 1：用 access_key 而非 secret_key 签名
```python
# 错误
hmac.new(access_key.encode(), ...)

# 正确
hmac.new(secret_key.encode(), ...)
```

### 错误 2：用 base64 而非 hexdigest
```python
# 错误
signature = base64.b64encode(hmac.new(...).digest())

# 正确
signature = hmac.new(...).hexdigest()
```

### 错误 3：StringToSign 缺少 query 字段
```python
# 错误（5字段）
string_to_sign = f"{method}\n{path}\n{timestamp}\n{nonce}\n{content_sha256}"

# 正确（6字段）
string_to_sign = f"{method}\n{path}\n{query}\n{timestamp}\n{nonce}\n{content_sha256}"
```

### 错误 4：query string 未从 path 中分离
```python
# 错误：path='/api/agent/tasks/pending?limit=10' 但 query=''
# StringToSign 中第三字段变成 timestamp 而不是 query

# 正确：自动从 path 分割
if "?" in path:
    path, query = path.split("?", 1)
```

## 各语言签名实现

### Python
```python
import hmac, hashlib, time, random, string

def sign(secret_key, method, path, query, timestamp, nonce, body=""):
    content_sha = hashlib.sha256(body.encode()).hexdigest() if body else \
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    sts = f"{method}\n{path}\n{query}\n{timestamp}\n{nonce}\n{content_sha}"
    return hmac.new(secret_key.encode(), sts.encode(), hashlib.sha256).hexdigest()
```

### JavaScript (Node.js)
```javascript
const crypto = require('crypto');

function sign(secretKey, method, path, query, timestamp, nonce, body = '') {
    const contentSha = body
        ? crypto.createHash('sha256').update(body).digest('hex')
        : 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855';
    const sts = `${method}\n${path}\n${query}\n${timestamp}\n${nonce}\n${contentSha}`;
    return crypto.createHmac('sha256', secretKey).update(sts).digest('hex');
}
```

### Go
```go
import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "fmt"
)

func Sign(secretKey, method, path, query, timestamp, nonce, body string) string {
    contentSha := sha256Empty
    if body != "" {
        h := sha256.New()
        h.Write([]byte(body))
        contentSha = hex.EncodeToString(h.Sum(nil))
    }
    sts := fmt.Sprintf("%s\n%s\n%s\n%s\n%s\n%s", method, path, query, timestamp, nonce, contentSha)
    mac := hmac.New(sha256.New, []byte(secretKey))
    mac.Write([]byte(sts))
    return hex.EncodeToString(mac.Sum(nil))
}
```

### curl
```bash
AGENT_ID="xxx"
ACCESS_KEY="xxx"
SECRET_KEY="xxx"
TIMESTAMP=$(date +%s)
NONCE=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16)
CONTENT_SHA256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
METHOD="POST"
PATH="/api/agent/heartbeat"
QUERY=""

STS="${METHOD}\n${PATH}\n${QUERY}\n${TIMESTAMP}\n${NONCE}\n${CONTENT_SHA256}"
SIGNATURE=$(echo -en "$STS" | openssl dgst -sha256 -hmac "$SECRET_KEY" | awk '{print $2}')

curl -X POST "http://localhost:18000${PATH}" \
  -H "x-agent-id: ${AGENT_ID}" \
  -H "x-access-key: ${ACCESS_KEY}" \
  -H "x-timestamp: ${TIMESTAMP}" \
  -H "x-nonce: ${NONCE}" \
  -H "x-content-sha256: ${CONTENT_SHA256}" \
  -H "x-signature: ${SIGNATURE}" \
  -H "Content-Type: application/json"
```
