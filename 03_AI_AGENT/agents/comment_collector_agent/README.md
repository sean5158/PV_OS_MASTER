# Comment Collector Agent — README

版本：V1.0 | 日期：2026-07-20
Agent 定义：`agent.yml` V1.1

## 定位

PV_OS 数据链路最前端——连接视频平台 → 采集竞品评论 → 输出到 02_DATA/raw/ → 触发 Pipeline

```
视频平台 → comment_collector_agent → 02_DATA/raw/ → data_cleaner → Pipeline → CRM
```

## 文件结构

| 文件 | 用途 |
|------|------|
| `agent.yml` | Agent 定义（V1.1） |
| `README.md` | 本文件 |

## 相关代码

| 组件 | 路径 |
|------|------|
| 连接器基座 | `08_SYSTEM/scripts/collector_base.py` |
| 抖音连接器 | `08_SYSTEM/scripts/douyin_connector.py` |
| 小红书连接器 | `08_SYSTEM/scripts/xiaohongshu_connector.py` |
| 数据清洗 | `08_SYSTEM/scripts/data_cleaner.py` |
| 配置加载 | `08_SYSTEM/scripts/config_loader.py` |
| 运行入口 | `08_SYSTEM/scripts/run_collector.py` |
| 调度器 | `10_AI_AUTOMATION_ENGINE/scheduler/collection_scheduler.py` |
| 采集配置 | `02_DATA/01_COLLECTION/config.yml` |
| 采集规则 | `02_DATA/01_COLLECTION/COLLECTION_RULE.md` |

## 运行方式

```bash
# Mock 模式（测试数据验证链路）
cd PV_OS_MASTER
python 08_SYSTEM/scripts/run_collector.py

# 调度模式（定时触发）
python 10_AI_AUTOMATION_ENGINE/scheduler/collection_scheduler.py --once

# 完整链路（采集 + Pipeline）
python 10_AI_AUTOMATION_ENGINE/scheduler/collection_scheduler.py --once
```

## 当前状态

- ✅ Agent 定义 (agent.yml V1.1)
- ✅ 连接器基座 (collector_base.py)
- ✅ 平台连接器 (douyin/xiaohongshu, Mock 模式)
- ✅ 数据清洗管道 (data_cleaner.py)
- ✅ 调度器 (collection_scheduler.py)
- ✅ Pipeline 集成 (event_bus 触发)
- ⬜ 抖音真实 API 对接
- ⬜ 小红书真实 API 对接

## 设计文档

- `PV_OS_COMMENT_COLLECTION_STRATEGY.md` V2.0 — 采集策略
- `COMMENT_COLLECTOR_AGENT_DESIGN.md` V2.0 — Agent 设计
- `COMMENT_COLLECTION_AUDIT.md` — 采集能力审计
