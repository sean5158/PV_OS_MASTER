# PV_OS_BUSINESS_FLOW_MODEL V3.0

版本：V3.0
日期：2026-07-20
用途：PV_OS 两个商业闭环的完整流程定义

> 本次不做代码修改。本文为架构设计文件。

---

## 一、PV_OS 定位重申

PV_OS 不是评论采集系统。

PV_OS 是：**AI 驱动的城市家庭光伏主动获客 + 内容智能增长系统。**

必须形成两个完整商业闭环：

| 闭环 | 方向 | 核心问题 |
|------|------|---------|
| **A. 主动找客户 (Outbound)** | 我去找人 | 如何从竞品评论区发现客户？ |
| **B. 客户主动找我 (Inbound)** | 人来找我 | 如何让客户看了我的内容来找我？ |

---

## 二、闭环 A：主动获客 (Outbound)

### 2.1 完整流程

```
Step 1:  关键词词根 (人工选定 2-3 个)
            ↓
Step 2:  AI关键词扩展 (keyword_expander.py)
            ├── 平台联想词
            ├── 区域组合 (四川/重庆/贵州)
            └── 场景组合 (别墅/阳光房/小商业)
            ↓
Step 3:  平台公开搜索 (PublicSearchCollector)
            ├── douyin_public_collector
            ├── xiaohongshu_public_collector (待实现)
            └── kuaishou_public_collector (待实现)
            ↓
Step 4:  发现竞品账号 (CompetitorDiscovery)
            ├── 搜索结果初筛 (7排除规则)
            ├── 六维评分 (业务匹配/家庭光伏/高端场景/区域/评论价值/活跃度)
            └── 写入 competitor_master.csv
            ↓
Step 5:  发现视频 (discover_videos)
            ├── 获取账号作品列表
            ├── 筛选房屋场景匹配视频
            └── 写入 video_asset_store.csv
            ↓
Step 6:  采集评论 (Collector → data_cleaner)
            ├── 按视频采集评论 (首次7天，后续增量)
            ├── 去重/去噪/标准化
            └── 写入 comment_asset_library.csv
            ↓
Step 7:  评论用户分析
            ├── region_engine: 区域判断 (四川/重庆/贵州)
            ├── intent_model: 意图分级 (L0-L3)
            └── comment_analyzer: 客户类型识别
            ↓
Step 8:  Lead评分 (lead_scoring_agent)
            ├── 五维评分 (需求40+区域20+房屋20+时间10+真实10)
            └── S(≥80)/A(60-79)/B(35-59)/C(<35)
            ↓
Step 9:  CRM入库
            ├── S → hot/ (立即触达)
            ├── A → qualified/ (重点跟进)
            ├── B → nurture_pool.csv (长期培育)
            └── C → comment_asset_library.csv (资产保存)
            ↓
Step 10: 人工触达
            ├── 飞书展示: 客户昵称/评论/区域/评分/主页链接
            └── 人工点击链接 → 进入平台 → 私信回复
```

### 2.2 目标客户范围

| 维度 | 范围 |
|------|------|
| **区域** | 四川 (优先成都) / 重庆 / 贵州 |
| **房屋类型** | 别墅 / 叠拼 / 花园洋房 / 阳光房 |
| **客户类型** | 城市家庭光伏 / 小商业 (民宿/酒店/茶楼) |

### 2.3 禁止范围

| 类型 | 处理 |
|------|------|
| 农村光伏 (纯政策型) | 关键词过滤，不进入Lead |
| 大型工商业光伏 | 关键词过滤 |
| 地面电站 | 关键词过滤 |
| 光伏供应链 | 不纳入竞品发现 |

---

## 三、闭环 B：客户主动找我 (Inbound)

### 3.1 完整流程

```
Step 1:  竞品爆款分析 (Content Intelligence)
            ├── 从 video_asset_store.csv 读取竞品视频
            ├── AI分析: 钩子/痛点/结构/标题/评论触发/爆款原因
            └── 输出 content_insight.json
            ↓
Step 2:  二创脚本生成
            ├── 基于爆款结构 + PV_OS 差异化角度
            ├── 输出 AI二创脚本 (04_CONTENT/scripts_ai/)
            └── 人工审核 + 调整
            ↓
Step 3:  内容发布 (自有账号)
            ├── 拍摄/制作视频
            ├── 发布到抖音/小红书
            └── 记录到 content_calendar.csv
            ↓
Step 4:  效果追踪
            ├── 记录 content_performance.csv
            └── 归因: content_to_lead_mapping.csv
            ↓
Step 5:  自有账号评论采集
            ├── 系统区分 own_account vs competitor_account
            ├── 采集自有账号视频评论
            └── 标记 is_own_account=true
            ↓
Step 6:  评论AI分析 (与Outbound共享Pipeline)
            ├── region_engine
            ├── intent_model
            ├── comment_analyzer
            └── lead_scoring_agent
            ↓
Step 7:  Alert Engine 提醒
            ├── 飞书机器人通知
            ├── 展示: 平台/视频/客户昵称/评论/地区/评分/主页链接
            └── 人工点击 → 进入平台 → 回复客户
            ↓
Step 8:  触达跟进
            ├── CRM记录: S/A/B/C
            └── contact_journey: 已联系/已加微信/已成交
```

### 3.2 Inbound 特有组件

| 组件 | 说明 | 状态 |
|------|------|:--:|
| Content Intelligence | 竞品爆款拆解 → 二创方向 | 🆕 |
| own_account_master.csv | 自有账号注册 | 🆕 |
| Alert Engine | 飞书提醒 | 🆕 |
| content_calendar | 发布日历 | 🆕 |
| content_performance | 效果追踪 | 🆕 |

---

## 四、两个闭环的关系

```
                    ┌──────────────────────────┐
                    │   一次平台搜索+采集         │
                    │   (同一批数据)              │
                    └──────────┬───────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
        Outbound 闭环                    Inbound 闭环
        (主动找客户)                     (客户主动找我)
               │                               │
    competitor_master              video_asset_store
         ↓                              ↓
    comment_collector           content_intelligence
         ↓                              ↓
    lead_scoring                AI二创脚本
         ↓                              ↓
    CRM → 人工触达              自有账号发布
                                      ↓
                              自有账号评论采集
                                      ↓
                              Alert Engine → 人工回复
```

**共用组件**:
- Pipeline (region_engine / intent_model / comment_analyzer / lead_scoring)
- CRM (leads_master / nurture_pool)
- comment_asset_library.csv (全量评论资产)
- 数据清洗 (data_cleaner)

**各自独立组件**:
- Outbound: competitor_master / discovery / task scheduling
- Inbound: content_intelligence / own_account / alert_engine

---

## 五、Inbound vs Outbound 状态对比

| 维度 | Outbound | Inbound |
|------|:--:|:--:|
| 数据采集层 | ✅ P0-P2 已实现 | 🔴 未开始 |
| 内容分析层 | — | 🔴 未开始 |
| Pipeline 共享 | ✅ | 🔴 需连接 |
| CRM 共享 | ✅ | 🟡 需增加 alert |
| 飞书提醒 | 🔴 | 🔴 未开始 |
| 账号区分 | 🟡 仅竞品 | 🔴 无自有账号 |

---

## 六、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V3.0 | 2026-07-20 | 首次定义两个完整商业闭环：Outbound 10步 + Inbound 8步 |
