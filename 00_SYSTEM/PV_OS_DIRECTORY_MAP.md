B# PV_OS 目录地图 V1.1

> 光伏行业 AI 自动化运营系统 · 目录结构定义与文件存放规范
>
> 最后更新：2026-07-14

---

## 一、项目定位

PV_OS 不是传统软件工程项目，而是一个**光伏行业 AI 自动化运营系统**。其核心是通过 AI Agent + 数据采集 + 内容生产 + CRM 跟踪，实现从"潜在客户发现 → 内容引流 → 客户评分 → 销售转化"的全链路自动化。

客户生命周期分为两层：

```
公开数据（平台评论 / 内容互动 / 竞品评论）
    │
    ▼
05_CUSTOMER_LEADS（AI 客户发现层）
    │  负责：AI 发现 → 评论线索 → 评分结果 → 培育池
    │
    ▼
05_CUSTOMER_CRM（销售管理层）
    │  负责：销售跟进 → 联系记录 → 商机管理 → 成交客户
```

本目录地图定义：
1. 每个一级目录的业务用途与边界
2. 数据 / 文档 / 代码 / 配置 / 模型五类资产的存放位置
3. AI 读取文件的优先级规则
4. 新增文件时判断存放位置的决策流程

---

## 二、目录树总览

```
PV_OS_MASTER/
├── 00_SYSTEM/                   # 系统级规则与元文档
├── 01_PROJECT_MANAGEMENT/       # 项目管理
├── 02_DATA/                     # 数据资产
├── 03_AI_AGENT/                 # AI Agent 定义
├── 04_CONTENT/                  # 内容生产
├── 05_CUSTOMER_LEADS/           # AI 客户发现层（线索评分、培育池）
├── 05_CUSTOMER_CRM/             # 客户关系管理（销售管理层）
├── 06_CASE_LIBRARY/             # 案例库
├── 07_FINANCE/                  # 财务
├── 08_SYSTEM/                   # 系统技术实现
├── 09_AI_OPERATION/             # AI 运营
├── 10_AI_AUTOMATION_ENGINE/     # AI 自动化引擎
├── 11_AI_PRODUCTIZATION/        # AI 产品化与商业包装
├── 12_AI_RUNTIME/               # AI 运行时
└── 99_BACKUP/                   # 备份归档
```

---

## 三、一级目录详解

### 00_SYSTEM —— 系统级规则与元文档

存放整个 PV_OS 项目的**元信息**，是 AI Agent 进入项目时首先读取的入口。

- `PV_OS_DIRECTORY_MAP.md` — 本文件，目录地图
- `PV_OS_ARCHITECTURE.md` — 系统架构设计文档
- `PV_OS_AI_RULES.md` — AI Agent 行为规则与约束
- `PV_OS_PROJECT_STATUS.md` — 项目当前状态、进度、待办事项

**规则：** 任何全局性、跨模块的规则、架构决策、项目状态，均放此处。本目录不存放代码、数据、配置。

---

### 01_PROJECT_MANAGEMENT —— 项目管理

存放项目计划、任务看板、里程碑、会议纪要、SOP 流程文档等项目管理资料。

**对应业务：** 全业务线

典型子目录结构（按需创建）：
- `plans/` — 项目计划与路线图
- `tasks/` — 任务拆分与跟踪
- `meetings/` — 会议纪要
- `sops/` — 标准操作流程文档

---


## 02_DATA —— AI 获客数据资产层


定位：

PV_OS 的核心数据资产层。

存放：

- 原始采集数据
- 结构化业务数据
- AI分析数据
- 客户线索数据
- 模型训练数据


这是 AI 主动获客系统的数据燃料。


---

## 对应业务


### 1. 内容生态数据

来源：

- 抖音
- 快手
- 视频号
- 小红书


包括：

- 视频数据
- 账号数据
- 评论数据
- 互动数据



### 2. 竞品数据

目录：

02_COMPETITOR_DATABASE


包括：

- 个人光伏内容博主
- 光伏安装公司
- 光伏品牌厂家
- 行业相关账号


用途：

发现客户来源。


### 3. 评论客户数据

目录：

04_COMMENT_DATABASE


包括：

- 评论原文
- 用户区域
- 用户需求
- 房屋场景
- 意向等级


用途：

评论转潜客。


### 4. AI评分数据

目录：

06_SCORE_MODEL


包括：

- 竞品评分模型
- 评论客户评分
- Lead评分模型



---

## 典型目录结构


raw/

原始采集数据：

- JSON
- CSV
- 平台接口数据


processed/

清洗后的结构化数据：

- 账号表
- 评论表
- 用户标签表


datasets/

AI训练及评估数据：

- 分类数据
- 标注数据


exports/

业务输出：

- 客户名单
- 分析报告


data_dict/

字段定义：

- 数据结构说明
- 标签定义



---

## 核心原则


数据与规则分离。


规则：

存放：

00_SYSTEM


数据：

存放：

02_DATA


AI模型：

读取：

规则 + 数据


形成：

发现

分析

评分

获客

闭环。


END

---

### 03_AI_AGENT —— AI Agent 定义

存放 AI Agent 的**角色定义、Prompt 模板、行为策略、决策逻辑**。

**对应业务：**
- 评论区潜在客户识别（业务6）
- AI 客户评分（业务7）

典型子目录结构：
- `agents/` — 各 Agent 角色定义（如 `comment_analyzer`、`lead_scoring_agent`）
- `prompts/` — Prompt 模板库
- `strategies/` — 决策策略与规则引擎
- `evals/` — Agent 输出质量评估

---

### 04_CONTENT —— 内容生产

存放 AI 生成或人工创作的**内容资产**：视频脚本、图文素材、爆款拆解分析、发布排期等。

**对应业务：**
- 爆款视频拆解（业务9）
- AI 内容生产（业务10）

典型子目录结构：
- `scripts/` — 视频脚本
- `materials/` — 图文素材与模板
- `viral_analysis/` — 爆款视频拆解分析报告
- `calendar/` — 内容发布排期
- `outputs/` — 成品内容（视频、图文）

---

### 05_CUSTOMER_LEADS —— AI 客户发现层

存放 AI 从公开数据中发现的潜在客户线索。这是 PV_OS 客户生命周期的**第一层**：从原始数据中通过 AI 识别潜在客户。

**定位：** AI 发现层 — 在销售介入之前，由 AI 完成客户线索的发现、评分和分类。

**数据来源：**
- 竞品评论区分析结果
- 内容互动数据分析结果
- 平台公开数据挖掘结果
- 评论资产库中的潜在信号

**生命周期：**

```
公开数据（平台评论 / 内容互动 / 竞品评论）
    │
    ▼
05_CUSTOMER_LEADS（AI 客户发现层）
    ├── comment_asset_library.csv   # 评论资产库（全量保存）
    ├── leads_master.csv            # 客户线索主表（S/A 级）
    ├── nurture_pool.csv            # 培育池（B 级）
    ├── FIELD_MAPPING_RULE.md       # 字段映射规则（数据 → CRM）
    └── scoring_results/            # 评分明细
    │
    ▼ 评分完成
05_CUSTOMER_CRM（销售管理层）
```

**核心字段（从 AI 分析结果到 CRM 线索的映射）：**

| AI 分析字段 | LEADS 字段 | CRM 字段 |
|-----------|----------|---------|
| platform | platform | location |
| province / city / district | province / city / district | location |
| housing_type | housing_type | house_type |
| demand_signals | tags | tags |
| total_score | ai_score | lead_score |
| lead_grade | priority | intent_level |

> 引用：`05_CUSTOMER_LEADS/FIELD_MAPPING_RULE.md` V1.0

---

### 05_CUSTOMER_CRM —— 销售管理层

存放客户信息、跟进记录、客户分级、销售漏斗等 CRM 相关数据与流程。这是 PV_OS 客户生命周期的**第二层**：销售团队对已评分的客户线索进行跟进和转化。

**定位：** 销售管理层 — 接收 05_CUSTOMER_LEADS 输出的评分结果，由销售团队进行人工跟进。

**对应业务：**
- 城市家庭光伏客户开发（业务1）
- 别墅 / 叠拼 / 花园洋房 / 露台 / 阳光房需求（业务2）
- 小商业场景：民宿、酒店、棋牌室、茶楼、美容院（业务3）
- CRM 客户跟踪（业务8）

典型子目录结构：
- `leads/` — 销售线索（hot/、qualified/、raw/）
- `customers/` — 正式客户档案
- `follow_ups/` — 跟进记录
- `funnel/` — 销售漏斗分析
- `tags/` — 客户标签体系（场景类型、房产类型等）

**LEADS 与 CRM 的边界：**

| 05_CUSTOMER_LEADS | 05_CUSTOMER_CRM |
|-------------------|----------------|
| ✅ AI 发现 | ✅ 销售跟进 |
| ✅ 评论线索 | ✅ 联系记录 |
| ✅ 评分结果 | ✅ 商机管理 |
| ✅ 培育池 | ✅ 成交客户 |
| ❌ 不涉及销售动作 | ❌ 不涉及 AI 评分 |

---

### 06_CASE_LIBRARY —— 案例库

存放光伏项目**实装案例**：方案设计、效果图、施工记录、客户评价。

**对应业务：**
- 别墅 / 叠拼 / 花园洋房 / 露台 / 阳光房项目案例（业务2）
- 小商业场景项目案例（业务3）

典型子目录结构：
- `residential/` — 住宅类案例（别墅、叠拼、洋房、阳光房、露台）
- `commercial/` — 小商业案例（民宿、酒店、棋牌室、茶楼等）
- `designs/` — 方案设计图、系统图
- `photos/` — 实拍照片素材

---

### 07_FINANCE —— 财务

存放报价模板、成本核算、合同管理、财务报表等财务相关数据。

**对应业务：** 报价管理、合同管理

典型子目录结构：
- `quotes/` — 报价模板与历史报价
- `costs/` — 成本数据
- `contracts/` — 合同模板与签约记录
- `reports/` — 财务报表

---

### 08_SYSTEM —— 系统技术实现

存放系统级的技术代码、配置文件、数据库 Schema、运维脚本等。

**规则：** 不与具体业务绑定的通用技术代码放此处。与特定业务绑定的代码归入对应业务目录。

典型子目录结构：
- `src/` — 核心源代码
- `config/` — 系统级配制
- `scripts/` — 运维 / 部署 / 数据维护脚本
- `db/` — 数据库 Schema 与迁移

---

### 09_AI_OPERATION —— AI 运营

存放运营策略、竞品分析报告、平台采集配置等 AI 运营相关资产。

**对应业务：**
- 竞品账号自动发现（业务4）
- 平台采集策略（业务5）
- 运营分析与洞察

典型子目录结构：
- `competitors/` — 竞品分析报告
- `platforms/` — 各平台采集配置与策略
- `comments/` — 评论区运营分析
- `insights/` — AI 运营洞察与周报

---

### 10_AI_AUTOMATION_ENGINE —— AI 自动化引擎

存放 AI 工作流定义、任务编排、事件触发、定时调度等自动化相关代码。

**对应业务：**
- 自动化 Agent 编排（业务11）
- 评论 → 客户 → CRM 全链路自动化

典型子目录结构：
- `workflows/` — AI 工作流定义（YAML/JSON）
- `orchestrator/` — 任务编排与执行
- `triggers/` — 事件触发规则
- `scheduler/` — 定时调度
- `tests/` — 自动化测试

---

### 11_AI_PRODUCTIZATION —— AI 产品化与商业包装

存放产品定义、定价策略、营销材料、交付物等商业相关资产。

**对应业务：** 产品化、营销推广

典型子目录结构：
- `products/` — 产品定义与规格
- `pricing/` — 定价策略
- `marketing/` — 营销材料
- `deliverables/` — 客户交付物模板

---

### 12_AI_RUNTIME —— AI 运行时

存放 AI 模型权重、推理代码、依赖配置、运行日志等运行时环境。

典型子目录结构：
- `models/` — AI 模型权重文件
- `inference/` — 推理服务代码
- `deps/` — 依赖清单（requirements.txt 等）
- `logs/` — 运行日志

---

### 99_BACKUP —— 备份归档

存放废弃文档、历史版本、环境迁移备份等归档内容。不参与日常开发。

---

## 四、五类资产存放矩阵

| 资产类型 | 存放位置 | 边界说明 |
|---------|---------|---------|
| **文档** | `00_SYSTEM/`、`01_PROJECT_MANAGEMENT/`、`04_CONTENT/`、`09_AI_OPERATION/` | 项目管理文档 → 01；规则文档 → 00；内容资产 → 04；运营分析 → 09 |
| **数据** | `02_DATA/` | 所有数据类文件（raw/processed/datasets/exports/） |
| **代码** | `08_SYSTEM/`、`10_AI_AUTOMATION_ENGINE/`、`12_AI_RUNTIME/` | 系统代码 → 08；工作流代码 → 10；推理代码 → 12 |
| **配置** | `08_SYSTEM/config/`、`09_AI_OPERATION/platforms/` | 系统配置 → 08；平台采集配置 → 09 |
| **模型** | `12_AI_RUNTIME/models/` | 所有 AI 模型权重文件 |

### 边界判断口诀

> - 是"信息"还是"逻辑"？信息 → 02_DATA；逻辑 → 08_SYSTEM
> - 是"定义"还是"执行"？定义 → 03_AI_AGENT；执行 → 10_AI_AUTOMATION_ENGINE
> - 是"策略"还是"结果"？策略 → 09_AI_OPERATION；结果 → 02_DATA
> - 是"内容"还是"客户"？内容 → 04_CONTENT；客户 → 05_CUSTOMER_CRM
> - 是"AI 发现"还是"销售跟进"？发现 → 05_CUSTOMER_LEADS；跟进 → 05_CUSTOMER_CRM

---

## 五、AI 读取文件规则

PV_OS 的 AI Agent 在读取项目文件时，遵循以下优先级：

### 5.1 入口文件（必读）

任何 AI Agent 进入 PV_OS 项目时，应首先读取以下文件：

1. `00_SYSTEM/PV_OS_DIRECTORY_MAP.md` — 理解项目结构与文件存放规则
2. `00_SYSTEM/PV_OS_AI_RULES.md` — 理解 AI 行为约束
3. `00_SYSTEM/PV_OS_PROJECT_STATUS.md` — 了解当前项目状态

### 5.2 按任务类型定向读取

| 任务类型 | 优先读取目录 |
|----------|-------------|
| 数据采集相关 | `02_DATA/`、`09_AI_OPERATION/` |
| 客户识别/评分 | `03_AI_AGENT/`、`05_CUSTOMER_LEADS/`、`05_CUSTOMER_CRM/` |
| 内容生产/拆解 | `04_CONTENT/`、`09_AI_OPERATION/` |
| Agent 开发/编排 | `03_AI_AGENT/`、`10_AI_AUTOMATION_ENGINE/` |
| 系统开发/运维 | `08_SYSTEM/`、`12_AI_RUNTIME/` |
| 商业/产品决策 | `11_AI_PRODUCTIZATION/`、`01_PROJECT_MANAGEMENT/` |

### 5.3 读取深度原则

- **层级递进**：先读该目录下的 README 或索引文件，再深入子目录
- **避免全量扫描**：不要遍历所有目录，根据任务目标定向读取
- **信任目录约定**：需要数据就去 02_DATA，需要代码就去 08_SYSTEM，无需猜测

---

## 六、新增文件存放决策流程

当需要在 PV_OS 中新增文件时，按以下决策树判断存放位置：

```
新增文件
├─ 是数据（JSON/CSV/Excel/数据集）？
│  └─ → 02_DATA/ （根据 raw/processed/datasets 细分）
│
├─ 是系统级规则/架构文档？
│  └─ → 00_SYSTEM/
│
├─ 是项目管理文档（计划/会议/SOP）？
│  └─ → 01_PROJECT_MANAGEMENT/
│
├─ 是 AI Agent 定义/Prompt/策略？
│  └─ → 03_AI_AGENT/
│
├─ 是内容资产（脚本/素材/拆解）？
│  └─ → 04_CONTENT/
│
├─ 是 AI 客户线索/评分结果/培育池？
│  └─ → 05_CUSTOMER_LEADS/
│
├─ 是销售客户/跟进记录/商机？
│  └─ → 05_CUSTOMER_CRM/
│
├─ 是项目案例/方案设计？
│  └─ → 06_CASE_LIBRARY/
│
├─ 是财务/报价/合同？
│  └─ → 07_FINANCE/
│
├─ 是可执行代码/系统配置/DB Schema？
│  └─ → 08_SYSTEM/
│
├─ 是运营策略/竞品分析/采集配置？
│  └─ → 09_AI_OPERATION/
│
├─ 是工作流/编排/触发规则/调度？
│  └─ → 10_AI_AUTOMATION_ENGINE/
│
├─ 是产品定义/定价/营销材料？
│  └─ → 11_AI_PRODUCTIZATION/
│
├─ 是模型权重/推理代码/运行时日志？
│  └─ → 12_AI_RUNTIME/
│
└─ 是废弃/历史版本？
   └─ → 99_BACKUP/
```

---

## 七、业务能力映射总表

| 序号 | 核心业务 | 主要目录 | 辅助目录 |
|------|---------|---------|---------|
| 1 | 城市家庭光伏客户开发 | `05_CUSTOMER_CRM/` | `05_CUSTOMER_LEADS/`、`06_CASE_LIBRARY/` |
| 2 | 别墅/叠拼/洋房/露台/阳光房需求 | `05_CUSTOMER_CRM/` | `05_CUSTOMER_LEADS/`、`06_CASE_LIBRARY/`、`11_AI_PRODUCTIZATION/` |
| 3 | 小商业场景（民宿/酒店/棋牌室等） | `05_CUSTOMER_CRM/` | `05_CUSTOMER_LEADS/`、`06_CASE_LIBRARY/`、`11_AI_PRODUCTIZATION/` |
| 4 | 竞品账号自动发现 | `09_AI_OPERATION/` | `10_AI_AUTOMATION_ENGINE/` |
| 5 | 抖音/小红书/快手/视频号数据采集 | `02_DATA/` | `09_AI_OPERATION/` |
| 6 | 评论区潜在客户识别 | `03_AI_AGENT/` | `05_CUSTOMER_LEADS/`、`09_AI_OPERATION/`、`10_AI_AUTOMATION_ENGINE/` |
| 7 | AI 客户评分 | `03_AI_AGENT/` | `05_CUSTOMER_LEADS/`、`05_CUSTOMER_CRM/` |
| 8 | CRM 客户跟踪 | `05_CUSTOMER_CRM/` | `10_AI_AUTOMATION_ENGINE/` |
| 9 | 爆款视频拆解 | `04_CONTENT/` | `09_AI_OPERATION/` |
| 10 | AI 内容生产 | `04_CONTENT/` | `03_AI_AGENT/`、`10_AI_AUTOMATION_ENGINE/` |
| 11 | 自动化 Agent 运行 | `10_AI_AUTOMATION_ENGINE/` | `12_AI_RUNTIME/`、`03_AI_AGENT/` |

-A--

## 八、版本记录

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| V1.0 | 2026-07-11 | 初始版本，定义全部 14 个一级目录、五类资产存放矩阵、AI 读取规则、新增文件决策流程 |
| V1.1 | 2026-07-14 | 新增 05_CUSTOMER_LEADS（AI 客户发现层），区分 AI 发现与销售管理两层架构，更新目录树（14→15 个一级目录）、决策流程、业务能力映射表、读取规则 |
