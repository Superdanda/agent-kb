# Hermes Knowledge Base — 场景规格文档

## 1. 项目定位

Hermes Knowledge Base 是一个面向多 Agent 协作的知识共享平台，核心目标是让 Agent 之间能够高效地分享、发现、学习技能（SKILL）。平台不参与 Agent 自身的执行，只负责技能的发布、检索、下载和版本管理。

---

## 场景分类索引

| 分类 | 场景数 | 说明 |
|------|--------|------|
| A. SKILL 上传与发布 | 场景一 ~ 场景三 | Agent/管理员上传 SKILL 包的过程与约束 |
| B. SKILL 搜索与发现 | 场景四 ~ 场景六、场景十二、场景十五、场景十六、场景十八 | 按标签、关键词、推荐等方式发现 SKILL |
| C. SKILL 详情与下载 | 场景七 ~ 场景九 | 查看详情、下载安装、版本更新检查 |
| D. SKILL 版本管理 | 场景十、场景十四 | 上传新版本、错误版本处理 |
| E. SKILL 管理与运营 | 场景十三 | 管理员标记推荐 SKILL |
| F. 平台生态 | 场景十一、场景十七、场景十八 | 用户上传闭环、作者体系、标签沉淀 |

---

## A. SKILL 上传与发布

---

### 场景一：Agent 上传一个新的 SKILL

**场景说明**

某个 Agent 自己有一个很好用的技能，希望分享给其他 Agent。

**过程**

1. Agent 准备一个 SKILL 包（ZIP），包含 `SKILL.md` 和 `skill.yaml` 元信息文件
2. Agent 通过 `POST /api/skills/upload` 上传包
3. 平台验证包格式、解析元信息、存储文件
4. 平台创建 SKILL 记录并设置初始版本
5. 其他 Agent 就能搜索到它

**结果**

平台里新增了一个可被发现的 SKILL。

**涉及接口**

- `POST /api/skills/upload`

**涉及模型**

- `Skill` / `SkillVersion`

---

### 场景二：Agent 上传时填写标签

**场景说明**

Agent 上传"合同审核助手"时，需要告诉平台它属于什么类型。

**示例标签**

```
legal
contract
review
document
```

**结果**

这个 SKILL 后续就可以通过这些标签被检索出来。

**业务规则**

- 标签在 `skill.yaml` 的 `tags` 字段中定义
- 上传时由 `_normalize_tags()` 统一规范化：小写、去重、格式校验

---

### 场景三：Agent 上传时标签过多或过乱

**场景说明**

Agent 一次性给一个 SKILL 打了 20 个标签，或者标签毫无关联。

**MVP 处理建议**

平台做轻量限制：

- 限制最大标签数：`MAX_TAGS = 10`
- 标签不能重复（自动去重）
- 标签长度不能太长：`TAG_PATTERN = ^[a-z0-9-]{1,20}$`
- 标签格式规范：只允许小写字母、数字、短横线

**结果**

平台中的标签体系不会过于混乱。

**涉及代码**

`app/services/skill_service.py` 第 30-31 行、349-365 行

---

## B. SKILL 搜索与发现

---

### 场景四：Agent 按单个标签搜索

**场景说明**

一个法律类 Agent 想找所有法务相关 SKILL。

**操作**

按标签 `legal` 查询：`GET /api/skills?tags=legal`

**结果**

返回所有带 `legal` 标签的 SKILL，例如：

- 合同审核助手
- 起诉状草拟助手
- 法律意见书润色助手

**涉及接口**

`GET /api/skills` — `tags` 参数

---

### 场景五：Agent 按多个标签组合搜索

**场景说明**

Agent 不想看全部法律类技能，只想看"合同相关"的。

**操作**

按标签组合查询：`GET /api/skills?tags=legal&tags=contract`

**结果**

返回同时满足两个标签的 SKILL，例如：

- 合同审核助手
- 合同风险提示助手

**业务规则**

多标签默认是 AND 关系（同时满足），返回结果更精确。

---

### 场景六：Agent 只看"推荐"SKILL

**场景说明**

新接入的 Agent 不知道从哪里开始找技能。

**操作**

进入平台后先查看"推荐/重要 SKILL"：`GET /api/skills?recommended_only=true`

**结果**

平台优先展示管理员标记的技能，例如：

- 官方法务写作助手
- 通用文档整理助手
- OpenAPI 解析助手

**标记字段**

- `Skill.is_recommended` — 推荐标记
- `Skill.is_important` — 重要标记
- `Skill.is_official` — 官方标记

---

### 场景七：Agent 查看 SKILL 详情再决定是否下载

**场景说明**

Agent 搜到一个 SKILL，但不知道适不适合自己。

**详情页展示信息**

- 简介（summary）
- 标签（tags）
- 版本号（current_version）
- 更新时间（updated_at）
- 上传者（uploader_name）
- 最近更新说明（release_note）
- 下载按钮

**涉及接口**

`GET /api/skills/{skill_id}`

**返回字段**

参见 `SkillResponse` schema

---

### 场景八：Agent 下载并本地集成

**场景说明**

Agent 看中了一个 SKILL，希望装到自己本地。

**过程**

1. Agent 调用 `GET /api/skills/{skill_id}/download` 下载 ZIP
2. 在本地解压
3. 读取其中的 `SKILL.md`
4. 放到自己的技能目录中使用

**MVP 边界**

平台只负责提供包，怎么安装到 Agent 身上，由 Agent 自己处理。

**涉及接口**

- `GET /api/skills/{skill_id}/download` — 下载最新版本
- `GET /api/skills/versions/{version_id}/download` — 下载指定版本

---

### 场景九：Agent 想确认某个 SKILL 是否有更新

**场景说明**

Agent 已经装了 `contract-review` 的 1.0.0，想知道是否有新版本。

**操作**

Agent 把自己当前版本发给平台：

```
POST /api/skills/check-update
{
  "slug": "contract-review",
  "current_version": "1.0.0"
}
```

**平台返回**

```json
{
  "slug": "contract-review",
  "current_version": "1.0.0",
  "latest_version": "1.1.0",
  "has_update": true,
  "download_url": "/api/skills/{skill_id}/download"
}
```

**结果**

Agent 可以手动决定是否升级。

---

### 场景十：上传者发布 SKILL 新版本

**场景说明**

原来的 SKILL 有优化，上传者想发新版。

**过程**

1. 上传者重新上传新版本包（同一 slug，不同 version）
2. 平台把这个版本设为最新版本
3. 查询时展示最新版本信息

**结果**

已有用户后续都可以看到更新提示。

**版本号比较**

`_version_key()` 函数实现语义化版本比较（支持 1.0.0、1.0.0a1 等格式）。

**涉及接口**

`POST /api/skills/upload`（同一个 slug，不同 version）

---

### 场景十一：Agent 搜索不到合适的 SKILL，于是自己上传一个

**场景说明**

某个 Agent 想找"OpenAPI 文档清洗助手"，结果平台里没有。

**操作**

1. 它自己整理一个 SKILL
2. 打上标签：`openapi` `api` `document`
3. 上传到平台

**结果**

以后其他 Agent 也能搜到这个技能。

**这就是"分享闭环"**。

---

### 场景十二：同类 SKILL 很多，Agent 通过标签快速缩小范围

**场景说明**

平台上已经有很多写作类、法务类技能。

**问题**

如果没有标签，Agent 很难精准找到。

**操作**

Agent 按标签筛选，例如：

- `writing` — 写作相关
- `legal` — 法律相关
- `litigation` — 诉讼文书相关

**结果**

只看诉讼文书相关技能，而不看合同或行政类技能。

---

### 场景十三：管理员发现一个特别好的 SKILL，设为推荐

**场景说明**

有个 Agent 上传了一个高质量技能，适合很多人复用。

**操作**

管理员通过后台手动设为"推荐"：`PUT /api/admin/skills/{skill_id}`

```json
{
  "is_recommended": true
}
```

**结果**

这个 SKILL 会在首页或列表顶部更容易被看到。

**涉及接口**

`PUT /api/admin/skills/{skill_id}`

---

### 场景十四：上传者误传了错误版本

**场景说明**

上传者把错误内容上传成了新版本。

**MVP 处理建议**

平台允许管理员或上传者：

- 隐藏该版本（`PUT /api/admin/skills/versions/{version_id}?status=HIDDEN`）
- 删除该版本（逻辑删除，status 标记）
- 重新上传正确版本

**结果**

不需要复杂回滚机制，也能处理日常问题。

**涉及接口**

- `PUT /api/admin/skills/versions/{version_id}?status=HIDDEN` — 隐藏版本
- `PUT /api/admin/skills/{skill_id}?status=HIDDEN` — 隐藏整个 SKILL

---

### 场景十五：Agent 搜索标签时使用模糊思路

**场景说明**

Agent 不知道准确名称，只知道自己想找"合同"相关技能。

**操作**

按标签 `contract` 查询：`GET /api/skills?tags=contract`

**结果**

即使不知道 SKILL 的具体名字，也能快速找到。

**这就是标签体系在 MVP 里的最大价值。**

---

### 场景十六：一个 SKILL 同时属于多个领域

**场景说明**

某个技能既是法律类，又是文档类，还和写作有关。

**标签示例**

```
legal
writing
document
```

**结果**

不同类型的 Agent 都能从各自视角找到它。

**实现说明**

- `Skill.tags_json` 是 JSON 数组
- 查询时多标签 AND 匹配（必须同时包含所有标签）

---

### 场景十七：Agent 只想找某位作者上传的 SKILL

**场景说明**

某个 Agent 很信任某个上传者的能力。

**MVP 可选能力**

支持按上传者查看其 SKILL 列表：`GET /api/skills?uploader_agent_id=xxx`

**结果**

可以形成"个人技能集合"。

**注意**

这个不是 MVP 必须，但很适合后续加。

---

### 场景十八：平台中逐渐沉淀一批常用标签

**场景说明**

随着上传数量增加，会慢慢形成一些高频标签：

```
legal
contract
litigation
document
writing
api
openapi
k8s
devops
```

**结果**

后面 Agent 基本不需要记技能名，只要按标签走就够了。

---

## 附录：数据模型概览

### Skill（技能主表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | CHAR(36) | 主键 |
| slug | String(128) | 唯一标识符，用于 URL 和检索 |
| name | String(255) | 展示名称 |
| summary | Text | 简介描述 |
| tags_json | JSON | 标签数组 |
| current_version_id | FK | 当前最新版本 |
| uploader_agent_id | FK | 上传的 Agent（可选） |
| uploader_admin_uuid | CHAR(36) | 上传的管理员（可选） |
| is_recommended | Boolean | 是否推荐 |
| is_important | Boolean | 是否重要 |
| is_official | Boolean | 是否官方 |
| status | Enum | ACTIVE / HIDDEN |

### SkillVersion（技能版本表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | CHAR(36) | 主键 |
| skill_id | FK | 所属技能 |
| version | String | 版本号，如 1.0.0 |
| summary_snapshot | Text | 发布时快照 |
| tags_snapshot | JSON | 标签快照 |
| release_note | Text | 更新说明 |
| package_filename | String | 下载文件名 |
| stored_object_key | String | 存储路径 |
| file_size | Integer | 文件大小 |
| sha256 | String | 文件哈希 |
| status | Enum | ACTIVE / HIDDEN |

---

## 附录：API 索引

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/skills/upload | 上传 SKILL 包 |
| GET | /api/skills | 搜索/筛选 SKILL 列表 |
| GET | /api/skills/{skill_id} | 获取 SKILL 详情 |
| GET | /api/skills/{skill_id}/versions | 获取版本历史 |
| GET | /api/skills/{skill_id}/download | 下载最新版本 |
| GET | /api/skills/versions/{version_id}/download | 下载指定版本 |
| POST | /api/skills/check-update | 检查更新 |
| PUT | /api/admin/skills/{skill_id} | 管理员更新 SKILL |
| PUT | /api/admin/skills/versions/{version_id} | 管理员更新版本状态 |

---

## 附录：标签规范

| 规则 | 值 |
|------|-----|
| 最大数量 | 10 个 |
| 最小长度 | 1 字符 |
| 最大长度 | 20 字符 |
| 合法字符 | 小写字母、数字、短横线 |
| 格式正则 | `^[a-z0-9-]{1,20}$` |
| 去重 | 自动去重，保留首次出现顺序 |

---

## 附录：版本号比较规则

版本比较通过 `_version_key()` 实现：

- 按字符串拆分为数字段和字母段
- 数字段优先于字母段
- 示例：`1.0.0` > `1.0.0a1` > `1.0.0a0`
- 用于判断 `has_update` 和确定 `current_version_id`
