# PV_OS_DATA_ASSET_ARCHITECTURE V3.0

版本：V3.0
日期：2026-07-20
用途：PV_OS 数据资产架构 — 定义一次采集形成的全部长期数据资产及其关系

> 本次不做代码修改。本文为架构设计文件。

---

## 一、核心原则

**一次采集，形成长期资产，多次消费。**

不是"采集评论 → 分析一次 → 丢弃"。而是：

```
一次平台公开搜索/采集
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                  三层长期资产                           │
│                                                       │
│  Account Asset     Video Asset     Comment User Asset  │
│  (账号是谁)         (发了什么)       (谁在评论)          │
└───────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ 客户发现       │  │ 爆款拆解       │  │ Lead评分       │
│ 竞品监控       │  │ 二创脚本       │  │ CRM入库        │
│ 市场分析       │  │ 内容策略       │  │ 用户画像       │
└───────────────┘  └───────────────┘  └───────────────┘
```

---

## 二、Account Asset（账号资产）

### 2.1 存储位置

```
02_DATA/02_COMPETITOR_DATABASE/
├── competitor_master.csv        # 竞品账号主表
├── own_account_master.csv       # 自有账号主表（新增）
└── discovery_logs/              # 发现日志
```

### 2.2 competitor_master.csv（扩展现有）

| 字段 | 类型 | 说明 |
|------|------|------|
| `competitor_id` | string | 内部唯一ID |
| `platform` | string | douyin/xiaohongshu/kuaishou/shipinhao |
| `account_id` | string | 平台账号ID |
| `account_name` | string | 昵称 |
| `account_url` | string | 主页链接 |
| `account_type` | string | national_brand/regional_installer/city_case/renovation |
| **`account_purpose`** | string | 🆕 customer_source / content_learning / both |
| **`learning_priority`** | int | 🆕 1-10，内容学习优先级（仅 purpose=content_learning/both 时有效） |
| `bio` | string | 简介 |
| `grade` | string | S/A/B |
| `total_score` | int | 六维评分总分 |
| `discovery_keyword` | string | 发现关键词 |
| `discovery_date` | date | 首次发现日期 |
| `follower_count` | int | 粉丝数 |
| `ip_location` | string | IP属地 |
| `region` | string | 账号所在地 |
| `monitor_frequency` | string | 6h/daily/3d/weekly |
| `status` | string | active/paused/deprecated |
| **`last_content_analyzed_at`** | datetime | 🆕 最近一次内容分析时间 |
| `created_at` | datetime | 入库时间 |
| `updated_at` | datetime | 最后更新时间 |

### 2.3 own_account_master.csv（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_id` | string | 内部ID |
| `platform` | string | 平台 |
| `platform_account_id` | string | 平台账号ID |
| `account_name` | string | 昵称 |
| `account_url` | string | 主页链接 |
| `account_type` | string | 个人/企业 |
| `content_frequency` | string | 发布频率 |
| `primary_topic` | string | 主要内容方向 |
| `monitor_comments` | boolean | 是否监控该账号评论（默认true） |
| `created_at` | datetime | 注册时间 |

---

## 三、Video Asset（视频资产）

### 3.1 存储位置

```
02_DATA/04_COMMENT_DATABASE/
├── video_asset_store.csv        # 🆕 视频资产主表
└── video_analysis/              # 🆕 视频AI分析结果
```

### 3.2 video_asset_store.csv（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| `video_id` | string | 平台视频唯一ID |
| `video_url` | string | 视频链接 |
| `platform` | string | 平台 |
| `author_id` | string | 发布者平台ID |
| `author_name` | string | 发布者昵称 |
| `author_url` | string | 发布者主页链接 |
| `title` | string | 视频标题 |
| `description` | string | 视频描述 |
| `publish_time` | datetime | 发布时间 |
| `duration_seconds` | int | 时长 |
| **基础互动** | | |
| `like_count` | int | 点赞 |
| `comment_count` | int | 评论 |
| `collect_count` | int | 收藏 |
| `share_count` | int | 转发 |
| **AI分析** | | 🆕 内容智能层 |
| `hook_3_seconds` | string | 黄金三秒钩子 |
| `pain_point` | string | 用户痛点 |
| `customer_type` | string | 目标客群 |
| `video_structure` | string | 结构拆解 |
| `title_pattern` | string | 标题模式 |
| `comment_trigger` | string | 评论触发点 |
| `viral_reason` | string | 爆款原因 |
| `turning_point` | string | 转折点 |
| `closing_factor` | string | 成交因素 |
| `housing_signal` | string | 房屋场景信号 |
| `relevance_score` | int | 与PV_OS相关度 0-10 |
| `collected_at` | datetime | 采集时间 |
| `analyzed_at` | datetime | AI分析时间 |

---

## 四、Comment User Asset（评论用户资产）

### 4.1 存储位置

```
02_DATA/04_COMMENT_DATABASE/
├── comment_asset_library.csv    # 扩展现有
└── comment_users/               # 🆕 用户画像持久化
```

### 4.2 comment_asset_library.csv（扩展字段）

现有字段 + 新增：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 评论ID |
| `platform` | string | 平台 |
| `content` | string | 评论正文 |
| `author` | string | 用户昵称 |
| `create_time` | datetime | 评论时间 |
| `source_url` | string | 来源视频链接 |
| `ip_location` | string | IP属地 |
| **`user_id`** | string | 🆕 平台用户唯一ID |
| **`user_profile_url`** | string | 🆕 用户主页链接 |
| **`comment_like_count`** | int | 🆕 评论点赞数 |
| **`reply_count`** | int | 🆕 回复数 |
| **`video_author_id`** | string | 🆕 视频发布者 |
| `collected_time` | datetime | 采集时间 |
| `processing_status` | string | collected/cleaned/analyzed |
| **`intent_score`** | int | 🆕 意图评分 0-100 |
| **`region_tag`** | string | 🆕 区域标签 |
| **`lead_grade`** | string | 🆕 S/A/B/C |
| **`is_own_account`** | boolean | 🆕 是否来自自有账号视频 |

---

## 五、Content Asset（内容资产）🆕

### 5.1 存储位置

```
04_CONTENT/
├── analytics/
│   ├── content_insight.json         # 🆕 竞品内容洞察
│   ├── content_performance.csv      # 🆕 自有内容效果
│   └── content_to_lead_mapping.csv  # 🆕 内容→线索归因
├── strategy/
│   └── content_strategy.md          # 🆕 内容策略文档
├── calendar/
│   └── content_calendar.csv         # 🆕 发布日历
├── scripts/                         # 脚本输出
├── scripts_ai/                      # AI二创脚本
├── materials/                       # 素材库
└── viral_analysis/                  # 爆款拆解报告
```

### 5.2 content_insight.json（新增）

```json
{
  "generated_at": "2026-07-20",
  "source_period": "最近30天",
  "topics": [
    {"topic": "别墅光伏安装", "count": 45, "avg_comments": 120, "trend": "rising"},
    {"topic": "光伏省钱计算", "count": 32, "avg_comments": 85, "trend": "stable"}
  ],
  "demand_gaps": [
    {"gap": "成都老旧小区光伏安装", "demand_signals": 28, "content_count": 3},
    {"gap": "阳光房光伏避坑", "demand_signals": 15, "content_count": 1}
  ],
  "title_patterns": [
    {"pattern": "我家别墅装了光伏，一年省了X万", "effectiveness": "high"},
    {"pattern": "XX平米屋顶，光伏发电够不够用？", "effectiveness": "high"}
  ],
  "hook_formulas": [
    {"formula": "数字对比型", "example": "电费从3000降到300"},
    {"formula": "场景痛点型", "example": "阳光房太晒怎么办"}
  ]
}
```

### 5.3 content_performance.csv（新增）

| 字段 | 说明 |
|------|------|
| `content_id` | 内容ID |
| `platform` | 发布平台 |
| `publish_time` | 发布时间 |
| `views` | 播放量 |
| `likes` | 点赞 |
| `comments` | 评论数 |
| `shares` | 转发 |
| `leads_generated` | 产生的线索数 |
| `top_comment_themes` | 评论主要话题 |

### 5.4 content_calendar.csv（新增）

| 字段 | 说明 |
|------|------|
| `date` | 发布日期 |
| `platform` | 平台 |
| `topic` | 选题 |
| `content_type` | 视频/图文 |
| `target_audience` | 目标客群 |
| `source` | 原创/二创/竞品参考 |
| `status` | planned/writing/reviewing/published |

---

## 六、资产关系模型

```
                    ┌─────────────────────┐
                    │  Platform Search     │
                    │  (一次公开搜索)       │
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     Account Asset      Video Asset     Comment Asset
              │               │               │
              │        ┌──────┴──────┐        │
              │        ▼             ▼        │
              │  content_insight  viral_      │
              │  (选题发现)       analysis    │
              │                  (爆款拆解)    │
              │        │             │        │
              │        └──────┬──────┘        │
              │               ▼               │
              │     content_calendar          │
              │     scripts_ai/               │
              │     (二创脚本)                 │
              │                               │
              └───────────┬───────────────────┘
                          ▼
                   Lead Scoring
                          │
                  ┌───────┴───────┐
                  ▼               ▼
              CRM (outbound)  Alert Engine (inbound)
              (主动找客户)      (客户主动咨询)
```

---

## 七、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V3.0 | 2026-07-20 | 首次建立三层资产架构：Account + Video + Comment User + Content 四个资产模型 |
