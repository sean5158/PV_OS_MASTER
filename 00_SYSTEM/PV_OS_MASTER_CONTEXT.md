# PV_OS MASTER 项目上下文 V1.0

> 光伏行业 AI 自动化运营系统
>
> 用于新 AI / 新账号恢复项目上下文

更新时间：
2026-07-20


# 一、项目名称

PV_OS_MASTER


# 二、项目定位

PV_OS 是光伏行业 AI 自动化运营系统。

目标：

通过 AI Agent + 数据采集 + 内容生产 + CRM 自动化，
实现：

潜在客户发现 → 客户分析 → 客户评分 → 销售转化 → 案例沉淀。


核心方向：

1. 城市家庭光伏
2. 别墅/叠拼/花园洋房/阳光房光伏
3. 小商业光伏（民宿、酒店、茶楼、美容院等）


禁止方向：

- 大型工商业光伏
- 地面电站
- 光伏供应链


# 三、系统架构

项目目录：

00_SYSTEM
系统规则与项目入口

01_PROJECT_MANAGEMENT
项目管理

02_DATA
数据资产

03_AI_AGENT
AI Agent定义

04_CONTENT
内容生产

05_CUSTOMER_CRM
客户管理

06_CASE_LIBRARY
案例库

07_FINANCE
财务

08_SYSTEM
技术实现

09_AI_OPERATION
AI运营

10_AI_AUTOMATION_ENGINE
自动化引擎

11_AI_PRODUCTIZATION
产品化

12_AI_RUNTIME
AI运行环境

99_BACKUP
备份


# 四、已完成内容


## 00_SYSTEM 已完成

文件：

PV_OS_ARCHITECTURE.md

PV_OS_DIRECTORY_MAP.md

PV_OS_AI_RULES.md

PV_OS_PROJECT_STATUS.md


作用：

定义系统架构、AI规则、目录规则、项目状态。


## 02_DATA 已完成设计

已完成：

- 关键词库规则
- 竞品数据库规则
- 评论分析规则
- 客户评分模型


# 五、当前项目阶段


Phase 2：

P2 架构确立 + 采集链路建设


当前完成：

60%

269/269 测试通过


已完成：

✅ 系统架构 + AI协作规则 + 文件管理规范
✅ 数据规则设计（关键词/竞品/评论/评分）
✅ Comment Analyzer / Lead Scoring / Customer Finder Agent
✅ Pipeline 端到端验证 (S/A/B/C → CRM)
✅ P1 阶段冻结（Task Model / Intent Model / Competitor Account / Scheduler）
✅ P2-1 Platform Adapter (mock/public/official 三模式)
✅ P2-2 CSV Import + Pipeline 端到端
✅ P2-3 Douyin Collector 架构框架
✅ P2-4 Collector 生产增强 (cursor/分页/日志)
✅ 规则校准 → P2 架构重设计 V2.1


当前焦点：

P2-1: 竞品发现引擎 (Competitor Discovery Layer)
  - 关键词驱动 → 平台公开搜索 → 账号发现 → 视频发现 → 评论采集
  - competitor_master.csv (AI自动发现 + 人工确认)

核心路线：

关键词驱动 → 平台公开搜索 → 发现账号 → 发现视频 → 评论采集 → AI分析 → CRM


# 六、P2 数据采集路线


## 6.1 核心路线（规则固化）

```
关键词驱动 → 平台公开搜索 → 发现竞品账号 → 发现视频 → 采集公开评论 → AI分析 → CRM
```

参考文件：
- `02_DATA/01_KEYWORD_LIBRARY/KEYWORD_STRATEGY.md` — 关键词八源体系
- `02_DATA/02_COMPETITOR_DATABASE/COMPETITOR_DISCOVERY_ALGORITHM.md` — 六阶段竞品发现
- `PV_OS_COMMENT_COLLECTION_STRATEGY.md` V2.0 — 采集策略
- `COMMENT_COLLECTOR_AGENT_DESIGN.md` V2.0 — Collector 设计
- `00_SYSTEM/PV_OS_P2_ARCHITECTURE_DESIGN.md` V2.1 — P2 架构


## 6.2 数据来源

Public Data Collection（公开数据采集）

- 仅采集平台公开可见内容（搜索框/公开页面/评论区）
- 不依赖平台官方 API（official 模式为补充路径）
- 三模式: mock（测试）/ public（公开采集）/ official（API补充）


## 6.3 已完成 Agent

| Agent | 状态 |
|-------|:--:|
| comment_analyzer | ✅ V2.0，Pipeline 已验证 |
| lead_scoring_agent | ✅ V2.0，S/A/B/C 分级 |
| customer_finder_agent | ✅ V1.0 |
| comment_collector_agent | ✅ V2.0，架构就绪，待竞品发现引擎 |
| competitor_account_agent | ✅ V1.1，Pipeline 已接入 |


# 七、AI平台分工


ChatGPT：

负责：

战略规划
商业分析
Prompt设计
内容策略


Codex Desktop：

负责：

文件管理
代码开发
项目结构维护


Codex CLI：

负责：

Shell执行
数据处理
自动化脚本


DeepSeek：

负责：

中文批处理
大规模文本分类


# 八、AI进入项目规则


任何AI进入项目：

第一步读取：

00_SYSTEM/PV_OS_DIRECTORY_MAP.md

00_SYSTEM/PV_OS_AI_RULES.md

00_SYSTEM/PV_OS_PROJECT_STATUS.md


然后执行任务。


禁止：

- 随意创建目录
- 修改无关文件
- 数据和代码混放
- 编造客户案例数据


# 九、当前下一步任务


P2-1：竞品发现引擎 (Competitor Discovery Layer)

优先级：P0（客户获取最高优先级）


目标：

实现关键词→公开搜索→账号发现→视频发现→评论采集


关键文件：

- `competitor_discovery.py` (新)
- `competitor_master.csv` (AI发现资产库)
- `competitor_accounts.csv` (测试用途)


完成后更新：

- `00_SYSTEM/PV_OS_PROJECT_STATUS.md`
- `00_SYSTEM/PV_OS_P2_ARCHITECTURE_DESIGN.md`


# 十、新账号恢复指令


请读取：

00_SYSTEM/PV_OS_MASTER_CONTEXT.md

然后读取：

PV_OS_ARCHITECTURE.md

PV_OS_AI_RULES.md

PV_OS_PROJECT_STATUS.md


恢复 PV_OS_MASTER 项目上下文。

继续当前 Phase 1 开发任务。


END
