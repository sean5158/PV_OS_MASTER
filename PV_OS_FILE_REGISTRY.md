# PV_OS_FILE_REGISTRY

版本：V1.0
日期：2026-07-13
用途：PV_OS 项目完整文件注册表，按系统层级分类，作为 AI 进入项目后的文件导航索引。

> 本注册表基于全项目扫描生成（`find . -name "*.md" -o -name "*.yml" -o -name "*.yaml"`），
> 排除 .venv/、.pytest_cache/、backup/history/ 等非项目源文件目录。
> 功能说明根据各文件实际内容和 README 提取。

---

## 文件统计

| 指标 | 数值 |
|------|:----:|
| 全项目 .md/.yml/.yaml 文件数（含备份/缓存） | 121 |
| 排除 .venv/ + .pytest_cache/ | -2 |
| 排除 backup/history/ 历史备份 | -48 |
| 项目有效文件总数 | **71** |
| 一级目录数 | 14 |
| 包含 .md 文件 | 60 |
| 包含 .yml/.yaml 文件 | 11 |

---

## 分类 A：启动必读文件

AI 进入 PV_OS 项目后必须首先读取的文件，用于建立项目全局认知和上下文。

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| A1 | PV_OS_BOOTSTRAP.md | 项目根 | md | 项目身份入口：定义 Codex 角色、启动读取顺序、开发原则、禁止行为 |
| A2 | PV_OS_MASTER_CONTEXT.md | 项目根 | md | 项目全局上下文入口：10 板块汇总项目定位、商业目标、客户模型、评分规则、CRM 流转、当前状态、AI 读取顺序 |
| A3 | PV_OS_BACKUP_MAP_V1.0.md | 项目根 | md | 项目恢复导航文件：系统架构、已完成模块、当前开发位置、AI Agent 状态 |
| A4 | backup/PV_OS_BACKUP_MAP_V1.0.md | `backup/` | md | （与 A3 同步镜像） |
| A5 | backup/PV_OS_BUSINESS_TREE.md | `backup/` | md | 核心业务流程图：评论进入 → AI 分析 → 客户评分 → CRM 分级 → 销售跟进 |
| A6 | backup/PV_OS_RULE_INDEX.md | `backup/` | md | 规则索引表：汇总所有系统规则、数据规则、CRM 规则、AI Agent 的文件路径 |
| A7 | backup/PV_OS_STATUS.md | `backup/` | md | 项目状态追踪：已完成模块清单、当前开发位置、下一步计划、最近备份时间 |
| A8 | backup/PV_OS_CODEX_STATUS.md | `backup/` | md | Codex 专属状态：Codex 身份、当前任务、最近读取文件、修改记录、测试记录、阻塞问题 |

---

## 分类 B：系统治理规则

存放于 `00_SYSTEM/`，定义项目架构、AI 协作规范、开发约束、环境配置和项目状态。

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| B1 | PV_OS_AI_RULES.md | `00_SYSTEM/` | md | AI 协作规则 V1.0：四平台角色分工（ChatGPT/Codex Desktop/Codex CLI/DeepSeek）、AI 执行流程、文件管理规则、偏差纠正机制 |
| B2 | PV_OS_GOVERNANCE_RULES.md | `00_SYSTEM/` | md | 项目治理规范 V1.0：最高目标、商业价值优先原则、P0-P4 优先级、模块开发审批规则、商业验证原则 |
| B3 | PV_OS_CODEX_RULES.md | `00_SYSTEM/` | md | Codex 开发约束：启动必读文件清单、允许/禁止修改目录、状态记录要求、业务链路保护 |
| B4 | PV_OS_ARCHITECTURE.md | `00_SYSTEM/` | md | 系统架构文档 V1.0：四层架构（采集→数据→AI→业务）、模块交互关系、数据流向、技术选型 |
| B5 | PV_OS_DEVELOPMENT_ROADMAP.md | `00_SYSTEM/` | md | 开发路线图：Phase1-4 里程碑、模块就绪度矩阵、优先级排序的待办清单 |
| B6 | PV_OS_DIRECTORY_MAP.md | `00_SYSTEM/` | md | 目录地图：14 个一级目录的用途说明、文件归属决策树、命名规范 |
| B7 | PV_OS_ENVIRONMENT.md | `00_SYSTEM/` | md | 开发环境配置：运行环境、依赖、工具链说明 |
| B8 | PV_OS_PROJECT_STATUS.md | `00_SYSTEM/` | md | 项目状态看板：各模块完成进度、已知问题、变更记录 |
| B9 | PV_OS_RECOVERY_GUIDE.md | `00_SYSTEM/` | md | 项目恢复指南：环境迁移、账号切换后的恢复流程 |

---

## 分类 C：业务规则文件

定义 PV_OS 核心商业逻辑，包括关键词策略、竞品发现、内容生产、运营规则、商业验证规范。

### C1：关键词与竞品发现

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| C1.1 | KEYWORD_STRATEGY.md | `02_DATA/01_KEYWORD_LIBRARY/` | md | 关键词发现与扩展策略 V1.0：八源关键词体系、五维评分（100 分）、S/A/B/C 分级、搜索投放策略 |
| C1.2 | COMPETITOR_DISCOVERY_ALGORITHM.md | `02_DATA/02_COMPETITOR_DATABASE/` | md | 竞品账号自动发现算法 V1.0：有效竞品定义、排除范围、关键词驱动发现、自扩展循环 |
| C1.3 | COMPETITOR_SCORE_RULE.md | `02_DATA/02_COMPETITOR_DATABASE/` | md | 竞品账号评分规则 V1.0：六维评分（100 分）、九步 AI 判断流程、S/A/B/C 等级划分 |
| C1.4 | README.md | `02_DATA/01_KEYWORD_LIBRARY/` | md | 关键词库说明 |
| C1.5 | README.md | `02_DATA/02_COMPETITOR_DATABASE/` | md | 竞品数据库说明 |

### C2：内容与运营

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| C2.1 | README.md | `04_CONTENT/` | md | AI 内容智能生产系统 V1.0：策略→脚本→生成→发布→分析的内容闭环 |
| C2.2 | README.md | `09_AI_OPERATION/` | md | AI 运营中心 V1.0：评论管理、竞品监控、市场洞察、平台管理、任务系统 |
| C2.3 | README.md | `09_AI_OPERATION/competitors/` | md | 竞品智能分析系统 V1.0：竞品数据库→监控→分析→报告的闭环 |
| C2.4 | README.md | `09_AI_OPERATION/insights/` | md | AI 市场洞察引擎 V1.0：市场趋势、客户需求、内容方向、销售机会发现 |
| C2.5 | README.md | `09_AI_OPERATION/tasks/` | md | AI 任务管理系统 V1.0：任务生成→分配→执行→反馈 |
| C2.6 | config.yml | `09_AI_OPERATION/platforms/douyin/` | yml | 抖音平台运营配置 |
| C2.7 | config.yml | `09_AI_OPERATION/platforms/xiaohongshu/` | yml | 小红书平台运营配置 |
| C2.8 | config.yml | `09_AI_OPERATION/platforms/kuaishou/` | yml | 快手平台运营配置 |
| C2.9 | config.yml | `09_AI_OPERATION/platforms/wechat_video/` | yml | 视频号平台运营配置 |

### C3：商业验证

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| C3.1 | README.md | `13_BUSINESS_VALIDATION/` | md | 商业验证阶段 V1.0：主动获客 + 被动获客两大实验、核心验证指标 |
| C3.2 | README.md | `13_BUSINESS_VALIDATION/outbound_customer_finding/` | md | 主动获客实验 V1.0：A/B/C 级客户定义、数据来源、AI 筛选规则、实验指标 |
| C3.3 | customer_filter.yml | `13_BUSINESS_VALIDATION/outbound_customer_finding/filters/` | yml | 四川城市高价值光伏客户过滤规则：target 包含/排除区域和物业类型 |
| C3.4 | customer_scoring.yml | `13_BUSINESS_VALIDATION/outbound_customer_finding/scoring/` | yml | 客户评分配置：正向加分（别墅+30、安装咨询+20）、负向扣分（农村免费-50、招商-80） |
| C3.5 | validation_report_001.md | `13_BUSINESS_VALIDATION/outbound_customer_finding/results/` | md | TEST-001 主动获客链路验收报告：6 项测试全部通过 |

---

## 分类 D：数据规则文件

定义数据采集、存储、清洗、生命周期管理的规则和标准结构。

### D1：评论数据规则

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| D1.1 | COMMENT_ANALYZER_RULE.md | `02_DATA/04_COMMENT_DATABASE/` | md | 评论潜客识别算法 V1.1：S/A/B/C 评论分级、评论时间价值窗口（7 天/30 天/180 天）、区域模糊识别、房屋场景识别、农村客户分层 |
| D1.2 | COMMENT_TIME_AND_MATCH_RULE.md | `02_DATA/04_COMMENT_DATABASE/` | md | 评论时间资产与区域模糊识别规则：四级时间窗口策略、区域三级识别优先级（文字>IP>昵称>资料） |
| D1.3 | COMMENT_DATA_LIFECYCLE_RULE.md | `02_DATA/04_COMMENT_DATABASE/` | md | 评论数据生命周期规则：数据各阶段流转、保留与清理策略 |
| D1.4 | README.md | `02_DATA/04_COMMENT_DATABASE/` | md | 评论数据库说明 |
| D1.5 | COMMENT_ANALYZER_RULE_V1.0_backup.md | `02_DATA/04_COMMENT_DATABASE/` | md | 评论分析规则 V1.0 历史备份 |

### D2：区域数据规则

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| D2.1 | REGION_MASTER.md | `02_DATA/03_REGION_LIBRARY/` | md | 核心市场行政区域主数据 V1.0：川渝黔三级区域结构、P0 成都/P1 四川+重庆/P2 贵州优先级 |
| D2.2 | REGION_MATCH_RULE.md | `02_DATA/03_REGION_LIBRARY/` | md | 客户区域模糊识别规则 V1.0：四级识别精度（区县→城市→省→口语）、区域评分映射表 |
| D2.3 | REGION_MASTER_backup.md | `02_DATA/03_REGION_LIBRARY/` | md | 区域主数据备份 |

### D3：数据标准与映射

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| D3.1 | comment_schema.md | `02_DATA/data_dict/` | md | 评论数据标准结构 V1.0：基础字段、来源字段、AI 分析字段、客户标签字段、处理状态定义 |
| D3.2 | FIELD_MAPPING_RULE.md | `05_CUSTOMER_LEADS/` | md | 客户数据字段映射规则 V1.0：评论采集→AI 分析→评分模型→CRM 的全链路字段映射、等级转换（S→3/A→2/B→1/C→0） |
| D3.3 | README.md | `02_DATA/` | md | 数据资产层总说明：raw/→processed/→datasets/→exports/ 数据流向、文件命名规范 |
| D3.4 | README.md | `02_DATA/03_PLATFORM_DATA/` | md | 平台原始数据目录说明 |
| D3.5 | README.md | `02_DATA/05_CUSTOMER_LEADS/` | md | 客户线索出口库说明：leads_master.csv/nurture_pool.csv/comment_asset_library.csv 三层结构 |
| D3.6 | README.md | `05_CUSTOMER_LEADS/` | md | 客户线索出口库说明（承接评论分析→CRM 的数据） |

---

## 分类 E：客户评分规则

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| E1 | CUSTOMER_SCORE_MODEL.md | `02_DATA/06_SCORE_MODEL/` | md | 客户价值评分模型 V1.0：五维评分体系（需求强度 40+区域 20+房屋 20+时间 10+真实性 10）、S/A/B/C 四级划分、负向修正规则、农村客户动态修正 V1.1、人工反馈闭环、版本管理 |
| E2 | CUSTOMER_SCORE_MODEL_V1.0_backup.md | `02_DATA/06_SCORE_MODEL/` | md | 评分模型 V1.0 历史备份 |
| E3 | README.md | `02_DATA/06_SCORE_MODEL/` | md | 评分模型目录说明 |

---

## 分类 F：CRM 规则

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| F1 | lead_schema.md | `05_CUSTOMER_CRM/leads/` | md | CRM 客户线索标准结构 V1.0：基础信息、客户信息、AI 评分、销售状态四大类字段定义 |
| F2 | FIELD_MAPPING_RULE.md | `05_CUSTOMER_LEADS/` | md | 同 D3.2，承接数据→CRM 字段映射 |

---

## 分类 G：AI Agent 文件

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| G1 | agent.yml | `03_AI_AGENT/agents/comment_analyzer/` | yml | 评论分析 Agent 配置：输入源（02_DATA/raw/）、分析维度（客户类型/意向等级/评分）、输出路径（05_CUSTOMER_CRM/leads/） |
| G2 | README.md | `03_AI_AGENT/agents/comment_analyzer/` | md | 评论分析 Agent 说明：4 类分析任务、输入/输出定义 |
| G3 | agent.yml | `03_AI_AGENT/agents/customer_finder_agent/` | yml | 主动客户发现 Agent 配置：分析规则（客户类型/意向等级/评分优先级）、输出结构（lead_id/score/tags/next_action）、关联商业验证模块 |
| G4 | README.md | `03_AI_AGENT/agents/customer_finder_agent/` | md | 主动客户发现 Agent 说明：连接 13_BUSINESS_VALIDATION 的评分与过滤规则 |
| G5 | agent.yml | `03_AI_AGENT/agents/lead_scoring_agent/` | yml | 客户评分 Agent 配置（开发中）：五维输出结构（demand/region/housing/time/authenticity_score）、S/A/B/C 路由规则、qualified_leads 阈值 |
| G6 | README.md | `03_AI_AGENT/agents/lead_scoring_agent/` | md | 客户评分 Agent 说明：输入字段、评分逻辑、三级路由（hot/qualified/raw） |

---

## 分类 H：自动化流程文件

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| H1 | README.md | `10_AI_AUTOMATION_ENGINE/` | md | AI 自动化引擎 V1.0：Orchestrator/Scheduler/Triggers/Workflows 四模块，核心流程（评论→分析→评分→CRM→销售任务） |
| H2 | comment_to_lead_pipeline.yml | `10_AI_AUTOMATION_ENGINE/workflows/` | yml | 评论转客户自动化管道：新评论采集→comment_analyzer→lead_scoring_agent→CRM 入库 |

---

## 分类 I：Backup 恢复文件

| # | 文件名 | 路径 | 类型 | 功能说明 |
|:-:|--------|------|:--:|---------|
| I1 | PV_OS_DEV_LOG.md | `99_BACKUP_ENGINE/chat_history/2026-07-13/` | md | 开发日志：2026-07-13 开发主题（Backup Engine）、当日完成项、下一步计划 |
| I2 | 最新快照合集 | `backup/latest/` | md | 最新备份快照：BACKUP_MAP / BUSINESS_TREE / CODEX_STATUS / RULE_INDEX / STATUS / DEV_LOG |
| I3 | 上下文备份合集 | `99_BACKUP/context_backup/` | md | 系统规则上下文备份：AI_RULES / ARCHITECTURE / DIRECTORY_MAP / MASTER_CONTEXT / PROJECT_STATUS |

---

## 推荐 AI 启动读取顺序

### 首次进入项目

| 顺序 | 分类 | 文件 | 阅读重点 |
|:----:|:----:|------|---------|
| 1 | A | `PV_OS_BOOTSTRAP.md` | 角色定义、开发原则、禁止行为 |
| 2 | A | `PV_OS_MASTER_CONTEXT.md` | 10 板块全局认知（定位、目标、客户模型、评分、CRM、状态） |
| 3 | A | `backup/PV_OS_BACKUP_MAP_V1.0.md` | 系统架构、已完成模块、当前开发位置 |
| 4 | A | `backup/PV_OS_BUSINESS_TREE.md` | 核心业务流 |
| 5 | A | `backup/PV_OS_RULE_INDEX.md` | 所有规则文件路径速查 |
| 6 | A | `backup/PV_OS_STATUS.md` | 项目当前进度 |
| 7 | A | `backup/PV_OS_CODEX_STATUS.md` | Codex 当前任务与记忆 |
| 8 | B | `00_SYSTEM/PV_OS_CODEX_RULES.md` | 允许/禁止修改的目录、任务流程 |
| 9 | B | `00_SYSTEM/PV_OS_AI_RULES.md` | 四平台 AI 分工 |
| 10 | B | `00_SYSTEM/PV_OS_GOVERNANCE_RULES.md` | 项目治理优先级 |

### 恢复上下文后按需深入

| 如需开发/理解 | 深入分类 | 核心文件 |
|-------------|:------:|---------|
| 评论分析 / 客户识别 | D1 | `COMMENT_ANALYZER_RULE.md`、`COMMENT_TIME_AND_MATCH_RULE.md` |
| 客户评分 / 等级划分 | E | `CUSTOMER_SCORE_MODEL.md` |
| 区域匹配 / 市场覆盖 | D2 | `REGION_MASTER.md`、`REGION_MATCH_RULE.md` |
| CRM 入库 / 线索处理 | F | `lead_schema.md`、`FIELD_MAPPING_RULE.md` |
| Agent 开发 / 配置 | G | 各 Agent 的 `agent.yml` + `README.md` |
| 自动化管道 | H | `comment_to_lead_pipeline.yml` |
| 竞品发现 | C1 | `COMPETITOR_DISCOVERY_ALGORITHM.md`、`COMPETITOR_SCORE_RULE.md` |
| 商业验证 / 测试 | C3 | `validation_report_001.md`、`customer_filter.yml` |

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-13 | 全项目扫描生成，71 个有效文件，9 大分类体系 |

