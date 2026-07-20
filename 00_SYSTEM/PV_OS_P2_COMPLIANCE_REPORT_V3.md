# PV_OS P2 架构合规报告 V3.0

版本：V3.0
日期：2026-07-20
用途：基于 10 个固化规则文件，审计当前代码与 V3.0 架构的差距

> 本次不做代码修改。仅输出合规分析和修改建议。

---

## 一、当前代码符合度总览

| 维度 | 当前 | V3.0 要求 | 符合度 |
|------|:--:|:--:|:--:|
| 两个商业闭环 | 仅 Outbound 80% | Outbound + Inbound | 40% |
| 三层资产 | 账号 ✅ / 视频 ❌ / 评论 🟡 | 全部持久化 + AI分析字段 | 33% |
| 账号分类 | 四级内容分类 | customer_source / content_learning / both + own_account | 30% |
| 内容智能 | 目录骨架 | 爆款拆解 + AI二创 + 内容策略 | 5% |
| 提醒机制 | 无 | 飞书机器人 + contact_journey | 0% |
| 自有账号区分 | 无 | own_account_master + is_own_account | 0% |
| 首次采集窗口 | P0=0(不限) | 7天滑动窗口 | 偏离 |
| 视频发布者数据 | 仅 VideoCandidate 内存 | video_asset_store 持久化 + 完整字段 | 偏离 |
| 评论用户链接 | 无 user_profile_url | user_id + user_url 完整保存 | 偏离 |
| 业务边界 | 关键词过滤 | 完整 | 85% |

---

## 二、偏离规则的位置

### 偏离 1: 只有 Outbound，无 Inbound

**规则**: `PV_OS_GOVERNANCE_RULES.md §八` — "核心验证: 主动获客 + 被动获客"

**当前**: 代码 100% 围绕 Outbound 建设。无 Inbound 任何实现。

**影响文件**: 无（需要新建模块，非修改现有代码）

---

### 偏离 2: 竞品账号未按用途分类

**规则**: `PV_OS_ACCOUNT_MODEL_V3.md` — customer_source / content_learning / both

**当前**: `competitor_master.csv` 有 `account_type`(national_brand/regional_installer/city_case/renovation) 但无 `account_purpose` 和 `learning_priority`。

**需要修改**:
- `competitor_master.csv` 增加 `account_purpose`、`learning_priority` 字段
- `competitor_discovery.py` CompetitorCandidate 增加对应字段

---

### 偏离 3: 视频资产无持久化

**规则**: `PV_OS_DATA_ASSET_ARCHITECTURE_V3.md §三`

**当前**: `VideoCandidate` 仅存在于 `public_search_base.py` 内存中，无持久化存储。无 AI 分析字段 (hook_3_seconds 等)。

**需要新增**:
- `video_asset_store.csv`
- `video_analysis/` 目录

---

### 偏离 4: 评论用户无主页链接

**规则**: `COMMENT_SCHEMA.md §四` — user_id / user_name / user_url

**当前**: `CommentRecord` 有 `author`(昵称) 但无 `user_id`、`user_profile_url`、`comment_like_count`、`reply_count`。

**需要修改**: `collector_base.py CommentRecord`

---

### 偏离 5: 首次采集窗口不正确

**规则**: `PV_OS_COMMENT_COLLECTION_TASK_MODEL.md §8.1` — 首次采集最近7天

**当前**: `task_manager.py:251` — P0 `time_window_days=0`(不限)

**需要修改**: `task_manager.py` 增加 `is_first_collection` 标记

---

### 偏离 6: 无自有账号概念

**规则**: `PV_OS_ACCOUNT_MODEL_V3.md §二`

**当前**: 系统只认识竞品账号。无法区分"这是自己的视频还是竞品的视频"。

**需要新增**: `own_account_master.csv` + `is_own_account` 标记

---

### 偏离 7: 缺失 Task 类型区分

**规则**: discovery_task(发现) vs monitor_task(监控) vs collection_task(采集)

**当前**: `CollectionTask` 无 `task_type` 字段，全部走同一状态机。

**需要修改**: `task_manager.py CollectionTask` 增加 `task_type`

---

## 三、需要修改的文件

### 3.1 必须修改（已有文件）

| 优先级 | 文件 | 修改内容 |
|:--:|------|---------|
| P0 | `collector_base.py` | CommentRecord + user_id / user_profile_url / comment_like_count / reply_count |
| P0 | `task_manager.py` | CollectionTask + task_type / is_first_collection |
| P0 | `task_manager.py:251` | P0 time_window_days=7 (首次) |
| P1 | `competitor_master.csv` | + account_purpose / learning_priority |
| P1 | `competitor_discovery.py` | CompetitorCandidate + account_purpose / learning_priority |
| P1 | `public_search_base.py` | VideoCandidate + author_id / author_name / author_url |

### 3.2 必须新增

| 优先级 | 文件 | 说明 |
|:--:|------|------|
| P1 | `own_account_master.csv` | 自有账号注册 |
| P1 | `video_asset_store.csv` | 视频资产持久化 |
| P2 | `contact_journey.csv` | 触达全流程 |
| P2 | `content_insight.json` | 内容洞察 |
| P2 | `content_calendar.csv` | 发布日历 |
| P2 | `content_performance.csv` | 内容效果 |

---

## 四、新增模块建议

| 模块 | 优先级 | 依赖 | 说明 |
|------|:--:|------|------|
| `ContentIntelligence` | P2 | video_asset_store | 爆款拆解 + AI二创脚本 |
| `AlertEngine` | P2 | own_account + Pipeline | 飞书机器人通知 |
| `OwnAccountManager` | P1 | own_account_master | 自有账号 CRUD + 评论区分 |
| `VideoAssetStore` | P1 | video_asset_store.csv | 视频资产读写 + 查询 |
| `ContactJourney` | P2 | CRM + leads | 触达状态全流程追踪 |

---

## 五、下一阶段开发顺序

### Phase 2A: 资产层固化 (当前可直接启动)

```
1. CommentRecord 字段扩展 (user_id / user_profile_url)
2. VideoCandidate → video_asset_store.csv 持久化
3. TaskManager task_type + is_first_collection
4. P0 time_window_days = 7
```

### Phase 2B: 账号模型升级

```
5. competitor_master + account_purpose / learning_priority
6. own_account_master.csv
7. Pipeline 增加 is_own_account 标记
```

### Phase 2C: Inbound 闭环

```
8. ContentIntelligence (爆款拆解)
9. AI二创脚本生成
10. AlertEngine (飞书通知)
11. contact_journey 触达追踪
```

---

## 六、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V3.0 | 2026-07-20 | 基于 10 规则文件审计，输出 7 个偏离点 + 文件清单 + 开发顺序 |
