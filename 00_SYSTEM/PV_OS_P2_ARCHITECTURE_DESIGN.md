# PV_OS P2 数据接入架构设计 V2.1

版本：V2.1
日期：2026-07-20
状态：**P2 架构重设计 — 基于规则校准结果**

> V1.0 → V2.1 变更：从 "API采集模式" 调整为 "关键词驱动→公开搜索→发现→采集" 七步链路，增加竞品发现层。
>
> 依赖规则：
> - `00_SYSTEM/PV_OS_MASTER_CONTEXT.md` — 项目定位
> - `00_SYSTEM/PV_OS_GOVERNANCE_RULES.md` — 治理规范（商业价值第一）
> - `02_DATA/01_KEYWORD_LIBRARY/KEYWORD_STRATEGY.md` — 关键词八源体系
> - `02_DATA/02_COMPETITOR_DATABASE/COMPETITOR_DISCOVERY_ALGORITHM.md` — 六阶段竞品发现
> - `PV_OS_COMMENT_COLLECTION_STRATEGY.md` V2.1 — 采集策略
> - `COMMENT_COLLECTOR_AGENT_DESIGN.md` V2.1 — Collector 设计
> - `PV_OS_COMMENT_COLLECTION_TASK_MODEL.md` V1.0 — 任务模型

---

## A. 修正后的完整数据链路

### A.1 规则定义的核心路线

来自 `COMPETITOR_DISCOVERY_ALGORITHM.md` + `COMMENT_COLLECTOR_AGENT_DESIGN.md` + `KEYWORD_STRATEGY.md`：

```
关键词驱动 → 平台公开搜索 → 发现竞品账号 → 发现视频 → 采集公开评论 → AI分析 → CRM
```

这是 PV_OS 定义的核心获客链路。**任何偏离此路线的设计都应纠正。**

### A.2 完整七步架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PV_OS P2 完整数据链路                              │
│                                                                          │
│  Layer 1: 关键词引擎（KEYWORD_STRATEGY.md）                               │
│  ┌────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ 人工词根    │───→│ 平台联想词    │───→│ AI扩展 +     │                  │
│  │ seed_      │    │ suggest API  │    │ 五维评分     │                  │
│  │ keywords   │    │ (公开接口)    │    │ (S/A/B/C)   │                  │
│  └────────────┘    └──────────────┘    └──────┬───────┘                  │
│                                                │                         │
│  Layer 2: 竞品发现引擎（COMPETITOR_DISCOVERY_ALGORITHM.md）               │
│  ┌────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ 平台搜索    │───→│ 搜索结果初筛  │───→│ 六维评分 +   │                  │
│  │ 公开搜索框  │    │ (7种排除规则) │    │ S/A/B 入库   │                  │
│  └────────────┘    └──────────────┘    └──────┬───────┘                  │
│                                                │                         │
│  Layer 3: 账号主表（competitor_master.csv）                               │
│  ┌──────────────────────────────────────────────┐                        │
│  │  竞品账号主表 (AI自动发现 + 人工补充)          │                        │
│  │  字段: competitor_id / platform / grade /     │                        │
│  │        discovery_keyword / monitor_frequency   │                        │
│  └──────────────────────┬───────────────────────┘                        │
│                          │                                               │
│  Layer 4: 任务模型（PV_OS_COMMENT_COLLECTION_TASK_MODEL.md）              │
│  ┌──────────────────────┴───────────────────────┐                        │
│  │  TaskManager: 账号→任务转化 / 7状态机 / 增量游标 │                       │
│  │  seed_from_accounts() 从主表批量创建            │                        │
│  └──────────────────────┬───────────────────────┘                        │
│                          │                                               │
│  Layer 5: 调度器（collection_scheduler V2）                               │
│  ┌──────────────────────┴───────────────────────┐                        │
│  │  读取pending任务 / 并发控制 / 执行日志 / 重试拾取 │                      │
│  └──────────────────────┬───────────────────────┘                        │
│                          │                                               │
│  Layer 6: Public Data Collector（重新定位）                                │
│  ┌──────────────────────┴───────────────────────┐                        │
│  │  平台公开数据采集:                              │                        │
│  │  ├─ Mock模式: 测试数据 (始终可用)               │                        │
│  │  ├─ File模式: CSV/手动导出导入                  │                        │
│  │  └─ Public模式: 平台公开搜索+浏览+采集           │                        │
│  │      (非API调用，是公开可访问内容的采集)          │                        │
│  └──────────────────────┬───────────────────────┘                        │
│                          │                                               │
│  Layer 7: Pipeline + AI（不改动）                                         │
│  ┌──────────────────────┴───────────────────────┐                        │
│  │  raw/ → data_cleaner → Pipeline 10步          │                        │
│  │  → Intent Model → Comment Analyzer            │                        │
│  │  → Lead Scoring → CRM                        │                        │
│  └──────────────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### A.3 关键设计变更（V1.0 → V2.1）

| V1.0 (旧) | V2.1 (新) | 原因 |
|------|------|------|
| `collection_scheduler → create_collector()` 直接从已知账号采集 | 增加 Layer 1-3：先通过关键词搜索发现账号 | 规则要求"关键词驱动→搜索→发现" |
| `mode=live` = API采集 | `mode=public` = 公开数据采集 | 重新定位为 Public Data Collector |
| 账号来源：用户手工填 CSV | 账号来源：AI自动发现(主) + 手工补充(辅) | `COMPETITOR_DISCOVERY_ALGORITHM.md` §一 |
| DouyinLiveCollector 核心是 API | DouyinLiveCollector 核心是公开搜索/浏览 | 非API优先，公开数据优先 |
| `competitor_accounts.csv` = 唯一账号来源 | `competitor_master.csv` = AI发现入库 + 人工标记 | 规则要求"AI自动发现" |

---

## B. 新增模块：Competitor Discovery Layer

### B.1 定位

竞品发现层是 P2 重构的核心新增模块。它实现 `COMPETITOR_DISCOVERY_ALGORITHM.md` 定义的完整六阶段流程。

### B.2 模块结构

```
02_DATA/02_COMPETITOR_DATABASE/
├── competitor_master.csv              # 竞品账号主表 (AI填入+人工补充)
├── discovery_logs/                    # 发现日志 (按日期)
│   └── YYYY-MM-DD.json
├── COMPETITOR_SCORE_RULE.md           # 评分规则 (已有)
├── COMPETITOR_DISCOVERY_ALGORITHM.md  # 发现算法 (已有)
└── COMPETITOR_ACCOUNT_MODEL.md        # 账号模型 (已有)

08_SYSTEM/scripts/
└── competitor_discovery.py            # [新] 竞品发现引擎

10_AI_AUTOMATION_ENGINE/
└── workflows/
    └── competitor_discovery_pipeline.yml  # [新] 竞品发现工作流
```

### B.3 discovery 数据流

```
seed_keywords.yml (S/A级)
    │
    ▼
competitor_discovery.py
    │
    ├─ Phase 1: 关键词投放
    │   └─ 对每个 keyword: 平台搜索框 → 获取搜索结果列表
    │
    ├─ Phase 2: 初筛
    │   └─ 7种排除: 资讯号/厂商号/科普号/异地无关/注销/大型集团/个人生活号
    │
    ├─ Phase 3: 内容分析
    │   └─ 获取账号详情: 昵称/简介/近期视频标题/粉丝数/IP属地
    │
    ├─ Phase 4: 六维评分 (COMPETITOR_SCORE_RULE.md)
    │   └─ 业务匹配(30) + 城市家庭光伏(20) + 别墅权重(15) + 区域(15) + 需求价值(10) + 活跃度(10)
    │
    ├─ Phase 5: 入库
    │   └─ S/A级 → competitor_master.csv + 生成首次采集任务
    │   └─ B级 → 候选池，月度重评
    │   └─ C级 → 标记，不入库
    │
    └─ Phase 6: 日报
        └─ 写入 discovery_logs/YYYY-MM-DD.json
```

### B.4 与现有模块的关系

| 现有模块 | 变更 |
|------|------|
| `competitor_accounts.csv` | **重命名/合并** → `competitor_master.csv`。当前仅1条测试数据。明确标注"AI自动发现填充主字段，人工仅补充 monitor_level 标记" |
| `TaskManager.seed_from_accounts()` | 不变。从 `competitor_master.csv` 读取 active 账号生成任务 |
| `analyze_source_account` | 不变。Pipeline 中消费账号数据做来源分析 |
| `competitor_account_agent` | 扩展职责：从"来源分析"扩展包含"发现入库" |

### B.5 competitor_master.csv 字段定义

| 字段 | 填充方式 | 说明 |
|------|:--:|------|
| `competitor_id` | 自动 | PV_COMP_{seq} |
| `platform` | 自动 | 发现来源平台 |
| `account_id` | 自动 | 平台账号ID |
| `account_name` | 自动 | 昵称 |
| `account_url` | 自动 | 主页链接 |
| `account_type` | AI分类 | national_brand / regional_installer / city_case / renovation / personal_blogger |
| `grade` | AI评分 | S / A / B |
| `total_score` | AI评分 | 0-100 |
| `discovery_keyword` | 自动 | 发现该账号使用的关键词 |
| `discovery_date` | 自动 | 首次发现日期 |
| `follower_count` | 自动 | 粉丝数 |
| `ip_location` | 自动 | IP属地 |
| `monitor_level` | **人工** | S / A / B。人工确认AI评分后标记 |
| `monitor_frequency` | 自动 | 由 grade 推导: S→6h, A→daily, B→weekly |
| `customer_source_score` | AI | 评论区客户密度评分 0-100 |
| `account_authority_score` | AI | 账号权威度评分 0-100 |
| `status` | 自动 | active / paused / deprecated |

> **人工 vs AI 分工**：AI负责发现、评分、分类、填充。人工仅确认 `monitor_level` 和标记 `status`。这与 `PV_OS_GOVERNANCE_RULES.md` §四 "AI自动发现"一致。

---

## C. DouyinCollector 重新定位：Public Data Collector

### C.1 旧定位（V1.0）→ 新定位（V2.1）

| V1.0 | V2.1 |
|------|------|
| "抖音真实 API 采集器" | "抖音公开数据采集器" |
| `_fetch_video_list_live()` → 调用API | `_search_and_discover()` → 平台公开搜索框 |
| `_fetch_comments_live()` → 调用API | `_browse_and_collect()` → 浏览公开评论区 |
| 核心依赖：API key / client_secret | 核心依赖：公开搜索 / 公开页面浏览 |
| mode=`live` | mode=`public` |

### C.2 重新定义的接口

```
DouyinPublicCollector(LiveCollectorBase)    ← 继承关系不变
│
├─ search_accounts(keyword, depth)          ← [新] 关键词搜索→账号列表
│   └─ 实现: 平台搜索框公开结果解析
│
├─ discover_account(account_id)             ← [新] 获取账号详情
│   └─ 实现: 账号主页公开内容解析
│
├─ discover_videos(account_id, time_range)  ← [新] 发现目标视频
│   └─ 实现: 账号作品列表公开内容解析
│
├─ collect_comments(video_id, limit)        ← [重命名] 采集公开评论
│   └─ 原 _fetch_comments，重新表述为公开页面内容提取
│
└─ _parse_to_record(raw_item)              ← 不变
```

### C.3 mode 重命名

| 旧名称 | 新名称 | 含义 |
|------|------|------|
| `mock` | `mock` (不变) | 内置测试数据，Pipeline验证 |
| `file` | `file` (不变) | CSV/手动导出导入 |
| `live` | **`public`** | 平台公开数据采集（搜索框/公开页面浏览/评论区提取） |
| — | **`official`** (新增) | 平台官方API（需企业认证/API Key），作为public不可用时的升级路径 |

> 三模式优先级: `mock` (始终可用) > `public` (公开数据优先) > `official` (API作为补充)。
> `platform_adapter.py` 的 `CollectorMode.LIVE` 重命名为 `CollectorMode.PUBLIC`，新增 `CollectorMode.OFFICIAL`。
> 旧的 `mode=live` 参数值保持兼容，内部映射到 public。

### C.4 公开数据采集的技术含义

```
不是:
  ❌ GET https://open.douyin.com/video/list/          ← API调用
  ❌ 需要 client_key + client_secret + access_token    ← 认证模式
  ❌ 依赖平台开放平台权限                               ← 企业认证

而是:
  ✅ 模拟正常用户在平台搜索框输入关键词                    ← 公开搜索
  ✅ 浏览搜索结果列表，提取公开可见的账号信息              ← 公开浏览
  ✅ 浏览账号主页，提取公开可见的视频标题/评论内容         ← 公开内容
  ✅ 速率限制在正常用户行为范围 (≤10 req/min)            ← 合规
  ✅ 仅提取公开评论区内容，不触碰登录态/私信/粉丝群       ← 边界清晰
```

---

## D. 更新后的 Platform Adapter 架构

### D.1 mode 路由

```
platform_adapter.get_collector(platform, mode)
│
├─ mode=auto
│   ├─ csv_import / xiaohongshu → file (文件导入优先)
│   ├─ 有官方API凭证 → official
│   ├─ 配置 enable_public_collection=true → public
│   └─ 其他 → mock (始终可用)
│
├─ mode=mock     → 始终 Mock (Pipeline验证/测试，零依赖)
│
├─ mode=file     → CSV/手动导入 (小红书优先，绕过反爬)
│
├─ mode=public   → Public Data Collector
│   ├─ 平台公开搜索框 → 结果列表解析
│   ├─ 公开页面浏览 → 评论区内容提取
│   ├─ 速率限制 + 反爬策略
│   └─ 失败降级 → mock
│
└─ mode=official → Official API Collector (P2后期)
    ├─ 需企业认证 + API Key
    ├─ 作为 public 不可用时的升级路径
    └─ 失败降级 → public → mock
```

### D.2 更新后的 SUPPORTED_PLATFORMS

```python
SUPPORTED_PLATFORMS = [
    "douyin",        # Public Data Collector (P2)
    "xiaohongshu",   # File Import优先, Public预留
    "kuaishou",      # Public预留 (城市客户密度低)
    "wechat_video",  # 不采集 (无公开入口)
    "csv_import",    # 文件导入
]
```

---

## E. 更新后的 P2 实施路线图

### E.0 P2 前置：架构修正（本次）

| # | 内容 | 状态 |
|:--:|------|:--:|
| 1 | 更新 `PV_OS_P2_ARCHITECTURE_DESIGN.md` V2.1 | ✅ 本文档 |
| 2 | 更新 `platform_adapter.py`: `LIVE→PUBLIC` | ⬜ |
| 3 | 更新 `DouyinLiveCollector` → `DouyinPublicCollector` 文档 | ⬜ |
| 4 | 更新 `PV_OS_PROJECT_STATUS.md` P2 描述 | ⬜ |
| 5 | 现有 269 测试确保通过 | ⬜ |

### P2-1: 竞品发现引擎（新增，最高优先级）

| # | 内容 | 输出 |
|:--:|------|------|
| 1 | 实现 `competitor_discovery.py` — Phase 1-6 骨架 | 发现引擎脚本 |
| 2 | 实现关键词→平台搜索→结果解析 (Mock先行) | 搜索模块 |
| 3 | 实现初筛逻辑 (7种排除规则) | 筛选模块 |
| 4 | 实现六维评分 | 评分模块 |
| 5 | 实现 `competitor_master.csv` 读写 | 存储模块 |
| 6 | 实现发现日报 | 日志模块 |
| 7 | 端到端测试：关键词→搜索→发现→评分→入库 | 测试: 20+ |

### P2-2: Public Data Collector 重新定位（原 P2-3，调整方向）

| # | 内容 | 输出 |
|:--:|------|------|
| 1 | `DouyinLiveCollector` → `DouyinPublicCollector` | 重命名+重新表述 |
| 2 | 增加 `search_accounts()` / `discover_videos()` 接口 | 公开搜索接口 |
| 3 | `mode=live` → `mode=public` (platform_adapter) | mode 重命名 |
| 4 | 确保 Mock 兼容性 + 269 测试通过 | 回归 |
| 5 | 手动验证：关键词→搜索→浏览→提取 | 人工验证 |

### P2-3: CSV/File Import（已完成，方向不变）

| # | 内容 | 状态 |
|:--:|------|:--:|
| 1 | `csv_import_collector.py` | ✅ 已完成 |
| 2 | `mode=file` 路由 | ✅ 已完成 |
| 3 | 端到端测试 | ✅ 41/41 |

### P2-4: 数据闭环验证

| # | 内容 | 依赖 |
|:--:|------|:--:|
| 1 | 竞品发现→入库→TaskModel→Scheduler→Collector→Pipeline 全链路 | P2-1 + P2-2 |
| 2 | 城市客户占比评估 | 真实数据 |
| 3 | S/A级线索人工抽检 | 真实数据 |

---

## F. 需要废弃或调整的旧设计

### F.1 废弃项

| 旧设计 | 原因 | 处理 |
|------|------|------|
| `mode=live` 作为"API采集"模式 | 与规则"公开搜索"不一致 | 重命名为 `mode=public`，语义改为"公开数据采集" |
| `DouyinLiveCollector._fetch_video_list_live()` 标注 "TODO: 对接抖音开放平台 API" | API调用不是设计目标 | 改为 `_search_and_discover()` 标注 "公开搜索框结果解析" |
| `platform_credentials.yml` 仅含 `cookie` 字段 | 不符合三模式设计 | 改为三个section: `public`(UA/rate_limit) / `official`(api_key/cookie) / 均为可选 |

### F.2 保留项

| 设计 | 理由 |
|------|------|
| `BaseCollector` / `CommentRecord` | P0 核心抽象，与采集方式无关 |
| `LiveCollectorBase` + `RateLimiter` + `CollectorState` | 速率限制/状态管理适用于公开采集 |
| `TaskManager` + 7状态机 + 增量游标 | 与采集方式无关 |
| `Pipeline` 10步 + `Engine` | P0 固化，不倒推 |
| `platform_adapter.py` 工厂模式 | 模式路由架构正确，只需调整 mode 命名和路由逻辑 |
| Mock 永驻 + 降级兜底 | 规则不要求改变 |

### F.3 命名调整清单

| 旧名称 | 新名称 | 影响文件 |
|------|------|------|
| `CollectorMode.LIVE` | `CollectorMode.PUBLIC` | `platform_adapter.py` |
| — | `CollectorMode.OFFICIAL` | `platform_adapter.py` (新增) |
| `mode="live"` | `mode="public"` | 所有调用方 (保持兼容) |
| `DouyinLiveCollector` | `DouyinPublicCollector` | `douyin_live_collector.py` (重命名) |
| `_fetch_video_list_live()` | `_search_and_discover()` | `douyin_live_collector.py` |
| `_fetch_comments_live()` | `_browse_and_collect()` | `douyin_live_collector.py` |
| `_api_available` | `_public_access_available` | `douyin_live_collector.py` |
| `competitor_accounts.csv` | `competitor_master.csv` | `02_DATA/02_COMPETITOR_DATABASE/` |

> `mode=official` 仅当 public 模式确实不可用（如平台不提供公开搜索）时才启用。PV_OS 默认策略：public优先，official补充。

---

## G. 更新后的降级与容灾

```
                      正常: mode=auto
                           │
                 ┌─────────┼─────────┐
                 ▼                   ▼
         公开访问可用            公开访问不可用
            │                      │
        mode=public             mode=mock
            │                      │
     ┌──────┼──────┐        继续用Mock跑全链路
     ▼      ▼      ▼        (Pipeline不受影响)
   成功   限流   封禁
     │      │      │
   正常   冷却   通知人工
         重试   切Mock
```

**核心保障不变**: Mock 永驻，Pipeline 永远不中断。

---

## H. 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-20 | 初版：Platform Adapter 模式，API采集导向 |
| V2.1 | 2026-07-20 | **架构重设计**：基于规则校准结果，增加竞品发现层，重新定位为 Public Data Collector，修正为七步链路 |
