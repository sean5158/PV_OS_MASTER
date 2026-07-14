# PV_OS_COMMENT_COLLECTION_TASK_MODEL

版本：V1.0
日期：2026-07-13
用途：PV_OS 评论采集任务模型——定义 comment_collector_agent 的任务结构、调度规则、增量采集、失败重试及与自动化引擎的连接

> 设计原则：仅基于已有固化规则文件设计，不自行创造业务规则。
> 核心聚焦：城市小区光伏客户。
>
> 依赖文档：
> - `PV_OS_MASTER_CONTEXT.md` — 项目全局上下文
> - `PV_OS_COMPETITOR_ACCOUNT_MODEL.md` V1.0 — 上游账号库
> - `COMMENT_COLLECTOR_AGENT_DESIGN.md` V2.0 — 任务执行者
> - `PV_OS_COMMENT_COLLECTION_STRATEGY.md` V2.0 — 采集策略
> - `10_AI_AUTOMATION_ENGINE/` — 调度与 pipeline

---

## 一、采集任务定位

### 1.1 任务模型在 PV_OS 中的位置

```
competitor_master.csv（竞品账号库）
    │  账号状态 = active
    ▼
┌─────────────────────────────────────────────────┐
│  采集任务模型（本文档定义）                          │
│  职责：将账号 → 转化为可执行任务 → 调度 → 监控      │
│  位置：账号库与 comment_collector_agent 之间        │
└─────────────────────────────────────────────────┘
    │  分发任务
    ▼
comment_collector_agent
    │  执行采集
    ▼
02_DATA/raw/
```

### 1.2 任务模型如何驱动 comment_collector_agent

```
任务模型                            comment_collector_agent
────────                            ─────────────────────
定义"采集谁"        ──────────→     读取 task 中的 account_id
定义"多久采一次"    ──────────→     按 collection_frequency 触发
定义"采哪些视频"    ──────────→     按 video_filter 筛选
定义"采多少评论"    ──────────→     按 comment_limit 控制深度
定义"上次采到哪"    ──────────→     按 last_collected_comment_id 增量
```

| 任务模型负责 | comment_collector_agent 负责 |
|------------|---------------------------|
| ✅ 什么时候采集 | ✅ 怎么采集 |
| ✅ 采集哪个账号 | ✅ 连接哪个平台 |
| ✅ 采集什么范围 | ✅ 数据格式标准化 |
| ✅ 是否成功/失败 | ✅ 写入 02_DATA/raw/ |
| ✅ 增量还是全量 | ✅ 触发 pipeline |

### 1.3 与已有 pipeline 的关系

```
任务模型 scheduler（周期性检查 pending 任务）
    │  触发
    ▼
comment_collector_agent（执行采集）
    │  完成
    ▼
event_bus.new_comment_received
    │  触发
    ▼
comment_to_lead_pipeline.yml（现有 pipeline，不受影响）
```

> 引用：`10_AI_AUTOMATION_ENGINE/workflows/comment_to_lead_pipeline.yml`

---

## 二、任务结构

### 2.1 单任务定义

```json
{
  "task_id": "string              // 任务唯一 ID（格式：平台_账号ID_日期_序号）",
  "platform": "string             // douyin / xiaohongshu / bilibili / kuaishou",
  "account_id": "string           // 竞品账号 ID（对应 competitor_master.csv）",
  "account_name": "string         // 账号昵称（冗余，便于日志追踪）",
  "account_category": "string     // national_brand / regional_installer / city_case / renovation",
  "collection_frequency": "string // 采集频率：6h / daily / 3d / weekly",
  "video_filter": {
    "time_range_days": "integer   // 获取最近 N 天内的视频（默认 30）",
    "housing_match_only": "boolean // 是否仅采集房屋场景匹配的视频（P0=false, P1=true）",
    "video_types": ["array        // 目标视频类型：installation / roof_renovation / home_energy / revenue / price / renovation"]
  },
  "comment_limit": {
    "per_video": "integer         // 每个视频最多采集评论数（默认 50）",
    "time_window_days": "integer  // 评论时间窗口（0=不限，7=近7天，30=近30天）"
  },
  "status": "string               // pending / running / completed / failed / paused",
  "last_run_time": "datetime      // 上次执行时间",
  "last_collected_comment_id": "string // 上次采集到的最后一条评论 ID（增量采集标记）",
  "next_run_time": "datetime      // 下次计划执行时间",
  "retry_count": "integer         // 当前重试次数",
  "max_retries": "integer         // 最大重试次数（默认 3）",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 2.2 字段说明

| 字段 | 说明 | 来源 |
|------|------|------|
| `task_id` | 全局唯一，格式 `{platform}_{account_id}_{YYYYMMDD}_{seq}` | 系统生成 |
| `platform` / `account_id` / `account_name` / `account_category` | 从 `competitor_master.csv` 同步 | 账号库 |
| `collection_frequency` | 由账号 `priority` 决定：P0→6h, P1→daily, P2→weekly | 账号库 |
| `video_filter.housing_match_only` | P0 账号 false（全量视频），P1 账号 true（仅房屋场景匹配） | 账号 category |
| `comment_limit.time_window_days` | P0 账号 0（不限时间），P1 账号 7（近 7 天），首次采集 30 | 采集策略 |
| `last_collected_comment_id` | 增量采集的锚点，防止重复采集 | collector 回写 |
| `status` | 任务生命周期状态 | 本文档 §三 |

### 2.3 任务生成规则

每个 active 状态账号对应 0 或 1 个 pending 任务：

```
competitor_master.csv（账号状态 = active）
    │
    ▼
检查是否存在 pending/running 任务
    ├── 不存在 → 生成新任务，status = pending
    └── 存在 → 不重复生成
```

任务完成后，根据 `collection_frequency` 自动生成下一周期任务（`next_run_time = now + frequency`）。

---

## 三、采集流程

### 3.1 完整任务执行流程

```
账号（competitor_master.csv, status = active）
    │
    ▼
任务生成（status = pending, next_run_time = now）
    │  scheduler 检查到达 next_run_time 的 pending 任务
    ▼
任务拾取（status → running）
    │
    ▼
comment_collector_agent 执行：
    ├── Step 1: 加载任务参数（account_id / video_filter / comment_limit）
    ├── Step 2: 获取账号最近 N 条视频（video_filter.time_range_days）
    ├── Step 3: AI 分析视频标题 → 筛选目标视频
    ├── Step 4: 对每个目标视频采集评论
    │     ├── 首次采集：全量评论（首个 comment_limit.time_window_days 天）
    │     └── 增量采集：仅采集 last_collected_comment_id 之后的新评论
    ├── Step 5: 去重 + 格式标准化
    └── Step 6: 写入 02_DATA/raw/
    │
    ▼
任务完成：
    ├── status → completed
    ├── last_collected_comment_id ← 本次最后一条评论 ID
    ├── next_run_time ← now + collection_frequency
    └── 发布 new_comment_received 事件
```

### 3.2 任务状态流转

```
 pending  ──→  running  ──→  completed  ──→（自动生成下一周期 pending）
    │              │
    │              ├──→  failed  ──→  retry（retry_count < max_retries）
    │              │                    │
    │              │                    └──→  failed_final（retry_count = max_retries）
    │              │
    │              └──→  paused（人工暂停）
    │
    └──→  cancelled（账号 status 变为 inactive/paused/inaccessible）
```

### 3.3 状态定义

| 状态 | 含义 | 何时进入 |
|------|------|---------|
| `pending` | 等待执行 | 任务创建后 / 上一周期完成后自动生成 |
| `running` | 正在执行 | scheduler 分发给 collector |
| `completed` | 执行成功 | collector 正常完成 |
| `failed` | 执行失败，等待重试 | collector 异常退出 |
| `failed_final` | 最终失败 | retry_count 达到 max_retries |
| `paused` | 人工暂停 | 手动操作 |
| `cancelled` | 已取消 | 对应账号变为 inactive/paused/inaccessible |

---

## 四、增量采集规则

### 4.1 核心原则

**不重复采集已入库的评论。** 每次采集只获取上次采集之后的新增评论。

### 4.2 增量标记机制

```
每次采集完成后：

comment_collector_agent 回写：
    task.last_collected_comment_id = 本次采集到的最后一条评论的平台原始 ID
    task.last_run_time = 本次采集完成时间

下次采集时：

comment_collector_agent 读取：
    task.last_collected_comment_id
    → 只采集此 ID 之后的新评论
    → 不重新拉取已入库的旧评论
```

### 4.3 首次采集 vs 增量采集

| 场景 | 采集范围 | 时间窗口 |
|------|---------|:--:|
| **首次采集**（无 `last_collected_comment_id`） | P0 账号近 30 天全量评论 / P1 账号近 7 天全量评论 | 30 天 / 7 天 |
| **增量采集**（有 `last_collected_comment_id`） | 仅 `last_collected_comment_id` 之后的新评论 | 不限制 |
| **重新全量**（手动触发，通常用于账号内容大变更后） | 重置 `last_collected_comment_id = null`，按首次采集规则 | 30 天 / 7 天 |

### 4.4 去重保障

增量采集之外，collector 输出前还需全局去重：

```
按 comment_id（平台_视频ID_评论ID）全局比对
    ├── 已存在 → 跳过（保留原记录）
    └── 不存在 → 写入
```

去重范围：同平台 + 同账号下的所有历史批次。

---

## 五、失败重试机制

### 5.1 重试策略

| 失败次数 | 重试间隔 | 策略 |
|:------:|---------|------|
| 第 1 次 | 5 分钟后 | 自动重试 |
| 第 2 次 | 30 分钟后 | 自动重试 |
| 第 3 次 | 2 小时后 | 自动重试 |
| 超过 3 次 | — | 标记 `failed_final`，停止自动重试，人工介入 |

### 5.2 失败分类

| 失败类型 | 是否重试 | 说明 |
|---------|:------:|------|
| 平台 API 超时 | ✅ | 网络波动，重试大概率成功 |
| 平台限流 | ✅ | 等待冷却后重试 |
| 账号已注销/私密 | ❌ | 不可恢复，标记账号 `inaccessible`，任务 `cancelled` |
| 账号无新视频 | ❌ | 非失败，标记 `completed` + 日志记录 |
| 数据格式异常 | ❌ | 采集成功但部分评论格式异常，标记 `completed` + 错误统计 |

### 5.3 失败任务日志

```json
{
  "task_id": "douyin_cd_pv_001_20260713_001",
  "status": "failed_final",
  "retry_count": 3,
  "error_log": [
    {
      "attempt": 1,
      "time": "2026-07-13 08:05:00",
      "error_type": "api_timeout",
      "error_message": "Connection timeout after 30s"
    },
    {
      "attempt": 2,
      "time": "2026-07-13 08:35:00",
      "error_type": "rate_limited",
      "error_message": "HTTP 429 Too Many Requests"
    },
    {
      "attempt": 3,
      "time": "2026-07-13 10:35:00",
      "error_type": "api_timeout",
      "error_message": "Connection timeout after 30s"
    }
  ],
  "resolution": "manual_intervention_required"
}
```

---

## 六、与 10_AI_AUTOMATION_ENGINE 连接

### 6.1 调度器（scheduler）

```
10_AI_AUTOMATION_ENGINE/scheduler/
    │
    ▼
周期性扫描任务表
    │  WHERE status = 'pending' AND next_run_time <= now()
    ▼
按优先级排序（P0 任务优先于 P1 任务）
    │
    ▼
分配给 comment_collector_agent 执行
```

### 6.2 调度配置

```yaml
# 10_AI_AUTOMATION_ENGINE/scheduler/collection_scheduler.yml
name: collection_task_scheduler

scan_interval: 300                # 每 5 分钟扫描一次

priority:
  P0:                             # 每 6 小时采集任务
    frequency: 6h
    max_concurrent: 3             # 最多 3 个 P0 任务并发
    platforms: [douyin]

  P1:                             # 每日采集任务
    frequency: daily
    max_concurrent: 5
    platforms: [douyin, xiaohongshu, bilibili]
    preferred_time: "09:00"

  P2:                             # 每周采集任务
    frequency: weekly
    max_concurrent: 2
    platforms: [kuaishou]
    preferred_day: monday
    preferred_time: "09:00"
```

### 6.3 与 event_bus 的连接

```
任务完成（status = completed）
    │  且 有新增评论（collected_count > 0）
    ▼
发布事件到 event_bus
    {
      "event": "new_comment_received",
      "task_id": "...",
      "platform": "douyin",
      "batch_path": "02_DATA/raw/douyin/2026-07-13/batch_06h_001.json",
      "stats": {
        "comments_collected": 175,
        "housing_signal_high": 34,
        "demand_signal_true": 28,
        "ip_city_match": 98,
        "recency_recent": 112
      }
    }
    │
    ▼
触发 comment_to_lead_pipeline.yml
```

### 6.4 与现有 pipeline 的关系

任务模型和 pipeline 是协作关系，不是替代关系：

| 任务模型（本文档） | pipeline（已有） |
|-----------------|---------------|
| 管理"什么时候采集" | 管理"采集到之后怎么处理" |
| 生成和执行采集任务 | 触发分析→评分→CRM 流程 |
| 发布 `new_comment_received` 事件 | 消费 `new_comment_received` 事件 |

---

## 七、开发规划

### 7.1 P0：任务模型设计

| # | 任务 | 产出 |
|:-:|------|------|
| 1 | 定义任务数据结构（task schema） | 本文档 §二 |
| 2 | 定义任务状态流转规则 | 本文档 §三 |
| 3 | 建立任务存储（CSV/JSON） | `02_DATA/01_COLLECTION/tasks/` |
| 4 | 手工创建首批 P0 账号的初始任务 | 10 个账号 × 首次全量采集任务 |

### 7.2 P1：调度执行

| # | 任务 | 依赖 |
|:-:|------|------|
| 5 | 实现任务扫描器（scheduler 读取 pending 任务） | P0 任务存储就绪 |
| 6 | 实现增量采集标记（last_collected_comment_id 回写） | collector 可执行 |
| 7 | 实现失败重试机制（3 次 + 退避） | collector 可执行 |
| 8 | 连接 event_bus（completed → new_comment_received） | pipeline 就绪 |

### 7.3 P2：自动化完整

| # | 任务 |
|:-:|------|
| 9 | 任务自动生成（账号入库 → 自动创建首次采集任务） |
| 10 | 任务效果监控（采集量/城市信号占比/失败率看板） |
| 11 | 任务自动扩缩（高产出账号自动提升频率，低产出账号自动降级） |
| 12 | 跨平台任务协调（避免同时大量请求触发限流） |

---

## 八、任务示例

### 8.1 P0 任务示例（区域安装商，每 6 小时）

```json
{
  "task_id": "douyin_cd_pv_001_20260713_001",
  "platform": "douyin",
  "account_id": "douyin_cd_pv_001",
  "account_name": "成都光伏老王",
  "account_category": "regional_installer",
  "collection_frequency": "6h",
  "video_filter": {
    "time_range_days": 30,
    "housing_match_only": false,
    "video_types": ["installation", "roof_renovation", "home_energy", "revenue", "price"]
  },
  "comment_limit": {
    "per_video": 50,
    "time_window_days": 0
  },
  "status": "completed",
  "last_run_time": "2026-07-13 06:00:00",
  "last_collected_comment_id": "douyin_v123456_c789",
  "next_run_time": "2026-07-13 12:00:00",
  "retry_count": 0,
  "max_retries": 3
}
```

### 8.2 P1 任务示例（全国品牌，每日）

```json
{
  "task_id": "douyin_zhengtai_20260713_001",
  "platform": "douyin",
  "account_id": "douyin_zhengtai",
  "account_name": "正泰安能",
  "account_category": "national_brand",
  "collection_frequency": "daily",
  "video_filter": {
    "time_range_days": 7,
    "housing_match_only": true,
    "video_types": ["installation", "home_energy"]
  },
  "comment_limit": {
    "per_video": 30,
    "time_window_days": 7
  },
  "status": "pending",
  "last_run_time": "2026-07-12 09:00:00",
  "last_collected_comment_id": "douyin_v987654_c321",
  "next_run_time": "2026-07-13 09:00:00",
  "retry_count": 0,
  "max_retries": 3
}
```

### 8.3 任务调度时间线示例

```
08:00  scheduler 扫描
       ├── douyin_cd_pv_001（P0，next_run_time=08:00）→ running
       ├── douyin_cq_pv_002（P0，next_run_time=08:00）→ running
       └── xiaohongshu_sunroom_01（P0，next_run_time=08:00）→ running（并发限制）

08:05  三个 P0 任务完成 → completed
       → 自动生成下一周期任务（next_run_time = 14:00）
       → 发布 new_comment_received × 3

09:00  scheduler 扫描
       ├── douyin_zhengtai（P1，next_run_time=09:00）→ running
       └── xiaohongshu_villa_01（P1，next_run_time=09:00）→ running
```

---

## 九、约束与禁止

| # | 约束 | 来源 |
|:-:|------|------|
| 1 | 不修改评分模型原文件 | `CUSTOMER_SCORE_MODEL.md` |
| 2 | 不修改 CRM 结构 | `05_CUSTOMER_CRM/` |
| 3 | 不修改已有规则文件 | `02_DATA/`、`00_SYSTEM/` |
| 4 | 不创建新的客户等级 | 等级由 lead_scoring_agent 判定 |
| 5 | 任务模型不替代 comment_to_lead_pipeline | 任务模型管采集调度，pipeline 管数据处理 |
| 6 | 增量采集不删除历史数据 | `COMMENT_DATA_LIFECYCLE_RULE.md` |

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-13 | 首次建立采集任务模型：任务结构（16 字段）、采集流程（6 步 + 7 状态流转）、增量采集机制（last_collected_comment_id 锚点）、失败重试（3 次退避 + 分类处理）、scheduler 连接、P0/P1/P2 开发规划、2 个任务示例 + 调度时间线示例 |
