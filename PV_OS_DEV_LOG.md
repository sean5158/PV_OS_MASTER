# PV_OS Development Decision Log


## 2026-07-20

### Decision: 采集链路代码层先于真实数据接入

Reason:

采集模块的代码骨架必须在真实数据接入前完成。
Mock 模式让整个链路可离线验证。

建立：

- 连接器基座 (collector_base.py)
- 四平台连接器 (douyin/xiaohongshu/kuaishou/wechat_video)
- 数据清洗管道 (data_cleaner.py)
- 调度器 + Pipeline 触发 (collection_scheduler.py)

真实数据接入取决于平台 API 凭证和竞品主表填充，属配置层问题。


---

### Decision: 采集阶段不做价值判断

Reason:

采集器的唯一职责是"从平台拿到评论，标准化后保存"。
不做：客户价值判断、城市/农村过滤、意向高低预判。
全部交给下游 comment_analyzer 和 lead_scoring_agent。

这确保了数据完整性，不会因为前置过滤丢失潜在客户。


---

## 2026-07-18

### Decision: Build AI Operating System, not a collection of tools

Reason:

PV_OS should become a complete AI business operating system.

The goal is not individual automation scripts,
but a connected intelligence system.


---

### Decision: Customer discovery before CRM

Reason:

The core business problem is not storing customers.

The core problem is:

How can AI actively discover potential customers,
identify opportunities,
and generate business signals?


---

### Decision: Competitor Intelligence as a signal source

Reason:

Competitor activities contain market information.

AI should analyze:

- content trends
- audience response
- market changes
- business opportunities


---

### Decision: Preserve architecture before rapid coding

Reason:

The system needs stable structure,
clear modules,
and reusable AI Agents.
