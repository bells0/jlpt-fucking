---
title: "维护脚本索引"
type: 索引
tags:
  - jlpt-n2
  - 索引
---
# 维护脚本索引

[[README|← 返回总导航]]

| 脚本 | 用途 | 详细说明 |
|---|---|---|
| `new_mistake_batch.py` | 归档错题截图并生成错题批次模板 | [[docs/automation|错题自动整理说明]] |
| `check_mistake_originals.py` | 检查错题批次是否完整保留原题和必要字段 | [[docs/automation|错题自动整理说明]] |
| `check_obsidian_vault.py` | 检查属性、双链、嵌入、原子知识点和索引完整性 | [[docs/automation|错题自动整理说明]] |

完整检查：

```bash
python3 scripts/check_mistake_originals.py
python3 scripts/check_obsidian_vault.py
```
