# PV_OS_CONTEXT_PROTOCOL

版本：V1.0
日期：2026-07-13
用途：定义 PV_OS 项目中所有 AI（Codex CLI / Codex Desktop / ChatGPT）进入项目后的上下文恢复协议、文件读取顺序和职责边界。

> 本协议整合以下源文件，不自行创造规则：
> - `PV_OS_BOOTSTRAP.md`
> - `PV_OS_MASTER_CONTEXT.md`
> - `PV_OS_FILE_REGISTRY.md`
> - `00_SYSTEM/PV_OS_AI_RULES.md`
> - `00_SYSTEM/PV_OS_CODEX_RULES.md`

---

## 一、协议定位

本协议是 PV_OS 所有 AI 协作的**唯一入口协议**。任何 AI 进入 PV_OS 项目后，必须首先执行本协议定义的启动流程，不得跳过步骤或依赖聊天历史/记忆代替文件读取。

### 1.1 核心原则

1. **固化文件优先**：所有业务决策以 `02_DATA/`、`00_SYSTEM/` 下固化文件为准
2. **状态文件驱动**：当前开发位置以 `backup/PV_OS_STATUS.md` 和 `backup/PV_OS_CODEX_STATUS.md` 为准
3. **禁止依赖聊天上下文**：每次新会话必须重新读取文件，不得凭记忆执行
4. **禁止自创业务规则**：AI 不得在未读取对应规则文件的情况下做出业务判断

---

## 二、AI 启动流程

### 2.1 完整启动流程（首次进入 / 恢复上下文）

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 0：身份确认                                                │
│   └─ 读取 PV_OS_BOOTSTRAP.md                                     │
│      - 确认角色：PV_OS Engineering Agent                         │
│      - 确认项目：光伏行业 AI 客户发现与销售自动化系统               │
│      - 确认开发原则：基于已有规则继续开发，不重新设计              │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 1：全局认知建立                                            │
│   ├─ 读取 PV_OS_MASTER_CONTEXT.md                                │
│   │   - 项目定位、商业目标、客户模型、评分逻辑、CRM 流转          │
│   └─ 读取 backup/PV_OS_BACKUP_MAP_V1.0.md                        │
│       - 系统架构、已完成模块、AI Agent 状态                       │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 2：业务流确认                                              │
│   ├─ 读取 backup/PV_OS_BUSINESS_TREE.md                          │
│   │   - 核心流程：评论 → AI 分析 → 评分 → CRM → 销售跟进         │
│   └─ 读取 backup/PV_OS_RULE_INDEX.md                             │
│       - 所有规则文件路径速查                                      │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 3：状态恢复                                                │
│   ├─ 读取 backup/PV_OS_STATUS.md                                 │
│   │   - 已完成模块、当前开发位置、下一步计划                      │
│   └─ 读取 backup/PV_OS_CODEX_STATUS.md                           │
│       - Codex 当前任务、修改记录、阻塞问题                        │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 4：约束加载                                                │
│   ├─ 读取 00_SYSTEM/PV_OS_CODEX_RULES.md                         │
│   │   - 允许修改目录、受保护目录、任务执行流程                    │
│   ├─ 读取 00_SYSTEM/PV_OS_AI_RULES.md                            │
│   │   - 四平台分工、执行流程、业务约束、偏差纠正                  │
│   └─ 读取 00_SYSTEM/PV_OS_GOVERNANCE_RULES.md                    │
│       - 项目最高目标、P0-P4 优先级、模块审批规则                  │
├─────────────────────────────────────────────────────────────────┤
│ PHASE 5：任务定向                                                │
│   └─ 根据用户任务类型，深入对应规则文件（见第四章）               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Codex 最小启动集（快速恢复）

当 Codex 需要快速恢复上下文而非完整启动时，至少读取以下 **8 个文件**：

| 顺序 | 文件 | 耗时（约） | 获取内容 |
|:----:|------|:--------:|---------|
| 1 | `PV_OS_BOOTSTRAP.md` | 快 | 身份、角色 |
| 2 | `PV_OS_MASTER_CONTEXT.md` | 中 | 全局认知 |
| 3 | `backup/PV_OS_BACKUP_MAP_V1.0.md` | 中 | 系统架构 |
| 4 | `backup/PV_OS_BUSINESS_TREE.md` | 快 | 业务流 |
| 5 | `backup/PV_OS_RULE_INDEX.md` | 快 | 规则索引 |
| 6 | `backup/PV_OS_STATUS.md` | 快 | 项目进度 |
| 7 | `backup/PV_OS_CODEX_STATUS.md` | 快 | 当前任务 |
| 8 | `00_SYSTEM/PV_OS_CODEX_RULES.md` | 快 | 开发约束 |

### 2.3 会话续接（同一天 / 同任务）

若 Codex 在同一会话内已经完成 Phase 0-4，无需重复读取全部文件。仅需：

1. 重新读取 `backup/PV_OS_CODEX_STATUS.md`（确认最新状态）
2. 按任务类型读取对应规则文件（见第四章）

---

## 三、启动文件读取顺序（分层定义）

### 3.1 读取金字塔

```
                    ┌──────────────────┐
                    │  Layer 5: 具体规则  │  ← 根据任务按需深入
                    │  评分/评论/CRM/区域  │
                    ├──────────────────┤
                    │  Layer 4: 约束规则  │  ← Phase 4
                    │  CODEX/AI/GOVERNANCE│
                    ├──────────────────┤
                    │  Layer 3: 状态文件  │  ← Phase 3
                    │  STATUS/CODEX_STATUS│
                    ├──────────────────┤
                    │  Layer 2: 导航文件  │  ← Phase 1-2
                    │  CONTEXT/MAP/INDEX  │
                    ├──────────────────┤
                    │  Layer 1: 入口文件  │  ← Phase 0
                    │  BOOTSTRAP          │
                    └──────────────────┘
```

### 3.2 各层必须读取（不可跳过）

| 层 | 文件 | 读取时机 | 如果跳过 |
|:--:|------|:------:|---------|
| L1 | `PV_OS_BOOTSTRAP.md` | 每次新会话 | 角色不明，开发原则不清 |
| L2 | `PV_OS_MASTER_CONTEXT.md` | 每次新会话 | 项目定位、商业目标不明 |
| L2 | `backup/PV_OS_BACKUP_MAP_V1.0.md` | 每次新会话 | 系统架构、模块位置不明 |
| L2 | `backup/PV_OS_BUSINESS_TREE.md` | 每次新会话 | 核心业务流程不明 |
| L2 | `backup/PV_OS_RULE_INDEX.md` | 每次新会话 | 规则文件路径不明 |
| L3 | `backup/PV_OS_STATUS.md` | 每次新会话 | 开发进度不明 |
| L3 | `backup/PV_OS_CODEX_STATUS.md` | 每次新会话 | 当前任务和记忆不明 |
| L4 | `00_SYSTEM/PV_OS_CODEX_RULES.md` | 每次新会话 | 可/不可修改目录不明 |
| L4 | `00_SYSTEM/PV_OS_AI_RULES.md` | 首次进入 | 四平台分工不明 |
| L4 | `00_SYSTEM/PV_OS_GOVERNANCE_RULES.md` | 首次进入 | 优先级和治理规范不明 |
| L5 | 按任务定向（见第四章） | 每次任务 | 具体业务规则缺失 |

### 3.3 ChatGPT 启动集

ChatGPT 不执行本地文件操作，读取顺序简化为：

1. `PV_OS_MASTER_CONTEXT.md` — 全局认知
2. `backup/PV_OS_BUSINESS_TREE.md` — 业务流
3. `00_SYSTEM/PV_OS_AI_RULES.md` — ChatGPT 职责定位
4. 按任务类型深入规则文件

---

## 四、任务类型与对应规则文件

### 4.1 任务-文件映射矩阵

> 以下映射规则：不同类型任务只需读取对应的 L5 层文件。
> L1-L4 层文件（第三章）在任何任务下都必须先读取。

| 任务类型 | 必读文件（L5 层） | 路径 |
|---------|------------------|------|
| **客户发现** | `COMMENT_ANALYZER_RULE.md` | `02_DATA/04_COMMENT_DATABASE/` |
| | `REGION_MATCH_RULE.md` | `02_DATA/03_REGION_LIBRARY/` |
| | `KEYWORD_STRATEGY.md` | `02_DATA/01_KEYWORD_LIBRARY/` |
| | `customer_filter.yml` | `13_BUSINESS_VALIDATION/outbound_customer_finding/filters/` |
| | `agent.yml`（customer_finder_agent） | `03_AI_AGENT/agents/customer_finder_agent/` |
| **评论分析** | `COMMENT_ANALYZER_RULE.md` | `02_DATA/04_COMMENT_DATABASE/` |
| | `COMMENT_TIME_AND_MATCH_RULE.md` | `02_DATA/04_COMMENT_DATABASE/` |
| | `COMMENT_DATA_LIFECYCLE_RULE.md` | `02_DATA/04_COMMENT_DATABASE/` |
| | `comment_schema.md` | `02_DATA/data_dict/` |
| | `agent.yml`（comment_analyzer） | `03_AI_AGENT/agents/comment_analyzer/` |
| **客户评分** | `CUSTOMER_SCORE_MODEL.md` | `02_DATA/06_SCORE_MODEL/` |
| | `lead_schema.md` | `05_CUSTOMER_CRM/leads/` |
| | `FIELD_MAPPING_RULE.md` | `05_CUSTOMER_LEADS/` |
| | `agent.yml`（lead_scoring_agent） | `03_AI_AGENT/agents/lead_scoring_agent/` |
| | `customer_scoring.yml` | `13_BUSINESS_VALIDATION/outbound_customer_finding/scoring/` |
| **CRM 任务** | `lead_schema.md` | `05_CUSTOMER_CRM/leads/` |
| | `FIELD_MAPPING_RULE.md` | `05_CUSTOMER_LEADS/` |
| | `COMMENT_DATA_LIFECYCLE_RULE.md` | `02_DATA/04_COMMENT_DATABASE/` |
| | `CUSTOMER_SCORE_MODEL.md` | `02_DATA/06_SCORE_MODEL/` |
| **Agent 开发** | `agent.yml`（目标 Agent） | `03_AI_AGENT/agents/{agent_name}/` |
| | `CUSTOMER_SCORE_MODEL.md` | `02_DATA/06_SCORE_MODEL/` |
| | `COMMENT_ANALYZER_RULE.md` | `02_DATA/04_COMMENT_DATABASE/` |
| | `comment_to_lead_pipeline.yml` | `10_AI_AUTOMATION_ENGINE/workflows/` |
| | `PV_OS_GOVERNANCE_RULES.md` | `00_SYSTEM/` |
| **竞品发现** | `KEYWORD_STRATEGY.md` | `02_DATA/01_KEYWORD_LIBRARY/` |
| | `COMPETITOR_DISCOVERY_ALGORITHM.md` | `02_DATA/02_COMPETITOR_DATABASE/` |
| | `COMPETITOR_SCORE_RULE.md` | `02_DATA/02_COMPETITOR_DATABASE/` |
| | `REGION_MASTER.md` | `02_DATA/03_REGION_LIBRARY/` |
| **文档维护** | `PV_OS_FILE_REGISTRY.md` | 项目根 |
| | `PV_OS_DIRECTORY_MAP.md` | `00_SYSTEM/` |
| | `PV_OS_AI_RULES.md`（偏差纠正章节） | `00_SYSTEM/` |

### 4.2 读取顺序规则

任务执行时，L5 层文件按以下顺序读取：

1. **Agent 配置**（`agent.yml`）— 首先确认该 Agent 的输入/输出/分析规则
2. **核心业务规则**（`COMMENT_ANALYZER_RULE.md` / `CUSTOMER_SCORE_MODEL.md`）— 加载评分和判断逻辑
3. **辅助规则**（区域、时间、生命周期、字段映射）— 补充上下文
4. **自动化管道**（`comment_to_lead_pipeline.yml`）— 确认上下游连接

### 4.3 交叉任务

如果任务同时涉及两个类型（如"分析评论后评分"），合并两个类型的所有文件，去重后按顺序读取。

---

## 五、ChatGPT 与 Codex 的职责边界

以下定义来自 `00_SYSTEM/PV_OS_AI_RULES.md` 第一章。

### 5.1 职责矩阵

| 维度 | ChatGPT Plus | Codex Desktop | Codex CLI |
|------|:-----------:|:------------:|:---------:|
| **定位** | 策略大脑 · 创意中心 | 项目总管 · 文件系统 | 自动化管道 · 批量执行器 |
| **PV_OS 中适用** | 市场策略、脚本创作、竞品分析、商业方案 | 文件管理、目录调整、文档维护 | Shell 执行、自动化开发、测试 |
| **操作范围** | 不碰文件系统 | `03_AI_AGENT/`、`10_AI_AUTOMATION_ENGINE/`、`99_BACKUP_ENGINE/` | `03_AI_AGENT/`、`10_AI_AUTOMATION_ENGINE/`、`99_BACKUP_ENGINE/` |
| **禁止** | 本地文件管理、Shell 执行、代码部署 | 联网搜索、外部数据采集、Web 浏览 | GUI 操作、纯策略讨论 |
| **修改权限** | 不直接修改文件 | 允许修改 Agent/自动化/备份目录 | 同 Codex Desktop |

### 5.2 协作链路

```
ChatGPT → 定方向、出策略、写爆款
    ↓ （策略输出）
Codex Desktop / CLI → 管文件、改代码、调结构、跑脚本
    ↓ （执行输出）
DeepSeek → 批量中文内容生成、评论情感分类（降成本）
```

### 5.3 禁止越界清单

| 场景 | 错误做法 | 正确做法 |
|------|---------|---------|
| ChatGPT 想调整目录结构 | 让 ChatGPT 直接操作 | 输出方案 → Codex 执行 |
| Codex CLI 需要内容策略 | 让 Codex CLI 做策略判断 | 调用 ChatGPT → 拿策略结果执行 |
| 批处理 2000 条评论 | 全部用 ChatGPT | ChatGPT 做少数样本策略 → DeepSeek 批量执行 |
| 跨平台任务（策略+执行） | 在单一平台勉强完成 | 拆分：策略→ChatGPT，执行→Codex |

### 5.4 受保护目录（Codex 视角）

以下目录 Codex 默认不可修改（来自 `PV_OS_CODEX_RULES.md`）：

| 目录 | 说明 | 例外 |
|------|------|------|
| `00_SYSTEM/` | 系统规则 | 可修改 `PV_OS_CODEX_RULES.md` |
| `02_DATA/` | 数据规则（评论规则、区域规则、评分模型） | 无 |
| `05_CUSTOMER_CRM/` | CRM 核心字段结构 | 无 |

如需修改受保护文件，必须：
1. 说明修改原因
2. 说明影响范围
3. 等待人工确认

---

## 六、规则优先级

### 6.1 优先级定义

当不同来源的信息发生冲突时，按以下优先级裁决：

```
优先级 1（最高）：业务规则文件
  ├── 02_DATA/04_COMMENT_DATABASE/COMMENT_ANALYZER_RULE.md
  ├── 02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md
  ├── 02_DATA/03_REGION_LIBRARY/REGION_MATCH_RULE.md
  ├── 02_DATA/01_KEYWORD_LIBRARY/KEYWORD_STRATEGY.md
  ├── 02_DATA/02_COMPETITOR_DATABASE/COMPETITOR_SCORE_RULE.md
  └── 05_CUSTOMER_CRM/leads/lead_schema.md

优先级 2：系统规则文件
  ├── 00_SYSTEM/PV_OS_GOVERNANCE_RULES.md
  ├── 00_SYSTEM/PV_OS_CODEX_RULES.md
  └── 00_SYSTEM/PV_OS_AI_RULES.md

优先级 3：状态文件
  ├── backup/PV_OS_STATUS.md
  ├── backup/PV_OS_CODEX_STATUS.md
  └── backup/PV_OS_BACKUP_MAP_V1.0.md

优先级 4（最低）：聊天历史 / AI 记忆
  └── 仅作参考，不得替代固化文件
```

### 6.2 冲突裁决规则

| 冲突场景 | 裁决 |
|---------|------|
| 业务规则文件 vs 系统规则文件 | **业务规则文件优先** |
| 系统规则文件 vs 状态文件 | **系统规则文件优先** |
| 状态文件 vs 聊天历史 | **状态文件优先** |
| 聊天历史 vs 业务规则文件 | **业务规则文件优先** — 即使聊天中说过，也必须以固化文件为准 |
| 两个业务规则文件冲突 | 检查版本日期，以**最新版本**为准；同版本则标记冲突，等待人工裁决 |

### 6.3 规则文件权威性

以下规则文件为 PV_OS 不可动摇的核心：

| 文件 | 权威范围 | 修改条件 |
|------|---------|---------|
| `COMMENT_ANALYZER_RULE.md` | 评论如何分析、客户如何识别 | 需人工确认 |
| `CUSTOMER_SCORE_MODEL.md` | 客户如何评分、S/A/B/C 等级划分 | 需人工确认 |
| `REGION_MATCH_RULE.md` | 区域如何识别、分值如何分配 | 需人工确认 |
| `PV_OS_GOVERNANCE_RULES.md` | 项目优先级、模块审批规则 | 需人工确认 |
| `lead_schema.md` | CRM 字段标准结构 | 需人工确认 |

---

## 七、禁止依赖聊天上下文替代固化文件

### 7.1 核心禁令

> **AI 不得以"我记得之前聊过""上次会话中说过"等聊天记忆为依据执行操作。所有决策必须以当前读取的固化文件为准。**

### 7.2 必须重新读取的场景

| 场景 | 必须执行的动作 |
|------|--------------|
| 新会话开始 | 完整执行 Phase 0-4 启动流程（第二章） |
| 切换任务类型 | 重新读取目标任务的 L5 层文件（第四章） |
| 修改任何文件前 | 重新读取该文件的最新内容 |
| 涉及业务判断 | 重新读取对应的业务规则文件 |
| 状态文件超 1 天未更新 | 人工确认当前实际状态 |
| 不确定规则来源 | 通过 `PV_OS_RULE_INDEX.md` 定位 → 读取源文件 |

### 7.3 违规示例

| 违规行为 | 为什么错误 | 正确做法 |
|---------|-----------|---------|
| "我记得评分模型是 40+20+20+10+10" | 聊天记忆可能过时 | 重新读取 `CUSTOMER_SCORE_MODEL.md` |
| "上次会话中用户说要改这个规则" | 用户指令未固化为文件 | 确认该修改是否已写入规则文件 |
| "我感觉这个客户应该算 S 级" | 凭感觉而非规则判断 | 对照 `CUSTOMER_SCORE_MODEL.md` 逐项评分 |
| "上周聊天中讨论过这个 Agent 要改" | 口头讨论不等于规则 | 检查 `agent.yml` 实际内容 |

### 7.4 唯一例外

只有在以下情况下可以跳过文件读取：

- 同一会话内，**刚刚**（本回合内）读取过该文件且未做任何修改
- `PV_OS_BOOTSTRAP.md`、`PV_OS_CODEX_RULES.md` 在同一会话内已读取且任务不变

---

## 八、偏差纠正机制

以下规则整合自 `00_SYSTEM/PV_OS_AI_RULES.md` 第九章。

### 8.1 自检清单

每次 AI 完成操作后，必须执行：

1. ✏️ 是否跳过了 L1-L4 层文件的启动读取？
2. ✏️ 业务判断是否基于固化文件（而非聊天记忆）？
3. ✏️ 是否误操作了受保护目录（`00_SYSTEM/`、`02_DATA/`、`05_CUSTOMER_CRM/`）？
4. ✏️ 是否自创了业务规则？
5. ✏️ 是否在未读取规则文件的情况下做了业务判断？

### 8.2 纠正流程

```
检测到偏差
    ↓
立即停止当前操作
    ↓
分析原因：规则不清 / 跳过读取 / 依赖聊天记忆 / 疏忽
    ↓
执行纠正：重读文件 / 回滚修改 / 修正判断
    ↓
记录到 backup/PV_OS_CODEX_STATUS.md
```

---

## 九、启动后第一个动作速查

### 9.1 Codex CLI（当前环境）

```
1. 确认已在 ~/PV_OS_MASTER 目录
2. 读取 PV_OS_BOOTSTRAP.md
3. 读取 PV_OS_MASTER_CONTEXT.md
4. 读取 backup/PV_OS_BACKUP_MAP_V1.0.md
5. 读取 backup/PV_OS_BUSINESS_TREE.md
6. 读取 backup/PV_OS_RULE_INDEX.md
7. 读取 backup/PV_OS_STATUS.md
8. 读取 backup/PV_OS_CODEX_STATUS.md
9. 读取 00_SYSTEM/PV_OS_CODEX_RULES.md
10. 如新会话：读取 00_SYSTEM/PV_OS_AI_RULES.md + 00_SYSTEM/PV_OS_GOVERNANCE_RULES.md
11. 按用户任务类型，进入第四章 L5 层文件
```

### 9.2 ChatGPT（Web 端）

```
1. 读取 PV_OS_MASTER_CONTEXT.md
2. 读取 backup/PV_OS_BUSINESS_TREE.md
3. 读取 00_SYSTEM/PV_OS_AI_RULES.md
4. 按任务类型读取对应业务规则文件
5. 策略/创意类输出转交 Codex 执行
```

---

## 十、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-13 | 整合 5 个源文件，建立统一的 AI 上下文恢复协议：五阶段启动流程、8 文件最小启动集、7 类任务-文件映射矩阵、规则优先级体系、禁令条款 |

