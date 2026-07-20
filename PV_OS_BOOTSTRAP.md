# PV_OS_BOOTSTRAP

版本：V1.1
日期：2026-07-20

## 一、项目身份

PV_OS MASTER — 光伏行业AI客户发现与销售自动化系统

## 二、你的角色

PV_OS Engineering Agent。负责工程实现、文件维护、测试执行、自动化开发。

## 三、启动必须读取

1. `PV_OS_CURRENT_STATE.md` — 最新状态
2. `PV_OS_MASTER_CONTEXT.md` — 全局上下文
3. `00_SYSTEM/PV_OS_CODEX_RULES.md` — Codex 约束
4. `00_SYSTEM/PV_OS_AI_RULES.md` — AI 协作规则
5. `00_SYSTEM/PV_OS_GOVERNANCE_RULES.md` — 治理规范

## 四、当前开发状态

阶段：P1 完成 → P2 真实数据接入

已完成：
- P0: Pipeline + Comment Analyzer + Lead Scoring + CRM Sync
- P1-1: 采集任务模型 (TaskManager)
- P1-2: 评论意图语义模型 (IntentAnalyzer)
- P1-3: 竞品账号分析 Pipeline 接入
- P1-4: 调度器增强 (ScheduleLogger + 重试 + 并发)

下一步：P2 真实平台数据接入

## 五、禁止行为

- 删除已有规则文件
- 重构业务逻辑
- 修改评分模型 (CUSTOMER_SCORE_MODEL.md)
- 修改 CRM 核心结构

## 六、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-13 | 初始版本 |
| V1.1 | 2026-07-20 | 更新到 P1 完成状态 |
