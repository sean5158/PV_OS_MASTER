# 05_CUSTOMER_LEADS —— 潜在客户线索库

## 目录用途

存放经 AI 识别和评分后的潜在客户线索，是 CRM 客户跟踪流程的起点。连接评论分析与销售漏斗。

典型内容：
- Comment Analyzer 识别出的潜在客户记录
- Customer Scorer 评分结果与优先级
- 客户意图标签（想装、比价、观望）
- 线索状态跟踪（新线索 → 已联系 → 报价中 → 成交 / 流失）

## 数据类型

- CSV 格式的线索主表（leads_master.csv）
- JSON 格式的单条线索完整档案
- Markdown 格式的线索分析摘要

## 未来 AI 读取方式

Customer Scorer Agent 读取此目录的新增线索进行评分，Lead Follow-up Agent 读取线索状态生成跟进建议。AI 按"状态 + 优先级"筛选待处理线索，避免全表扫描。
