# Phase 3-1 飞书运营层设计

**版本**: V1.0  
**日期**: 2026-07-20  
**状态**: 设计阶段 — 不执行代码  
**依赖**: PV_OS_V3.2_ARCHITECTURE_LOCK.md、PV_OS_ALERT_ENGINE_DESIGN_V1.md、PV_OS_BUSINESS_FLOW_MODEL_V3.md  

---

## 一、Alert Engine → 飞书通知流程

### 1.1 完整链路

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Inbound 评论采集 → 飞书通知                        │
│                                                                      │
│  Step 1: 自有账号发布视频                                              │
│     own_account_master.csv → platform_account_id                    │
│          ↓                                                           │
│  Step 2: Collector 采集评论                                           │
│     douyin_public_collector.py → CommentRecord                      │
│          ↓                                                           │
│  Step 3: Inbound Comment Detector 检测                               │
│     video_author_id ∈ own_account_ids → is_own_account = True       │
│     InboundDetectionResult(is_inbound=True, type="own_comment")      │
│          ↓                                                           │
│  Step 4: Pipeline 共享分析                                           │
│     region_engine → intent_model → comment_analyzer → lead_scoring  │
│          ↓                                                           │
│  Step 5: Alert Engine 判断                                           │
│     is_inbound=True AND lead_grade IN (S, A) → should_alert()       │
│     is_duplicate(comment_id) → False (24h去重)                       │
│          ↓                                                           │
│  Step 6: 飞书消息卡片生成                                             │
│     FeishuAlertPayload.to_feishu_message()                           │
│          ↓                                                           │
│  Step 7: 飞书机器人 Webhook 发送                                      │
│     feishu_webhook_client.py → HTTP POST                            │
│          ↓                                                           │
│  Step 8: 飞书群消息到达                                               │
│     S级: 卡片 + @负责人                                               │
│     A级: 卡片 + 群消息                                                │
│          ↓                                                           │
│  Step 9: 运营人员操作                                                 │
│     点击链接 → 进入对应平台App → 私信回复客户                           │
│          ↓                                                           │
│  Step 10: ContactJourney 更新                                        │
│     pending → contacted                                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 通知触发条件

| 条件 | 值 | 说明 |
|------|------|------|
| `is_inbound` | `True` | 必须来自自有账号视频 |
| `lead_grade` | `S` 或 `A` | B/C 级不触发通知 |
| `is_duplicate` | `False` | 同一 comment_id 24h 内不重复 |

### 1.3 飞书消息卡片格式（最终锁定）

```json
{
  "msg_type": "interactive",
  "card": {
    "header": {
      "title": {
        "tag": "plain_text",
        "content": "🔔 新客户咨询提醒"
      },
      "template": "red"
    },
    "elements": [
      {
        "tag": "div",
        "fields": [
          {"is_short": true, "text": {"tag": "lark_md", "content": "**平台**\n抖音"}},
          {"is_short": true, "text": {"tag": "lark_md", "content": "**视频**\n别墅光伏安装实拍"}}
        ]
      },
      {
        "tag": "div",
        "fields": [
          {"is_short": true, "text": {"tag": "lark_md", "content": "**客户**\n成都锦江业主刘先生"}},
          {"is_short": true, "text": {"tag": "lark_md", "content": "**地区**\n四川成都"}}
        ]
      },
      {
        "tag": "div",
        "text": {"tag": "lark_md", "content": "**💬 评论内容**\n我家在成都锦江区别墅，想装一套光伏发电系统，能报个价吗？"}
      },
      {
        "tag": "div",
        "fields": [
          {"is_short": true, "text": {"tag": "lark_md", "content": "**评分**: S级 (92分)"}},
          {"is_short": true, "text": {"tag": "lark_md", "content": "**时效**: 24小时内"}}
        ]
      },
      {"tag": "hr"},
      {
        "tag": "div",
        "text": {"tag": "lark_md", "content": "📎 [客户主页](https://douyin.com/user/xxx) ｜ 📎 [评论链接](https://douyin.com/video/xxx) ｜ 📎 [视频链接](https://douyin.com/video/xxx)"}
      },
      {
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": "PV_OS Alert Engine · 2026-07-20 10:30"}]
      }
    ]
  }
}
```

### 1.4 字段映射表（代码 → 飞书卡片）

| 飞书卡片字段 | 代码来源 | 数据类型 |
|------|------|------|
| 平台 | `CommentRecord.platform` | string |
| 视频 | `CommentRecord.source_video_title` | string |
| 客户 | `CommentRecord.author` | string |
| 评论 | `CommentRecord.content`（截断 200 字） | string |
| 地区 | `region_engine 输出 province + city` | string |
| 评分 | `lead_scoring_agent.total_score + grade` | string |
| 时效 | `AlertEngine.get_response_deadline(grade)` | string |
| 客户主页 | `CommentRecord.user_profile_url` | URL |
| 评论链接 | `CommentRecord.source_url` | URL |
| 视频链接 | `CommentRecord.source_url` | URL |

---

## 二、飞书多维表设计

### 2.1 定位

飞书多维表 = 人工运营工作台。

**数据库（CSV/SQLite）** 负责 AI 计算与资产持久化。  
**飞书多维表** 负责人工查看、状态更新、销售跟进。

两者通过 `lead_id` 关联，方向为 **数据库 → 飞书（单向同步）**。

### 2.2 多维表字段

| # | 字段名 | 类型 | 来源 | 说明 |
|:--:|------|------|------|------|
| 1 | `lead_id` | 文本 | `leads_master.lead_id` | 唯一标识，关联数据库 |
| 2 | `platform` | 单选 | `CommentRecord.platform` | 抖音/小红书/快手/视频号 |
| 3 | `account_name` | 文本 | `own_account_master.account_name` | 哪个自有账号的评论区 |
| 4 | `customer_name` | 文本 | `CommentRecord.author` | 客户昵称 |
| 5 | `user_id` | 文本 | `CommentRecord.user_id` | 平台用户ID |
| 6 | `user_profile_url` | 链接 | `CommentRecord.user_profile_url` | 🔗 点击跳转客户主页 |
| 7 | `video_url` | 链接 | `CommentRecord.source_url` | 🔗 点击跳转原视频 |
| 8 | `comment_url` | 链接 | `CommentRecord.source_url` | 🔗 点击跳转评论 |
| 9 | `comment_text` | 文本 | `CommentRecord.content`（截断 200 字） | 评论原文 |
| 10 | `region` | 文本 | `region_engine 输出` | 四川成都/重庆/贵州贵阳 |
| 11 | `intent_score` | 数字 | `intent_model 输出` | 0-100 |
| 12 | `lead_grade` | 单选 | `lead_scoring_agent.grade` | S / A |
| 13 | `status` | 单选 | `contact_journey.status` | pending→contacted→replied→wechat_added→site_visit→deal_closed |
| 14 | `alert_time` | 日期 | `alert_log.created_at` | 通知发送时间 |
| 15 | `owner` | 人员 | `contact_journey.owner` | 负责人 |
| 16 | `notes` | 文本 | `contact_journey.notes` | 人工备注 |

### 2.3 视图设计

| 视图 | 筛选条件 | 用途 |
|------|------|------|
| **待触达** | `status = pending` | 运营人员每日优先处理 |
| **跟进中** | `status IN (contacted, replied)` | 正在沟通的客户 |
| **已加微信** | `status = wechat_added` | 进入私域 |
| **本周新增** | `alert_time ≥ 本周一` | 周报统计 |
| **S级客户** | `lead_grade = S` | 高优先级单独视图 |
| **全部** | 无筛选 | 完整数据 |

### 2.4 同步策略

| 维度 | 策略 |
|------|------|
| 方向 | 数据库 → 飞书（单向） |
| 触发 | Alert Engine 生成 Alert 时同步 |
| 更新 | `contact_journey.status` 变更时更新飞书行 |
| 频率 | 实时（每次 Alert 触发即同步） |
| 去重 | 按 `lead_id` 去重（同一 lead_id 只保留最新行） |

---

## 三、客户跟进状态

### 3.1 状态机（锁定，不可改变）

```
                     ┌──────────┐
                     │ pending  │  待触达（初始状态）
                     └────┬─────┘
                          │ 人工在平台私信客户
                          ▼
                     ┌──────────┐
                     │contacted │  已联系
                     └────┬─────┘
                          │ 客户回复
                          ▼
                     ┌──────────┐
                     │ replied  │  已回复
                     └────┬─────┘
                          │ 加微信
                          ▼
                  ┌──────────────┐
                  │wechat_added  │  已加微信（进入私域）
                  └──────┬───────┘
                         │ 预约上门勘测
                         ▼
                  ┌──────────────┐
                  │ site_visit   │  已上门勘测
                  └──────┬───────┘
                         │ 签订合同
                         ▼
                  ┌──────────────┐
                  │ deal_closed  │  已成交 🎉
                  └──────────────┘

  任意阶段 ──────→  no_need   客户不需要/无法联系
```

### 3.2 状态转换规则

| 当前状态 | 允许转换到 | 操作者 |
|------|------|:--:|
| `pending` | `contacted`, `no_need` | 人工 |
| `contacted` | `replied`, `no_need` | 人工 |
| `replied` | `wechat_added`, `no_need` | 人工 |
| `wechat_added` | `site_visit`, `no_need` | 人工 |
| `site_visit` | `deal_closed`, `no_need` | 人工 |
| `deal_closed` | —（终态） | — |
| `no_need` | —（终态） | — |

**禁止倒退**: 不允许 `contacted → pending`、`replied → contacted` 等。

### 3.3 状态记录时机

| 操作 | 记录内容 | 触发 |
|------|------|------|
| 发送私信 | `status=contacted`, `first_contact_at=now`, `contact_channel=平台私信` | 人工在飞书标记 |
| 客户回复 | `status=replied`, `last_contact_at=now` | 人工在飞书标记 |
| 加微信 | `status=wechat_added`, `contact_channel=微信` | 人工在飞书标记 |
| 预约上门 | `status=site_visit` | 人工在飞书标记 |
| 成交 | `status=deal_closed` | 人工在飞书标记 |
| 放弃 | `status=no_need`, `notes=原因` | 人工在飞书标记 |

---

## 四、链接跳转方案

### 4.1 保存三个链接

系统在采集和分析阶段保存三个链接到 `CommentRecord` 和 `leads_master.csv`：

| 链接 | 字段 | 说明 |
|------|------|------|
| 客户主页 | `user_profile_url` | `https://douyin.com/user/{user_id}` |
| 视频链接 | `source_url`（视频部分） | `https://douyin.com/video/{video_id}` |
| 评论链接 | `source_url` | `https://douyin.com/video/{video_id}?comment_id={comment_id}` |

### 4.2 飞书点击跳转流程

```
┌──────────────────────────────────────────────┐
│              飞书消息卡片                      │
│                                              │
│  📎 [客户主页](douyin://user/xxx)             │
│  📎 [评论链接](douyin://video/xxx)            │
│  📎 [视频链接](douyin://video/xxx)            │
│                                              │
│  运营人员 点击链接                             │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  桌面端: 浏览器打开抖音网页版                   │
│  移动端: 唤醒抖音App (Universal Link)          │
│                                              │
│  douyin://  →  抖音App                        │
│  xhsdiscover://  →  小红书App                 │
│  kwai://  →  快手App                          │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│  进入对应页面后:                               │
│  1. 查看客户主页 → 判断是否真实客户             │
│  2. 查看原视频 → 了解上下文                    │
│  3. 查看原评论 → 私信回复客户                   │
│                                              │
│  人工回复内容参考:                              │
│  "您好，看到您对光伏感兴趣，我们是成都本地       │
│   安装团队，可以免费上门勘测，方便聊聊吗？"       │
└──────────────────────────────────────────────┘
```

### 4.3 各平台 URL Scheme

| 平台 | Universal Link | Web URL |
|------|------|------|
| 抖音 | `douyin://` | `https://www.douyin.com/` |
| 小红书 | `xhsdiscover://` | `https://www.xiaohongshu.com/` |
| 快手 | `kwai://` | `https://www.kuaishou.com/` |
| 视频号 | `weixin://` | `https://channels.weixin.qq.com/` |

> 飞书卡片中的链接默认使用 Web URL（兼容桌面端和移动端）。  
> 移动端飞书会自动尝试唤醒对应 App。

### 4.4 系统边界（重要）

| 系统负责 | 人工负责 |
|------|------|
| ✅ 保存 `user_profile_url` | 点击链接进入平台 |
| ✅ 保存 `source_url`（视频/评论） | 查看客户主页判断真实性 |
| ✅ 在飞书卡片中渲染可点击链接 | 撰写私信内容 |
| ✅ 提供客户评论原文和 AI 分析结果 | 决定是否联系及如何联系 |
| ❌ 不自动发送私信 | 完成私信沟通 |
| ❌ 不代替人工做联系决策 | 完成后续跟进 |

---

## 五、飞书与 CRM 同步关系

### 5.1 架构定位

```
┌─────────────────────────────────────────────────────────────┐
│                      第一层: 数据库                           │
│                      CSV/SQLite                              │
│                                                             │
│  职责: AI计算 + 数据持久化 + 资产保存                           │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │ leads_master.csv    │  │ contact_journey.csv  │           │
│  │ (19 fields)         │  │ (16 fields)          │           │
│  └─────────┬───────────┘  └──────────┬──────────┘           │
│            │                         │                      │
│  ┌─────────┴───────────┐  ┌──────────┴──────────┐           │
│  │ comment_asset_      │  │ alert_log.csv        │           │
│  │ library.csv         │  │ (18 fields)          │           │
│  └─────────────────────┘  └─────────────────────┘           │
└────────────────────────────┬────────────────────────────────┘
                             │ 单向同步（Alert触发时）
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    第二层: 飞书运营层                           │
│                                                             │
│  职责: 人工运营 + 销售跟进 + 数据查看                            │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐           │
│  │ 飞书消息卡片          │  │ 飞书多维表            │           │
│  │ (Alert通知)          │  │ (Lead看板)           │           │
│  │ S级: @负责人          │  │ 16个字段             │           │
│  │ A级: 群消息           │  │ 6个视图              │           │
│  └─────────────────────┘  └─────────────────────┘           │
│                                                             │
│  人工操作:                                                    │
│  - 点击链接 → 进入平台 → 私信回复                               │
│  - 更新 status → contacted/replied/wechat_added/...          │
│  - 填写 notes                                                │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 同步规则

| 规则 | 说明 |
|------|------|
| **方向** | 数据库 → 飞书（单向）。飞书不写回数据库（Phase 3-1） |
| **触发** | Alert Engine 生成 Alert 时同步创建飞书多维表行 |
| **更新** | 人工在飞书更新 status 后，通过 `feishu_webhook_client` 回调更新数据库 `contact_journey` |
| **冲突** | 数据库为准。飞书为展示层 |
| **去重** | 按 `lead_id` 去重 |

### 5.3 数据职责分离

| 数据 | 数据库负责 | 飞书负责 |
|------|:--:|:--:|
| AI 评分 | ✅ 计算并存储 | 展示 |
| Lead 分级 | ✅ S/A/B/C | 展示 + 筛选 |
| 评论原文 | ✅ 全量保存 | 展示（截断200字） |
| 客户链接 | ✅ 保存 | 渲染可点击链接 |
| 触达状态 | ✅ 持久化 | 人工更新 |
| 跟进备注 | ✅ 持久化 | 人工填写 |
| 转化漏斗 | ✅ 计算 | 可视化（飞书图表） |

### 5.4 同步技术方案

```
Alert Engine 触发:
    │
    ├── 1. 写入 alert_log.csv (数据库)
    ├── 2. 创建 contact_journey.csv 行 (数据库)
    ├── 3. 更新 leads_master.csv (is_inbound=True, journey_id=xxx)
    ├── 4. POST 飞书消息卡片 (飞书机器人)
    └── 5. POST 飞书多维表新增行 (飞书API)

人工更新 status:
    │
    飞书多维表 status 变更
        ↓
    飞书 Webhook 回调 → PV_OS
        ↓
    contact_journey.csv 更新 status + notes
```

---

## 六、多平台扩展设计

### 6.1 平台统一抽象

所有平台（抖音/小红书/快手/视频号）共享同一套飞书运营模型：

| 组件 | 平台差异 | 统一层 |
|------|------|------|
| 消息卡片格式 | 无差异 | `FeishuAlertPayload` 统一 |
| 多维表字段 | `platform` 字段区分 | 同一张多维表 |
| 链接跳转 | URL Scheme 不同 | 字段存储完整 URL |
| 跟进状态 | 完全一致 | `contact_journey` 7 状态统一 |
| AI 分析 | 完全一致 | Pipeline 共享 |

### 6.2 平台识别

在飞书多维表视图中按 `platform` 筛选：

| 视图 | 筛选条件 |
|------|------|
| 抖音客户 | `platform = 抖音` |
| 小红书客户 | `platform = 小红书` |
| 快手客户 | `platform = 快手` |
| 视频号客户 | `platform = 视频号` |

### 6.3 扩展顺序

| 阶段 | 平台 | Collector 就绪？ | 飞书就绪？ |
|:--:|------|:--:|:--:|
| Phase 3-1 | 抖音 | ✅ Mock（P2） | 🆕 本次设计 |
| Phase 3-2 | 抖音 | 🆕 Public 真实化 | ✅ |
| Phase 4 | 小红书 | ❌ | ✅ |
| Phase 4 | 快手 | ❌ | ✅ |
| Phase 4 | 视频号 | ❌ | ✅ |

---

## 七、实现清单（Phase 3-1 编码阶段）

### 7.1 新增文件

| # | 文件 | 用途 |
|:--:|------|------|
| 1 | `08_SYSTEM/scripts/feishu_webhook_client.py` | 飞书 Webhook 消息发送 |
| 2 | `08_SYSTEM/scripts/feishu_bitable_client.py` | 飞书多维表 API 同步 |

### 7.2 修改文件

| # | 文件 | 修改内容 |
|:--:|------|------|
| 1 | `alert_engine.py` | `process_inbound_lead()` 增加飞书发送回调 |
| 2 | `leads_master.csv` | Phase 3-0 已完成（is_inbound 等字段） |

### 7.3 配置项

| # | 配置 | 说明 |
|:--:|------|------|
| 1 | `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook 地址 |
| 2 | `FEISHU_APP_ID` | 飞书应用 ID（多维表 API） |
| 3 | `FEISHU_APP_SECRET` | 飞书应用密钥 |
| 4 | `FEISHU_BITABLE_ID` | 多维表 ID |
| 5 | `FEISHU_TABLE_ID` | 多维表子表 ID |
| 6 | `ALERT_OWNER_OPEN_ID` | S级 @负责人 open_id |

### 7.4 测试清单

| # | 测试 | 预期 |
|:--:|------|------|
| 1 | Mock Alert → 飞书消息卡片生成 | 卡片 JSON 正确 |
| 2 | 飞书 Webhook POST | HTTP 200 |
| 3 | 消息卡片在飞书端渲染 | 格式正确，链接可点击 |
| 4 | S级 @负责人 | @mention 生效 |
| 5 | A级群消息 | 卡片发送到群 |
| 6 | 重复抑制 | 同一 comment_id 24h 仅一条 |
| 7 | 多维表行创建 | 新 Alert 自动创建行 |
| 8 | status 更新 → 回调 | contact_journey 更新 |
| 9 | B/C 级不触发通知 | Alert 为 None |
| 10 | 多平台链接跳转 | URL Scheme 正确 |

---

## 八、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-20 | Phase 3-1 飞书运营层完整设计：通知流程、多维表、跟进状态、链接跳转、CRM同步、多平台扩展 |
