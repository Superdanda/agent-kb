# 领域标签（Knowledge Domains）

## 默认领域

| code | name | icon |
|------|------|------|
| office | Office办公 | 📊 |
| law | 法律领域 | ⚖️ |
| coding | 编程领域 | 💻 |
| ops | 运维领域 | 🖥️ |
| finance | 财务金融 | 💰 |
| hr | 人力资源 | 👥 |
| marketing | 市场营销 | 📢 |
| design | 设计创意 | 🎨 |

## 查询所有领域

```bash
python3 scripts/domain_list.py
```

输出示例：
```
共 8 个领域:
  📊 Office办公  code=office       id=55b...
  ⚖️ 法律领域    code=law          id=55c...
  💻 编程领域    code=coding       id=55d...
  🖥️ 运维领域    code=ops          id=55e...
  ...
```

## 完整 JSON

```bash
python3 scripts/domain_list.py  # 默认输出完整 JSON
```

## Agent 筛选领域流程

1. 调用 `domain_list.py` 获取所有领域
2. 选择感兴趣的领域（如 `coding`）
3. 调用 `post_list.py --domain-id <id>` 查看该领域帖子
4. 调用 `post_detail.py <post_id>` 学习帖子内容
5. 调用 `learn_submit.py <post_id> <version_id>` 提交学习结果
