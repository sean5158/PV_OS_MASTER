# Phase 3-3 Content Intelligence 内容智能系统设计

**版本**: V2.0
**日期**: 2026-07-21
**状态**: 设计阶段 — 不执行代码
**项目**: PV_OS V3.2
**上游**: Phase 3-2.2 Public Parser Core（已完成，761 测试）

> **本文档定义 Content Intelligence 的完整业务模型、数据模型和系统架构。**
> 不包含任何代码实现。编码阶段将严格遵循本文档。

---

## 一、业务目标

### 1.1 核心命题

Content Intelligence 解决 PV_OS 内容端的根本问题：

**"竞品视频我看了，然后呢？我自己该拍什么？"**

### 1.2 一次采集，多次复用

PV_OS 的数据采集不是一次性消费。同一次平台公开搜索/采集的结果，形成四层长期资产，服务四种商业用途：

```
┌──────────────────────────────────────────────────────────────┐
│              一次平台公开搜索 / 采集                           │
│                                                              │
│  输入: keyword + platform + region                           │
│                                                              │
│  ┌──────────────┬──────────────┬──────────────┬────────────┐ │
│  │  Account     │  Video       │  Comment     │  Content   │ │
│  │  Asset       │  Asset       │  Asset       │  Asset     │ │
│  │  账号是谁     │  发了什么     │  谁在评论     │  为什么爆   │ │
│  └──────┬───────┴──────┬───────┴──────┬───────┴─────┬──────┘ │
│         │              │              │             │        │
│         ▼              ▼              ▼             ▼        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ 用途 ①   │  │ 用途 ②   │  │ 用途 ③   │  │ 用途 ④   │    │
│  │ 主动找    │  │ 分析竞品  │  │ 指导自己  │  │ 生成二创  │    │
│  │ 客户      │  │ 内容      │  │ 做视频    │  │ 脚本      │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                                                              │
│  四种用途对应 PV_OS 两个商业闭环：                             │
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │ A. 主动找客户        │  │ B. 客户主动找我              │   │
│  │ (Outbound)           │  │ (Inbound)                    │   │
│  │                     │  │                             │   │
│  │ 用途① → Lead评分    │  │ 用途② → 爆款拆解            │   │
│  │       → CRM          │  │ 用途③ → 内容策略            │   │
│  │                     │  │ 用途④ → 二创脚本            │   │
│  │                     │  │       → 自有账号发布          │   │
│  │                     │  │       → 新评论 → Inbound     │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 1.3 Content Intelligence 的边界

| 是 | 不是 |
|------|------|
| ✅ 分析竞品内容为什么爆 | ❌ 评论分析工具 |
| ✅ 指导 PV_OS 自有账号生产内容 | ❌ 竞品销售分析 |
| ✅ 生成二创脚本 | ❌ 自动发布系统 |
| ✅ 内容策略决策支持 | ❌ 视频剪辑工具 |

---

## 二、Video Asset 数据模型

### 2.1 定位

`VideoAsset` 是 PV_OS 视频资产长期存储模型。与 `CommentRecord`（评论瞬态数据）不同，VideoAsset 是**长期资产**——入库后持续为内容分析、脚本生成、客户发现提供数据支撑。

### 2.2 存储位置

```
02_DATA/
├── video_asset_store.csv          # 视频资产主表
└── video_asset_index.json         # 索引（按 author_id / platform / publish_time）
```

### 2.3 主表字段定义

| # | 字段 | 类型 | 必填 | 说明 |
|:--:|------|------|:--:|------|
| 1 | `video_id` | string | ✅ | 平台视频唯一 ID（格式：`平台前缀_平台video_id`） |
| 2 | `platform` | enum | ✅ | douyin / xiaohongshu / kuaishou / shipinhao |
| 3 | `author_id` | string | ✅ | 视频发布者平台 ID |
| 4 | `author_name` | string | ✅ | 视频发布者昵称 |
| 5 | `author_url` | string | ✅ | 视频发布者主页链接 |
| 6 | `account_category` | string | ⚪ | 发布者账号分类（通过 author_id 关联 competitor_master） |
| 7 | `title` | string | ✅ | 视频标题 |
| 8 | `video_url` | string | ✅ | 视频链接 |
| 9 | `description` | string | ⚪ | 视频描述/简介 |
| 10 | `publish_time` | datetime | ✅ | 发布时间（ISO 8601） |
| 11 | `duration_seconds` | int | ⚪ | 时长（秒） |
| 12 | `like_count` | int | ✅ | 点赞数 |
| 13 | `comment_count` | int | ✅ | 评论数 |
| 14 | `collect_count` | int | ✅ | 收藏数 |
| 15 | `share_count` | int | ⚪ | 转发数 |
| 16 | `housing_signal` | string | ⚪ | 房屋场景信号：别墅/叠拼/阳光房/大平层/花园洋房/普通住宅 |
| 17 | `relevance_score` | int | ⚪ | PV_OS 内容相关度 0-10 |
| 18 | `collected_at` | datetime | ✅ | 入库时间 |
| 19 | `analyzed_at` | datetime | ⚪ | 最近一次 AI 分析时间 |
| 20 | `source_keyword` | string | ⚪ | 采集发现关键词 |
| 21 | `source_platform` | string | ⚪ | 采集来源平台 |

### 2.4 数据来源

```
PublicCollector (真实公开页面解析)
    │
    ▼
VideoCandidate (douyin_public_collector.py 输出)
    │
    ▼
VideoAsset.from_candidate()  →  video_asset_store.csv
    │
    ▼
ContentIntelligenceAgent.analyze()  →  填充 AI 分析结果
```

### 2.5 与 competitor_master 的关联

VideoAsset 不直接包含 `account_purpose` 字段。通过 `author_id` 关联查询：

```python
# 伪代码
account = competitor_master.get(author_id=video.author_id)
if account.account_purpose == "content_learning":
    route = "content_intelligence"    # → 爆款分析
elif account.account_purpose == "customer_source":
    route = "lead_scoring"           # → 客户发现
elif account.account_purpose == "both":
    route = "both"                   # → 两条路线并行
```

---

## 三、视频分析模型

### 3.1 八维分析框架

对每条入库视频，Content Intelligence 从八个维度进行拆解分析：

```
视频输入 (VideoAsset)
│
├── 维度 1: 黄金 3 秒 (Hook)
│   问题: 前 3 秒说了什么让人停下？
│   产出: hook_3_seconds, hook_type (数字对比/悬念/反差/痛点直击/场景代入)
│
├── 维度 2: 用户痛点 (Pain Point)
│   问题: 击中用户什么焦虑/需求？
│   产出: pain_point, pain_level (强/中/弱)
│
├── 维度 3: 目标客户画像 (Customer Profile)
│   问题: 面向谁？
│   产出: customer_type (别墅业主/小商家/普通家庭/装修业主)
│
├── 维度 4: 爆点 (Viral Trigger)
│   问题: 哪个片段引发传播？
│   产出: viral_reason, viral_type (情绪/实用/反差/共鸣/争议)
│
├── 维度 5: 冲突 (Conflict)
│   问题: 视频中有什么矛盾/对立？
│   产出: conflict_pattern (省钱vs品质/传统vs新能源/怀疑vs验证)
│
├── 维度 6: 转折 (Turning Point)
│   问题: 情绪/信息在哪里转折？
│   产出: turning_point, turning_type (数据揭示/方案呈现/客户证言)
│
├── 维度 7: 评论触发 (Comment Trigger)
│   问题: 什么让用户忍不住评论？
│   产出: comment_trigger, trigger_type (提问诱导/争议制造/共鸣激发)
│
└── 维度 8: CTA (Call to Action)
    问题: 视频如何引导下一步行动？
    产出: cta_analysis, cta_type (直接号召/软性引导/评论区诱导/主页引导)
```

### 3.2 分析输出格式

```json
{
  "video_id": "dy_v01234",
  "analyzed_at": "2026-07-21T10:00:00+08:00",
  "analysis": {
    "hook_3_seconds": {
      "description": "数字对比：电费从3000降到300",
      "hook_type": "数字对比",
      "effectiveness": "high"
    },
    "pain_point": {
      "description": "城市别墅业主电费高但不知道光伏能省多少",
      "pain_level": "strong",
      "target_emotion": "焦虑+好奇"
    },
    "customer_profile": {
      "customer_type": "别墅业主",
      "secondary_type": "对新能源有认知的城市中产",
      "housing_signal": "别墅"
    },
    "viral_trigger": {
      "viral_reason": "强数字对比 + 真实案例 + 本地信任感",
      "viral_type": "实用",
      "share_motivation": "帮朋友省钱"
    },
    "conflict": {
      "conflict_pattern": "省钱 vs 品质 — 装了光伏既省钱又不影响别墅美观",
      "resolution": "案例实拍打消顾虑"
    },
    "turning_point": {
      "description": "第15秒展示电费账单对比",
      "turning_type": "数据揭示",
      "position_seconds": 15
    },
    "comment_trigger": {
      "description": "制造了代入感 — 评论里很多人问'我家能装吗'",
      "trigger_type": "共鸣激发",
      "expected_reaction": "询问自身情况"
    },
    "cta_analysis": {
      "cta_type": "评论区诱导",
      "effectiveness": "medium",
      "suggestion": "可增强为'评论区告诉我你家面积，我给你算'"
    }
  },
  "reusable_elements": {
    "hook_template": "[数字]从[旧状态]变成[新状态]，我只做了一件事",
    "structure_template": "痛点开场 → 方案展示 → 数据对比 → 客户见证 → 引导咨询",
    "title_formula": "数字对比型：我家XX平米装了光伏，一年省了X万",
    "key_phrases": ["装了光伏", "一年省了", "真实案例", "本地安装"]
  },
  "scene_classification": {
    "housing_scene": "别墅",
    "region_relevance": "全国通用",
    "customer_stage": "认知阶段"
  }
}
```

### 3.3 分析结果存储

每个视频的分析结果保存为独立 JSON 文件：

```
04_CONTENT/analytics/
└── video_analysis_{video_id}_{timestamp}.json
```

同时，关键维度字段回写到 `video_asset_store.csv` 的对应列中，支持批量查询和筛选。

---

## 四、竞品账号用途分类

### 4.1 核心理念

**同一个竞品账号，对 PV_OS 有两种截然不同的商业价值。**

不能混淆。

### 4.2 A 类：内容学习账号

| 维度 | 说明 |
|------|------|
| **定位** | 全国优秀光伏/新能源内容创作者 |
| **地域** | **四川以外**（优先省外同行） |
| **原因** | PV_OS 自身是四川 IP 博主，四川同行主要用于市场观察而非内容学习 |
| **用途** | 爆款拆解、内容策略研究、二创脚本参考 |
| **分析维度** | 黄金3秒 / 痛点 / 客群画像 / 爆点 / 冲突 / 转折 / 评论触发 / CTA |
| **输出** | VideoAnalysisResult → ContentInsight → ScriptLibrary |
| **判定条件** | account_purpose = "content_learning" 或 "both" |
| **地域限制** | 无地域限制 — 全国范围均可 |

### 4.3 B 类：客户发现账号

| 维度 | 说明 |
|------|------|
| **定位** | 四川/重庆/贵州本地竞品（安装商/案例号） |
| **地域** | **四川、重庆、贵州** |
| **原因** | 评论区是目标区域城市家庭光伏客户的最高密度来源 |
| **用途** | 评论采集 → 客户发现 → Lead 评分 → CRM |
| **分析维度** | 评论意图 / 区域判断 / 房屋场景 / 需求强度 |
| **输出** | CommentRecord → CommentAnalyzer → LeadScoring → CRM |
| **判定条件** | account_purpose = "customer_source" 或 "both" |
| **地域限制** | 仅四川/重庆/贵州 |

### 4.4 两类的协同关系

一条视频可能同时服务两个闭环：

```
同一视频 (VideoAsset)
│
├── author.account_purpose = "both"
│
├──→ Content Intelligence 路线
│     └── 八维分析 → 二创脚本 → 自有账号发布 → Inbound
│
└──→ Lead Discovery 路线
      └── 评论采集 → Comment Intent → Lead Scoring → CRM (Outbound)
```

### 4.5 不得混淆的规则

| 禁止 | 原因 |
|------|------|
| ❌ 用 A 类账号的评论做客户发现 | 四川以外的评论用户不在目标市场 |
| ❌ 用 B 类账号的视频做内容学习 | 四川同行内容不具备全国爆款参考价值 |
| ❌ 混用 account_purpose 导致重复分析 | 浪费计算资源，污染分析结果 |

---

## 五、Content Insight

### 5.1 定义

`ContentInsight` 是**跨视频的聚合分析结果**。

它从多条 VideoAnalysisResult 中提取共性模式，回答：

- 光伏内容领域什么话题在爆？
- 当前市场的内容空白是什么？
- 哪种标题公式最有效？
- 哪种钩子类型最高频？

### 5.2 数据流

```
VideoAsset (N 条)
    │
    ▼
VideoAnalysisResult (N 条)
    │ 批量聚合分析
    ▼
ContentInsight
    ├── top_topics        当前热门话题 TOP N
    ├── demand_gaps       用户需求但内容空白的方向
    ├── title_patterns    高频标题公式
    ├── hook_formulas     高频钩子模式
    └── recommended_topics 推荐选题方向
```

### 5.3 ContentInsight 结构

```json
{
  "generated_at": "2026-07-21T10:00:00+08:00",
  "source_count": 150,
  "source_period": "2026-07-14 ~ 2026-07-21",
  "top_topics": [
    {
      "topic": "别墅光伏安装实拍",
      "frequency": 42,
      "avg_engagement": 8500,
      "trend": "rising"
    }
  ],
  "demand_gaps": [
    {
      "gap": "叠拼/花园洋房场景内容严重不足",
      "opportunity": "差异化切入点 — 竞品多在拍别墅和普通住宅",
      "estimated_demand": "high"
    }
  ],
  "title_patterns": [
    {
      "pattern": "数字对比型",
      "formula": "[面积]平米装了光伏，[时间]省了[金额]",
      "frequency": 38,
      "effectiveness": "high"
    }
  ],
  "hook_formulas": [
    {
      "type": "数字对比",
      "template": "从[高数字]到[低数字]，我只做了[一件事]",
      "usage_count": 45,
      "avg_retention": "high"
    }
  ],
  "recommended_topics": [
    {
      "topic": "叠拼/花园洋房光伏安装全流程",
      "rationale": "竞品内容空白 + 目标市场有需求 + 差异化定位",
      "target_audience": "成都叠拼/花园洋房业主",
      "priority": "P0"
    }
  ]
}
```

### 5.4 生成频率

| 分析类型 | 频率 | 触发 |
|------|:--:|------|
| 单视频分析 | 每次入库 | 自动触发 |
| ContentInsight 聚合 | 每周 | 手动或 Cron 触发 |
| 紧急趋势 | 按需 | 市场热点出现时 |

### 5.5 存储

```
04_CONTENT/strategy/
├── content_insight_{date}.json      # ContentInsight 快照
└── content_insight_latest.json      # 最新版本（供 Agent 读取）
```

---

## 六、Script Library

### 6.1 定位

Script Library 是 Content Intelligence 的输出层。

它将分析结果转化为**可直接用于拍摄的二创脚本**。

### 6.2 数据流

```
竞品视频 → AI 八维分析 → VideoAnalysisResult
                              │
                              ▼
                       ContentInsight（聚合洞察）
                              │
                              ▼
                       ScriptLibrary（二创脚本）
                              │
                    ┌─────────┼─────────┐
                    ▼                   ▼
              人工拍摄               AI 数字人口播
              (真人出镜)            (AI 生成视频)
                    │                   │
                    └─────────┬─────────┘
                              ▼
                        自有账号发布
                              │
                              ▼
                    content_calendar.csv
                              │
                              ▼
                    content_performance.csv
```

### 6.3 脚本条目结构

```json
{
  "script_id": "script_20260721_001",
  "generated_at": "2026-07-21T10:00:00+08:00",
  "source_videos": ["dy_v001", "dy_v003"],
  "source_insight_id": "content_insight_20260721",
  "title": "我家叠拼装了光伏，物业都来看了三次",
  "scene_type": "叠拼/花园洋房",
  "target_audience": "成都叠拼/花园洋房业主",
  "hook": "装了光伏之后，物业经理带着整个团队来参观",
  "structure": [
    {"segment": "开场钩子", "duration": 3, "content": "装了光伏之后，物业经理带着整个团队来参观"},
    {"segment": "痛点共鸣", "duration": 5, "content": "说实话之前也担心，叠拼屋顶结构复杂，怕装了不好看"},
    {"segment": "方案展示", "duration": 8, "content": "后来找了专业设计，做了隐藏式安装，屋顶反而更高级了"},
    {"segment": "数据对比", "duration": 5, "content": "上个月电费账单出来，从1千3降到200，物业都惊了"},
    {"segment": "CTA", "duration": 3, "content": "你家是叠拼还是花园洋房？评论区告诉我"}
  ],
  "total_duration_seconds": 24,
  "production_mode": "human_shoot",
  "review_status": "pending",
  "stored_at": "04_CONTENT/scripts_ai/script_20260721_001.md"
}
```

### 6.4 两种生产模式

| 模式 | 说明 | 脚本格式 | 适用场景 |
|------|------|---------|---------|
| **人工拍摄** | 真人出镜拍摄 | 口播逐字稿 + 镜头切换提示 | 需要有真人 IP 信任感的场景 |
| **AI 数字人口播** | AI 生成数字人视频 | 口播文案 + 画面素材列表 | 批量内容生产、测试选题 |

### 6.5 存储与索引

```
04_CONTENT/scripts_ai/
├── script_index.csv            # 脚本索引（script_id / title / scene_type / review_status）
├── script_20260721_001.md      # 脚本内容
├── script_20260721_002.md
└── ...

04_CONTENT/scripts_ai/generated/
├── content_calendar.csv        # 发布计划
├── content_performance.csv     # 发布效果
└── content_to_lead_mapping.csv  # 内容→客户归因
```

### 6.6 人工审核流程

```
ScriptEntry (AI 生成, review_status=pending)
    │
    ▼
人工审核
    ├── 通过 → review_status=approved → 进入拍摄/制作
    ├── 修改 → review_status=revised → AI 重新生成
    └── 废弃 → review_status=rejected
```

---

## 七、模块关系与依赖

### 7.1 本模块依赖

| 依赖 | 状态 | 说明 |
|------|:--:|------|
| Phase 3-2.2 Public Parser Core | ✅ | VideoCandidate 数据来源 |
| VideoAsset (video_asset.py) | ✅ | 31 字段已实现 |
| competitor_master.csv | ✅ | account_purpose 字段提供分类依据 |
| PV_OS_V3.2_ARCHITECTURE_LOCK.md | ✅ | 架构规则约束 |

### 7.2 本模块输出

| 输出 | 目标模块 | 用途 |
|------|------|------|
| VideoAnalysisResult | 04_CONTENT/analytics/ | 单视频分析存档 |
| ContentInsight | 04_CONTENT/strategy/ | 内容策略决策 |
| ScriptEntry | 04_CONTENT/scripts_ai/ | 拍摄制作 |

### 7.3 不修改的模块（锁定）

| 模块 | 原因 |
|------|------|
| Pipeline (comment_to_lead_pipeline.yml) | Outbound 闭环独立运行 |
| Agent (comment_analyzer / lead_scoring_agent / competitor_account_agent) | 已验证，不在此阶段范围 |
| CRM (05_CUSTOMER_CRM/) | 数据格式不变 |
| Lead Score (CUSTOMER_SCORE_MODEL.md) | 评分规则不变 |
| Business Rules (PV_OS_GOVERNANCE_RULES.md) | 治理规则不变 |
| Public Collector / Parser | 已在 Phase 3-2 交付 |

### 7.4 与 Inbound 闭环的关系

Content Intelligence 是 Inbound 闭环的起点：

```
Content Intelligence (本文档)
    │
    ▼
二创脚本 (ScriptLibrary)
    │
    ▼
自有账号发布
    │
    ▼
新评论产生
    │
    ▼
Inbound Detection (Phase 2C 已完成)
    │
    ▼
Alert Engine (Phase 2C 已完成)
    │
    ▼
飞书通知 (Phase 3-1 已完成)
```

---

## 八、已有的 Phase 2B 代码（不动）

以下代码在 Phase 2B 已实现（mock 模式），Phase 3-3 编码时直接沿用接口，不重构：

| 模块 | 文件 | 行数 | 状态 |
|------|------|:--:|:--:|
| VideoAsset | `08_SYSTEM/scripts/video_asset.py` | 269 | ✅ 31字段 |
| VideoAnalysisResult | `08_SYSTEM/scripts/video_analysis_model.py` | 269 | ✅ 16字段 + ReusableElements |
| ContentIntelligenceAgent | `08_SYSTEM/scripts/content_intelligence_agent.py` | 405 | ✅ mock 模式 |
| ScriptLibrary | `08_SYSTEM/scripts/script_library_model.py` | 316 | ✅ ScriptEntry + ScriptScene |

---

## 九、Phase 3-3 编码阶段待办

| # | 任务 | 内容 | 依赖 |
|:--:|------|------|------|
| 1 | video_analysis_model 扩展 | 新增字段：conflict_pattern / cta_analysis / user_resonance | 无 |
| 2 | ContentInsight 实现 | 跨视频聚合分析 + JSON 输出 | 需 ≥5 条已分析视频 |
| 3 | ScriptLibrary 扩展 | 增加 production_mode (human_shoot / ai_digital) | 无 |
| 4 | content_calendar.csv 初始化 | 本周发布计划模板 | 无 |
| 5 | content_to_lead_mapping.csv 初始化 | 内容归因模型 | CRM ≥ 1 条 Inbound Lead |

---

## 十、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-21 | 初版：12维分析 + 竞品分类 + 四层复用 |
| **V2.0** | **2026-07-21** | **重构：明确七项业务目标、八维分析模型、A/B类账号分离、Content Insight + Script Library 完整定义** |
