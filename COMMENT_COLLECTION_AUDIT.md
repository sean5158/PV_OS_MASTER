# COMMENT_COLLECTION_AUDIT

版本：V1.0
日期：2026-07-13
用途：审计 PV_OS 评论数据采集能力现状，识别缺失模块，提出下一步建设建议

> 被审计文件：
> - `PV_OS_MASTER_CONTEXT.md` — 项目全局上下文
> - `PV_OS_FILE_REGISTRY.md` — 文件注册表
> - `10_AI_AUTOMATION_ENGINE/` — 自动化引擎（含 pipeline、triggers、tests）
> - `02_DATA/04_COMMENT_DATABASE/` — 评论数据库规则
> - `03_AI_AGENT/agents/comment_analyzer/` — 评论分析 Agent
> - `02_DATA/data_dict/comment_schema.md` — 数据标准结构
> - `08_SYSTEM/scripts/` — 系统脚本（collector_base.py 等）

---

## 一、当前评论采集能力评估

### 1.1 是否存在自动采集模块？

**不存在。** PV_OS 当前没有视频平台评论自动采集模块。

证据：

| 检查项 | 状态 |
|--------|:--:|
| `02_DATA/raw/` 目录 | ❌ 空目录（0 文件） |
| `08_SYSTEM/scripts/collector_base.py` | ❌ 空文件（占位脚本，无代码） |
| `08_SYSTEM/scripts/data_cleaner.py` | ❌ 空文件（占位脚本，无代码） |
| `08_SYSTEM/scripts/config_loader.py` | ❌ 空文件（占位脚本，无代码） |
| 测试数据 | ⚠️ 仅有 1 条手工编写的 `sample_comment.json`（成都别墅客户） |
| Pipeline 采集步骤 | ⚠️ pipeline 声明了 `collect_comment` 步骤，但无实际采集逻辑 |

### 1.2 自动化引擎现状

`10_AI_AUTOMATION_ENGINE/` 已定义的架构：

| 模块 | 路径 | 状态 |
|------|------|:--:|
| Orchestrator（流程编排） | `orchestrator/step_executor.py` | ✅ 有代码 |
| Scheduler（定时调度） | `scheduler/` | ❌ 目录为空 |
| Triggers（事件触发） | `triggers/event_bus.py` | ✅ 有代码 |
| Workflows（工作流） | `workflows/comment_to_lead_pipeline.yml` | ✅ 已定义 |
| Engine（引擎入口） | `engine.py` | ✅ 有代码 |
| Pipeline 执行 | `run_pipeline.py` | ✅ 有代码 |

**关键发现：** 自动化引擎的下游（Orchestrator、Triggers、Pipeline）已有框架，但上游的 Scheduler 目录为空，且 Pipeline 的第一步 `collect_comment` 指向 `02_DATA/raw/`——该目录为空。

### 1.3 结论

```
当前链路状态：

❌ 评论采集    →  ⚠️ 数据清洗   →  ✅ 分析规则   →  ✅ 评分模型   →  ✅ CRM 结构
   (缺失)        (空脚本)          (已固化)        (已固化)        (已固化)
```

PV_OS 的下游分析能力（评论分析规则、评分模型、CRM 入库）已完整固化，但**上游数据入口是空的**。

---

## 二、评论数据入口现状

### 2.1 设计中的数据入口

根据 `comment_to_lead_pipeline.yml`：

```yaml
steps:
  - name: collect_comment
    input:
      path:
        - 02_DATA/raw/
```

Pipeline 期望 `02_DATA/raw/` 已有数据。但该目录为空。

### 2.2 测试数据唯一入口

`10_AI_AUTOMATION_ENGINE/tests/fixtures/sample_comment.json`：

```json
{
  "id": "douyin_test_S_001",
  "platform": "douyin",
  "content": "我家在成都郊区别墅，想装一套光伏系统，能报个价吗？电话联系138xxxx",
  "author": "用户A",
  "create_time": "2026-07-12 10:00:00",
  "source_url": "https://douyin.com/video/test_s",
  "ip_location": "四川成都",
  "video_title": "别墅光伏安装实拍",
  "keyword": "别墅光伏"
}
```

这是**城市小区光伏客户**的典型测试案例，但仅此 1 条手工数据。

### 2.3 数据入口总结

| 数据入口 | 状态 | 说明 |
|---------|:--:|------|
| `02_DATA/raw/` | ❌ 空 | 设计中的数据入口，无实际数据 |
| `sample_comment.json` | ⚠️ | 仅 1 条手工样本，城市别墅客户 |
| 平台 API 连接 | ❌ | 无抖音/小红书/快手/视频号 API 集成 |
| 竞品评论采集 | ❌ | 无竞品视频评论抓取能力 |

---

## 三、comment_analyzer 需要的数据格式

### 3.1 输入声明

`comment_analyzer/agent.yml`：

```yaml
input:
  source:
    - 02_DATA/raw/
  schema:
    - 02_DATA/data_dict/comment_schema.md
```

### 3.2 标准数据格式（comment_schema.md）

comment_analyzer 期望的完整字段结构：

| 分类 | 字段 | 类型 | 必填 |
|------|------|------|:--:|
| 基础 | `id` | string（平台_编号） | ✅ |
| 基础 | `platform` | douyin / xiaohongshu / kuaishou / wechat_video | ✅ |
| 基础 | `content` | string（原始评论） | ✅ |
| 基础 | `author` | string（脱敏昵称） | ✅ |
| 基础 | `create_time` | datetime（YYYY-MM-DD HH:MM:SS） | ✅ |
| 基础 | `source_url` | string | ⚪ |
| 来源 | `video_title` | string | ⚪ |
| 来源 | `video_url` | string | ⚪ |
| 来源 | `keyword` | string（触发采集关键词） | ⚪ |
| 来源 | `collected_time` | datetime | ⚪ |
| AI 分析 | `sentiment` | positive/neutral/negative | ⚪ |
| AI 分析 | `customer_intent` | integer(0-3) | ⚪ |
| AI 分析 | `customer_type` | string | ⚪ |
| AI 分析 | `score` | integer(0-100) | ⚪ |
| 标签 | `tags` | array | ⚪ |
| 标签 | `location` | string | ✅（采集阶段尽量获取） |
| 标签 | `house_type` | string | ⚪ |

**采集阶段最低必填字段：** `id`、`platform`、`content`、`author`、`create_time`、`location`（至少 IP 属地）。

---

## 四、下游 Agent 的数据需求链路

### 4.1 完整链路

```
采集模块（缺失）
    ↓ 输出：原始评论（comment_schema 格式）
02_DATA/raw/
    ↓
comment_analyzer
    ↓ 输出：customer_type、intent_level、score、province/city/district、housing_type、tags
05_CUSTOMER_LEADS
    ↓
lead_scoring_agent
    ↓ 输出：lead_score、lead_grade、crm_target、follow_up_priority
05_CUSTOMER_CRM
```

### 4.2 各模块数据需求

| 模块 | 输入来源 | 最低必填字段 |
|------|---------|------------|
| comment_analyzer | `02_DATA/raw/` | id、platform、content、create_time、location |
| lead_scoring_agent | comment_analyzer 输出 + LEADS 中间层 | source_content、intent_level、province、city、housing_type、comment_time、source_platform |
| CRM | lead_scoring_agent 输出 | lead_score、lead_grade、crm_target、follow_up_priority |

### 4.3 采集模块需要为 comment_analyzer 提供的最低字段

围绕**城市小区光伏客户**，采集模块必须输出：

| 字段 | 说明 | 采集来源 |
|------|------|---------|
| `id` | 评论唯一标识 | 平台生成 |
| `platform` | 来源平台 | 采集时已知 |
| `content` | 原始评论文本 | 平台评论区 |
| `author` | 脱敏用户昵称 | 平台评论区 |
| `create_time` | 评论发布时间 | 平台评论区 |
| `source_url` | 原始视频/笔记链接 | 采集时已知 |
| `video_title` | 视频标题 | 平台 API |
| `keyword` | 触发采集的关键词 | 采集配置 |
| `location` | 用户 IP 属地（公开信息） | 平台评论区 |

---

## 五、缺失模块分析

### 5.1 完整缺失清单

| 缺失模块 | 路径（建议） | 功能 | 优先级 |
|---------|------------|------|:----:|
| 评论采集器 | `02_DATA/01_COLLECTION/` | 连接视频平台 API，批量采集竞品视频评论 | 🔴 P0 |
| 数据清洗器 | `08_SYSTEM/scripts/data_cleaner.py` | 去重、去噪、格式标准化 | 🟡 P1 |
| 采集调度器 | `10_AI_AUTOMATION_ENGINE/scheduler/` | 定时采集、频率控制、逆止策略 | 🟡 P1 |
| 平台连接器 | `02_DATA/01_COLLECTION/connectors/` | 各平台 API 适配（抖音/小红书/快手/视频号） | 🔴 P0 |

### 5.2 最紧急缺口：评论采集模块

```
当前：
  ❌ 无自动采集 → 02_DATA/raw/ 为空 → comment_analyzer 无数据可分析

所需：
  ✅ 评论采集器 → 02_DATA/raw/ → comment_analyzer → lead_scoring_agent → CRM
```

### 5.3 建议模块结构

```
02_DATA/01_COLLECTION/
├── README.md                    # 采集模块说明
├── COLLECTION_RULE.md           # 采集规则（频率、平台、关键词、竞品目标）
├── connectors/
│   ├── douyin_connector.py      # 抖音评论采集
│   ├── xiaohongshu_connector.py # 小红书评论采集
│   ├── kuaishou_connector.py    # 快手评论采集
│   └── wechat_video_connector.py # 视频号评论采集
├── collector.py                 # 统一采集入口
└── config.yml                   # 采集配置（竞品列表、关键词、频率）
```

---

## 六、城市小区光伏客户采集策略

### 6.1 采集目标

围绕**城市小区光伏客户**，采集应聚焦：

| 采集维度 | 策略 |
|---------|------|
| 视频类型 | 别墅光伏安装、阳光房光伏、叠拼光伏、大平层光伏 |
| 竞品账号 | 川渝黔光伏安装商（参考 `COMPETITOR_SCORE_RULE.md`） |
| 关键词 | 别墅光伏、家庭光伏、屋顶发电、光伏储能、阳光房 |
| 区域过滤 | IP 属地在四川/重庆/贵州的用户优先 |
| 房屋信号 | 评论文本包含别墅、叠拼、阳光房、大平层、露台等关键词 |

### 6.2 城市客户采集优先级

| 优先级 | 平台 | 场景 | 关键词示例 |
|:----:|------|------|---------|
| 1 | 抖音 | 别墅光伏安装实拍 | 别墅光伏、家庭光伏安装 |
| 2 | 小红书 | 阳光房/露台改造 | 阳光房光伏、露台改造、屋顶发电 |
| 3 | 快手 | 自建房/大平层 | 家庭光伏、农村光伏（仅商业经营场景） |
| 4 | 视频号 | 光伏知识科普 | 光伏储能、家庭能源 |

### 6.3 采集后的数据流

```
采集器输出原始评论
    ↓（platform=抖音/小红书/快手/视频号）
02_DATA/raw/（按平台分目录）
    ↓
数据清洗器（去重、格式标准化）
    ↓
02_DATA/04_COMMENT_DATABASE/（标准化评论）
    ↓
comment_analyzer（识别人群、意向、区域、房屋）
    ↓
05_CUSTOMER_LEADS（客户线索）
```

---

## 七、下一步建议

### 7.1 优先级排序

| 序号 | 任务 | 说明 | 优先级 |
|:--:|------|------|:----:|
| 1 | 建立 `02_DATA/01_COLLECTION/` 模块 | 创建采集规则和目录结构 | P0 |
| 2 | 实现抖音评论采集器 | 最高优先级平台，城市小区客户最集中 | P0 |
| 3 | 填充 `data_cleaner.py` | 实现去重、去噪、格式化为 comment_schema | P1 |
| 4 | 实现小红书评论采集器 | 城市女性用户多，阳光房场景丰富 | P1 |
| 5 | 建立采集调度器 | 定时采集 + 频率控制 | P1 |
| 6 | 实现快手/视频号采集器 | 补充覆盖 | P2 |

### 7.2 不建议：在采集模块建成前测试 Agent

当前 `sample_comment.json` 仅 1 条测试数据（城市别墅客户）。Agent 端到端测试需要至少覆盖以下城市客户场景：

| 测试案例 | 场景 | 评分预期 |
|---------|------|:--:|
| 成都别墅 + 主动问价 | 城市高价值客户 | S（≥80） |
| 重庆叠拼 + 咨询效果 | 城市中高价值客户 | A（60-79） |
| 成都普通住宅 + 了解光伏 | 城市普通客户 | B（35-59） |
| 成都普通住宅 + 无关评论 | 低价值 | C（<35） |
| 贵阳大平层 + 询价 | 城市中高价值客户 | A（60-79） |

> 注意：测试案例仅使用城市客户场景，农村案例标记为边界测试。

---

## 八、总结

1. **PV_OS 当前不具备视频平台评论自动采集能力。**
2. **数据入口 `02_DATA/raw/` 为空**，下游分析链路无法启动。
3. **comment_analyzer** 需要 `comment_schema.md` 格式的标准化数据，采集阶段最低必填 6 个字段。
4. **08_SYSTEM/scripts/ 三个脚本均为空文件**（collector_base.py、data_cleaner.py、config_loader.py）。
5. **最紧急的下一步：建立 `02_DATA/01_COLLECTION/` 评论采集模块**，优先实现抖音平台采集器。
6. **城市小区光伏客户是采集焦点**：优先采集别墅、叠拼、阳光房、大平层场景的竞品评论区。

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-13 | 首次评论采集能力审计：识别采集模块完全缺失，建议建立 02_DATA/01_COLLECTION/ |
