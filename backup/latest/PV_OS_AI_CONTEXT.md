

# PV_OS_AI_CONTEXT


更新时间:

2026-07-19 11:08:53



# 项目

PV_OS_MASTER



# 当前定位

光伏行业 AI 自动化运营系统。



# 当前系统状态


# PV_OS 项目状态 V1.2

> 光伏行业 AI 自动化运营系统 · 当前进度、里程碑与变更记录
>
> 最后更新：2026-07-14

---

## 一、总体状态

| 维度 | 状态 |
|------|------|
| **当前阶段** | Phase 1.7：评论潜客发现链路固化 |
| **整体进度** | ████░░░░░░ 40% |
| **活跃模块** | 00_SYSTEM、02_DATA、03_AI_AGENT、05_CUSTOMER_LEADS、05_CUSTOMER_CRM、10_AI_AUTOMATION_ENGINE |
| **待启动模块** | 04_CONTENT、06_CASE_LIBRARY、07_FINANCE、08_SYSTEM、09_AI_OPERATION、11_AI_PRODUCTIZATION、12_AI_RUNTIME |
| **下一步焦点** | 测试评论数据准备 + Pipeline 运行验证 + CRM 同步测试 |

---

## 二、里程碑进度

### Phase 1：基础设施搭建

| # | 里程碑 | 状态 | 完成日期 |
|---|--------|------|---------|
| 1.1 | 14 个一级目录创建 | ✅ 完成 | 2026-07-11 |
| 1.2 | PV_OS_DIRECTORY_MAP.md V1.0 | ✅ 完成 | 2026-07-11 |
| 1.3 | PV_OS_AI_RULES.md V1.0 | ✅ 完成 | 2026-07-11 |
| 1.4 | PV_OS_ARCHITECTURE.md V1.0 | ✅ 完成 | 2026-07-11 |
| 1.5 | PV_OS_PROJECT_STATUS.md V1.0 | ✅ 完成 | 2026-07-11 |
| 1.6 | 各业务目录子结构搭建 | ✅ 完成 | 2026-07-12 |
| 1.7 | Comment Analyzer Agent V1.0 | ✅ 完成 | 2026-07-12 |
| 1.8 | Lead Scoring Agent V2.1 | ✅ 完成 | 2026-07-13 |
| 1.9 | Customer Finder Agent V1.0 | ✅ 完成 | 2026-07-12 |
| 1.10 | PV_OS Boot Context System V2 | ✅ 完成 | 2026-07-13 |
| 1.11 | 评论潜客发现链路固化 | ✅ 完成 | 2026-07-14 |
| 1.12 | 客户生命周期两层架构 | ✅ 完成 | 2026-07-14 |

### Phase 2：核心链路打通

| # | 里程碑 | 状态 |
|---|--------|------|
| 2.1 | 测试评论数据准备（城市小区客户样本） | ⬜ 待开始 |
| 2.2 | Comment Analyzer 运行验证 | ⬜ 待开始 |
| 2.3 | Lead Scoring 运行验证 | ⬜ 待开始 |
| 2.4 | Pipeline 端到端验证 | ⬜ 待开始 |
| 2.5 | CRM 同步测试 | ⬜ 待开始 |
| 2.6 | 抖音数据采集管道跑通 | ⬜ 待开始 |
| 2.7 | 小红书数据采集管道跑通 | ⬜ 待开始 |

### Phase 3：自动化与扩展

| # | 里程碑 | 状态 |
|---|--------|------|
| 3.1 | 定时采集自动化（Cron 调度） | ⬜ 待开始 |
| 3.2 | 竞品自动发现 Agent 上线 | ⬜ 待开始 |
| 3.3 | 爆款拆解 → 内容生产流水线 | ⬜ 待开始 |
| 3.4 | 运营仪表盘 | ⬜ 待开始 |

### Phase 4：产品化

| # | 里程碑 | 状态 |
|---|--------|------|
| 4.1 | 产品定义与定价 | ⬜ 待开始 |
| 4.2 | 营销材料包 | ⬜ 待开始 |
| 4.3 | 云端部署 | ⬜ 待开始 |

---

## 三、模块就绪度

| 目录 | 就绪度 | 已存在内容 |
|------|--------|-----------|
| `00_SYSTEM/` | 🟢 就绪 | AI_RULES / GOVERNANCE_RULES / CODEX_RULES / ARCHITECTURE / DIRECTORY_MAP / ENVIRONMENT / PROJECT_STATUS / RECOVERY_GUIDE / DEVELOPMENT_ROADMAP |
| `01_PROJECT_MANAGEMENT/` | 🟡 初步 | tasks/ |
| `02_DATA/` | 🟡 初步 | 01_KEYWORD_LIBRARY / 02_COMPETITOR_DATABASE / 03_REGION_LIBRARY / 04_COMMENT_DATABASE / 06_SCORE_MODEL / data_dict/ / raw/ |
| `03_AI_AGENT/` | 🟡 初步 | agents/comment_analyzer / agents/lead_scoring_agent / agents/customer_finder_agent |
| `04_CONTENT/` | 🔴 空 | — |
| `05_CUSTOMER_LEADS/` | 🟡 初步 | FIELD_MAPPING_RULE.md / comment_asset_library.csv（待填充） |
| `05_CUSTOMER_CRM/` | 🟡 初步 | leads/（含 lead_schema.md）/ follow_ups/ |
| `06_CASE_LIBRARY/` | 🔴 空 | — |
| `07_FINANCE/` | 🔴 空 | — |
| `08_SYSTEM/` | 🟡 初步 | scripts/（collector_base.py / config_loader.py / data_cleaner.py 占位） |
| `09_AI_OPERATION/` | 🔴 空 | — |
| `10_AI_AUTOMATION_ENGINE/` | 🟡 初步 | engine.py / run_pipeline.py / workflows/ / orchestrator/ / triggers/ / tests/ |
| `11_AI_PRODUCTIZATION/` | 🔴 空 | — |
| `12_AI_RUNTIME/` | 🔴 空 | — |
| `99_BACKUP/` | 🟢 就绪 | context_backup/ / chat_history/ |

---

## 四、Agent 状态

| Agent | 路径 | agent.yml | README | 状态 |
|-------|------|:--------:|:------:|:----:|
| comment_analyzer | `03_AI_AGENT/agents/comment_analyzer/` | ✅ V1.0 | ✅ | 已定义 |
| lead_scoring_agent | `03_AI_AGENT/agents/lead_scoring_agent/` | ✅ V2.1 | ✅ | 已定义（五维评分） |
| customer_finder_agent | `03_AI_AGENT/agents/customer_finder_agent/` | ✅ V1.0 | ✅ | 已定义 |
| comment_collector | `03_AI_AGENT/agents/comment_collector/` | ⬜ | ⬜ | 设计完成，待实现 |

---

## 五、Automation Engine 状态

| 组件 | 路径 | 状态 |
|------|------|:--:|
| Engine 入口 | `10_AI_AUTOMATION_ENGINE/engine.py` | ✅ 有代码 |
| Pipeline 执行 | `10_AI_AUTOMATION_ENGINE/run_pipeline.py` | ✅ 有代码 |
| Workflow：评论转客户 | `10_AI_AUTOMATION_ENGINE/workflows/comment_to_lead_pipeline.yml` | ✅ V1.1 |
| Orchestrator | `10_AI_AUTOMATION_ENGINE/orchestrator/step_executor.py` | ✅ 有代码 |
| Triggers | `10_AI_AUTOMATION_ENGINE/triggers/event_bus.py` | ✅ 有代码 |
| Tests | `10_AI_AUTOMATION_ENGINE/tests/` | ✅ 有 pytest + fixtures |
| Scheduler | `10_AI_AUTOMATION_ENGINE/scheduler/` | ❌ 空 |

---

## 六、客户生命周期架构

```
公开数据（平台评论 / 内容互动 / 竞品评论）
    │
    ▼
05_CUSTOMER_LEADS（AI 客户发现层）
    ├── comment_asset_library.csv    # 评论资产库
    ├── leads_master.csv             # 客户线索主表（S/A 级）
    ├── nurture_pool.csv             # 培育池（B 级）
    ├── FIELD_MAPPING_RULE.md        # 字段映射
    └── scoring_results/             # 评分明细
    │
    ▼
05_CUSTOMER_CRM（销售管理层）
    ├── leads/hot/                   # S 级，立即跟进
    ├── leads/qualified/             # A/B 级，重点培育
    ├── leads/raw/                   # C 级，分析保存
    ├── customers/                   # 正式客户
    └── follow_ups/                  # 跟进任务
```

---

## 七、当前待办（优先级排序）

| 优先级 | 任务 | 目标目录 | 说明 |
|:------:|------|---------|------|
| 🔴 P0 | 测试评论数据准备 | `10_AI_AUTOMATION_ENGINE/tests/fixtures/` | 城市小区光伏客户样本 ≥ 20 条 |
| 🔴 P0 | Comment Analyzer 运行验证 | `03_AI_AGENT/agents/comment_analyzer/` | 端到端：数据→分析→输出 |
| 🔴 P0 | Lead Scoring 运行验证 | `03_AI_AGENT/agents/lead_scoring_agent/` | 端到端：评分→S/A/B/C→CRM 路由 |
| 🔴 P0 | Pipeline 端到端验证 | `10_AI_AUTOMATION_ENGINE/` | comment_to_lead_pipeline 全链路 |
| 🔴 P0 | CRM 同步测试 | `05_CUSTOMER_CRM/leads/` | S→hot / A/B→qualified / C→raw |
| 🟡 P1 | 真实平台数据采集 | `02_DATA/raw/` | 抖音优先 |
| 🟡 P1 | comment_collector Agent 实现 | `03_AI_AGENT/agents/comment_collector/` | 采集链路设计已完成 |
| 🟢 P2 | 内容自动化生产 | `04_CONTENT/` | — |

---

## 八、变更记录

> 按 PV_OS_AI_RULES.md 第十章要求，记录所有重大变更。

| 日期 | 变更类型 | 变更内容 | 影响范围 | 操作者 |
|------|---------|---------|---------|--------|
| 2026-07-11 | 新增 | 创建全部 14 个一级目录 | 全局 | Codex |
| 2026-07-11 | 新增 | PV_OS_DIRECTORY_MAP.md V1.0 | 全局 · 文件存放规则 | Codex |
| 2026-07-11 | 新增 | PV_OS_AI_RULES.md V1.0 | 全局 · AI 协作规则 | Codex |
| 2026-07-11 | 新增 | PV_OS_ARCHITECTURE.md V1.0 | 全局 · 系统架构 | Codex |
| 2026-07-11 | 新增 | PV_OS_PROJECT_STATUS.md V1.0 | 全局 · 项目状态跟踪 | Codex |
| 2026-07-13 | 新增 | Comment Analyzer Agent V1.0 | 03_AI_AGENT | Codex |
| 2026-07-13 | 新增 | Lead Scoring Agent V2.1 | 03_AI_AGENT | Codex |
| 2026-07-13 | 新增 | Customer Finder Agent V1.0 | 03_AI_AGENT | Codex |
| 2026-07-13 | 新增 | PV_OS Boot Context System V2 | 全局 | Codex |
| 2026-07-13 | 新增 | 7 份采集链路设计文档 | 根目录 | Codex |
| 2026-07-14 | 更新 | PV_OS_PROJECT_STATUS.md V1.0 → V1.1 | 00_SYSTEM | Codex |
| 2026-07-14 | 新增 | 05_CUSTOMER_LEADS 目录（AI 客户发现层） | 全局 · 客户生命周期两层架构 | Codex |
| 2026-07-14 | 更新 | PV_OS_DIRECTORY_MAP.md V1.0 → V1.1 | 00_SYSTEM · 新增 LEADS 层 | Codex |
| 2026-07-14 | 更新 | PV_OS_PROJECT_STATUS.md V1.1 → V1.2 | 00_SYSTEM · Phase 1.7 评论潜客发现链路固化 | Codex |

---

## 九、已知问题 / 阻塞项

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| 1 | `02_DATA/raw/` 为空，无真实评论数据 | 核心链路未端到端验证 | 📋 计划中 |
| 2 | `03_AI_AGENT/agents/comment_collector/` 未实现 | 采集链路代码层缺失 | 📋 设计完成，待实现 |
| 3 | 抖音/小红书 API 访问策略待确认 | 数据采集方案依赖此决策 | ⏳ 待调研 |
| 4 | comment_analyzer 与 lead_scoring_agent 字段映射存在 5 个严重缺口 | Agent 间数据传递 | 📋 审计完成（FIELD_MAPPING_AUDIT.md） |
| 5 | Pipeline 尚未端到端验证 | 全链路未跑通 | 📋 依赖测试数据就绪 |

---

## 十、下一步行动

```
本周目标：完成 P0 验证任务

1. [ ] 准备 20+ 条城市小区光伏客户测试评论数据
2. [ ] Comment Analyzer 端到端运行验证
3. [ ] Lead Scoring Agent 端到端运行验证
4. [ ] comment_to_lead_pipeline 全链路验证
5. [ ] CRM 同步测试（S→hot / A/B→qualified / C→raw）
6. [ ] 补充 comment_analyzer agent.yml 的 output.schema
```

---

## 十一、版本记录

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| V1.0 | 2026-07-11 | 初始版本：项目状态首次建档，Phase 1 基础设施搭建进行中 |
| V1.1 | 2026-07-14 | 状态同步：Phase 1.6、3 个 Agent 状态、Automation Engine 骨架、CRM 结构 |
| V1.2 | 2026-07-14 | 架构升级：Phase 1.7 评论潜客发现链路固化、新增 05_CUSTOMER_LEADS 层、两层架构分离、Pipeline 链路就绪记录 |




# PV_OS V2.0战略决策


设计文件:

00_SYSTEM/PROJECT_MEMORY/PV_OS_DESIGN_DECISION_LOG_2026-07-15.md




# 当前 Agents


03_AI_AGENT/agents/customer_finder_agent/agent.yml
03_AI_AGENT/agents/comment_collector_agent/agent.yml
03_AI_AGENT/agents/lead_scoring_agent/agent.yml
03_AI_AGENT/agents/comment_analyzer/agent.yml
03_AI_AGENT/agents/competitor_account_agent/agent.yml




# 当前 Workflow


10_AI_AUTOMATION_ENGINE/workflows/comment_to_lead_pipeline.yml




# AI执行规则


进入项目必须读取:


00_SYSTEM/PV_OS_DIRECTORY_MAP.md


00_SYSTEM/PV_OS_AI_RULES.md


00_SYSTEM/PV_OS_PROJECT_STATUS.md


00_SYSTEM/PROJECT_MEMORY/PV_OS_DESIGN_DECISION_LOG*.md




禁止:


- 修改无关文件

- 偏离业务方向

- 编造数据

- 创建未定义目录



# 下一步


继续当前 Phase 开发。


