# PV_OS_ALERT_ENGINE_DESIGN V1.0

版本：V1.0
日期：2026-07-20
用途：PV_OS 提醒引擎 — 自有账号评论客户主动咨询的飞书通知机制

> 本次不做代码修改。本文为架构设计文件。
> 依赖：PV_OS_BUSINESS_FLOW_MODEL_V3.md、PV_OS_ACCOUNT_MODEL_V3.md

---

## 一、定位

Alert Engine 是 Inbound 闭环的末端节点。

**触发条件**: 自有账号视频评论被 AI 分析后判定为 S/A 级潜客。

**目标**: 不依赖短信，通过飞书机器人通知运营人员，实现人工快速回复。

---

## 二、通知架构

```
自有账号视频
    ↓
评论采集 (同 Outbound Collector)
    ↓
AI分析 (Pipeline 共享)
    ├── region_engine
    ├── intent_model
    ├── comment_analyzer
    └── lead_scoring_agent
    ↓
判断: is_own_account=true AND lead_grade IN (S, A)
    ↓
Alert Engine
    ↓
飞书机器人 → 运营人员
    ↓
人工点击链接 → 进入平台 → 回复客户
```

---

## 三、通知内容

### 3.1 单条提醒格式

由飞书机器人发送到指定群/个人：

```
🔔 新客户咨询提醒

平台：抖音
视频：别墅光伏安装实拍
客户：成都锦江业主刘先生
评论：我家在成都锦江区别墅，想装一套光伏发电系统，能报个价吗？
地区：四川成都
评分：S级 (92分)
时间：2026-07-20 10:30

📎 客户主页：https://douyin.com/user/xxx
📎 评论链接：https://douyin.com/video/xxx
📎 视频链接：https://douyin.com/video/xxx

⏰ 请在 24 小时内回复
```

### 3.2 字段映射

| 提醒字段 | 数据来源 |
|---------|---------|
| 平台 | `comment.platform` |
| 视频 | `comment.source_video_title` |
| 客户 | `comment.author` |
| 评论 | `comment.content` |
| 地区 | `region_analysis.province + city` |
| 评分 | `lead_scoring.total_score + grade` |
| 客户主页 | `comment.user_profile_url` |
| 评论链接 | `comment.source_url` |
| 视频链接 | `comment.source_url` |

---

## 四、通知策略

### 4.1 分级通知

| 等级 | 通知方式 | 时效要求 |
|:--:|------|:--:|
| **S级** (≥80) | 飞书群 + @负责人 | 24小时内回复 |
| **A级** (60-79) | 飞书群消息 | 48小时内回复 |
| **B级** (35-59) | 不提醒，进入培育池 | — |
| **C级** (<35) | 不提醒，资产保存 | — |

### 4.2 重复提醒抑制

- 同一 `comment_id` 24小时内不重复通知
- 同一 `user_id` 多评论合并为一条通知
- 已标记 `contact_status=已回复` 的不再提醒

---

## 五、数据存储架构

### 5.1 三层架构

```
第一层：数据库 (当前用CSV/JSON)
    ├── account
    ├── video
    ├── comment
    ├── lead
    └── contact_journey

第二层：文件资产库
    ├── 视频分析 (04_CONTENT/analytics/)
    ├── 二创脚本 (04_CONTENT/scripts_ai/)
    └── 爆款拆解 (04_CONTENT/viral_analysis/)

第三层：飞书 (运营层)
    ├── 客户提醒 (Alert Engine)
    ├── 销售跟进 (人工)
    └── 数据看板 (未来)
```

### 5.2 数据流向

```
数据库 ──(AI计算)──→ 文件资产库 ──(人工审核)──→ 飞书运营层
                                                      │
                                              人工点击链接
                                              进入平台回复
```

---

## 六、contact_journey 模型

### 6.1 新增数据模型

```
05_CUSTOMER_CRM/follow_ups/contact_journey.csv
```

| 字段 | 说明 |
|------|------|
| `journey_id` | 旅程ID |
| `lead_id` | 关联线索ID |
| `user_id` | 平台用户ID |
| `status` | pending / contacted / replied / wechat_added / site_visit / deal_closed / no_need |
| `first_contact_at` | 首次触达时间 |
| `last_contact_at` | 最近触达时间 |
| `contact_channel` | 平台私信 / 微信 / 电话 |
| `notes` | 人工备注 |
| `owner` | 负责人 |

### 6.2 状态流转

```
pending (待触达)
    ↓ 人工私信
contacted (已联系)
    ↓ 客户回复
replied (已回复)
    ↓ 加微信
wechat_added (已加微信)
    ↓ 上门勘测
site_visit (已上门)
    ↓ 成交
deal_closed (已成交)
```

---

## 七、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-20 | 首次建立提醒引擎：飞书通知架构、三层存储、contact_journey模型 |
