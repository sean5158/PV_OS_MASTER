# PV_OS V3.2 Architecture Lock

**版本**: V3.2  
**日期**: 2026-07-20  
**状态**: 架构锁定 — Phase 3 入口  
**前序版本**: V3.1 (Phase 2C 完成冻结)  
**测试基线**: 602/602 全部通过  

> **本文档是 PV_OS 架构的最终锁定版本。**
> Phase 3 所有开发、修改、新增必须以本文档为唯一权威参考。
> 如与任何旧版文档冲突，以本文档为准。
> 旧版设计文档不再作为开发依据，仅保留为设计历史。

---

## 一、四川/重庆/贵州城市级区域模型（锁定）

### 1.1 目标区域层级

```
PV_OS 目标市场
├── 一级: 四川（优先成都）
│   ├── 成都核心区: 武侯、双流、郫都、温江、龙泉驿、锦江、青羊、金牛、成华、高新
│   ├── 成都近郊: 新都、青白江、都江堰、彭州、崇州、邛崃、大邑、蒲江、新津
│   └── 四川地级市: 绵阳、德阳、宜宾、泸州、南充、乐山、达州、资阳、自贡、内江、遂宁、广元、雅安、巴中、眉山、广安、攀枝花、凉山(西昌)
│
├── 二级: 重庆
│   ├── 主城核心: 渝中、江北、南岸、沙坪坝、九龙坡、大渡口、渝北、巴南、北碚
│   └── 区县: 万州、涪陵、江津、合川、永川、长寿、綦江、璧山、铜梁、潼南、荣昌
│
└── 三级: 贵州
    ├── 贵阳核心: 南明、云岩、花溪、乌当、白云、观山湖
    ├── 贵阳近郊: 清镇、修文、息烽、开阳
    └── 贵州地级市: 遵义、毕节、安顺、六盘水、铜仁、黔南(都匀)、黔东南(凯里)、黔西南(兴义)
```

### 1.2 城市价值分级（用于区域评分 20 分制）

| 分值 | 条件 | 示例 |
|:--:|------|------|
| **20** | 成都核心区 + 重庆主城核心区明确 | 武侯区、渝北区 |
| **18** | 成都明确 / 重庆核心区域 / 贵阳核心区 | 成都、江北区、云岩区 |
| **16** | 四川其他城市 / 重庆区县 / 贵州地级市明确 | 绵阳、万州、遵义 |
| **15** | 省份明确（川/渝/黔）但无城市 | 四川、重庆、贵州 |
| **10** | 模糊区域表达 | "西南地区"、"我们这边" |

### 1.3 区域词库（强制正则匹配）

```
四川信号:
  省级: 四川|川|川A~川Z|蜀
  成都核心: 武侯|双流|郫都|温江|龙泉驿|锦江|青羊|金牛|成华|高新|天府
  地级市: 绵阳|德阳|宜宾|泸州|南充|乐山|达州|资阳|自贡|内江|遂宁|广元|雅安|巴中|眉山|广安|攀枝花|西昌

重庆信号:
  省级: 重庆|渝|渝A~渝H
  核心: 渝中|江北|南岸|沙坪坝|九龙坡|大渡口|渝北|巴南|北碚
  区县: 万州|涪陵|江津|合川|永川|长寿|綦江|璧山|铜梁|潼南|荣昌

贵州信号:
  省级: 贵州|黔|贵A~贵J
  核心: 南明|云岩|花溪|乌当|白云|观山湖
  地级市: 遵义|毕节|安顺|六盘水|铜仁|都匀|凯里|兴义
```

---

## 二、IP_location + comment_text 分层判断（锁定）

### 2.1 双信号模型

来自 `PV_OS_REGION_DETECTION_RULES.md §二`：

| 优先级 | 信号来源 | 字段 | 数据性质 |
|:--:|------|------|------|
| **一级** | IP 属地 | `CommentRecord.ip_location` | 平台公开用户地域信息 |
| **二级** | 评论文本 | `CommentRecord.content` | AI 自然语言区域识别 |

### 2.2 分层判断矩阵

| IP 属地 | 评论文本 | 置信度 | 处理 |
|------|------|:--:|------|
| 川/渝/黔明确 | 川/渝/黔明确 | **HIGH** | 直接进入 Lead 评分 |
| 川/渝/黔明确 | 无区域表达 | **HIGH** | 信任 IP，进入评分 |
| 非川/渝/黔 | 川/渝/黔明确 | **MEDIUM** | 用户可能在询问家乡安装 |
| 无 IP 数据 | 川/渝/黔明确 | **MEDIUM** | 信任文本，进入评分 |
| 川/渝/黔模糊 | 川/渝/黔模糊 | **LOW** | 降低区域分值 |
| 非川/渝/黔 | 无区域表达 | **EXCLUDE** | 非目标客户 |

### 2.3 强制禁止

| 禁止行为 | 原因 |
|------|------|
| ❌ 仅用 IP 判断区域 | 用户可能在异地询问家乡安装 |
| ❌ 仅用评论文本判断区域 | 文本可能不包含地名 |
| ❌ 因无城市名丢弃客户 | 省级匹配已足够进入分析 |
| ❌ 因 IP 不在目标省丢弃客户 | 可能出差/旅游中评论 |
| ❌ 忽略四川/重庆/贵州下属城市和区县 | 完整城市列表见 §一 |

---

## 三、Competitor Knowledge Asset（锁定）

### 3.1 定位

`competitor_master.csv` 不是简单的账号列表。它是 **Competitor Knowledge Asset** — 竞品知识资产。

每一个入库账号都是一份长期资产，包含：
- 账号身份（谁）
- 商业价值（价值几何）
- 发现路径（怎么找到的）
- 学习价值（能学到什么）

### 3.2 完整字段（24 字段，已实现 ✅）

```
competitor_id          # 内部唯一ID
platform               # douyin/xiaohongshu/kuaishou/shipinhao
account_id             # 平台账号ID
account_name           # 昵称
account_url            # 主页链接
account_type           # national_brand/regional_installer/city_case/renovation
account_purpose        # 🆕 customer_source/content_learning/both
learning_priority      # 🆕 1-10 (content_learning/both 时有效)
bio                    # 简介
grade                  # S/A/B
total_score            # 六维评分总分
discovery_keyword      # 发现关键词
discovery_date         # 首次发现日期
follower_count         # 粉丝数
ip_location            # IP属地
region                 # 账号所在地
monitor_level          # S/A/B
monitor_frequency      # 6h/daily/3d/weekly
status                 # active/paused/deprecated
score_business_match   # 业务匹配分
score_home_pv          # 家庭光伏分
score_premium_scene    # 高端场景分
score_region           # 区域分
score_comment_value    # 评论价值分
score_activity         # 活跃度分
```

### 3.3 account_purpose 入库判定（不可改变）

```
新账号入库
│
├── 川渝黔本地安装商/案例号？
│   → account_purpose = customer_source
│   → 全量评论采集，6h/daily 频率
│
├── 全国品牌，川渝黔客户密度高？
│   → account_purpose = customer_source
│   → IP属地过滤采集
│
├── 四川以外优秀同行，内容质量高？
│   → account_purpose = content_learning
│   → 仅采集视频资产，不采集全量评论
│   → learning_priority = 7-10
│
├── 本地同行，内容有参考价值？
│   → account_purpose = both
│   → 评论采集 + 内容分析
│   → learning_priority = 3-6
│
└── 纯资讯号/供应商号/无关内容？
    → 不入库
```

### 3.4 采集策略矩阵

| account_purpose | 评论采集 | 视频采集 | 内容分析 | 频率 |
|:---|:--:|:--:|:--:|:--:|
| `customer_source` | ✅ 全量 | ✅ | — | 6h/daily |
| `content_learning` | — | ✅ 全量 | ✅ 九维拆解 | weekly |
| `both` | ✅ 全量 | ✅ 全量 | ✅ | daily |

---

## 四、一次采集多次复用完整定义（锁定）

### 4.1 核心原则

**一次平台公开搜索/采集 → 形成四层长期资产 → 多重业务消费。**

不是"采集评论 → 分析一次 → 丢弃"。每条数据都是长期资产。

### 4.2 四层资产消费矩阵

```
                       ┌─────────────────────────────────────────────────────┐
                       │               一次平台公开搜索/采集                    │
                       └───────────────────────┬─────────────────────────────┘
                                               │
        ┌──────────────────────────────────────┼──────────────────────────────────────┐
        ▼                                      ▼                                      ▼
┌───────────────────┐              ┌───────────────────┐              ┌───────────────────┐
│  Account Asset    │              │  Video Asset      │              │  Comment Asset    │
│  competitor_      │              │  video_asset_     │              │  comment_asset_   │
│  master.csv       │              │  store.csv        │              │  library.csv      │
│  (24 fields)      │              │  (31 fields)      │              │  (20+ fields)     │
└───────┬───────────┘              └───────┬───────────┘              └───────┬───────────┘
        │                                  │                                      │
        ▼                                  ▼                                      ▼
┌───────────────┐              ┌───────────────────┐              ┌───────────────┐
│ 消费1: 客户发现│              │ 消费1: 评论采集源    │              │ 消费1: Lead评分│
│ 消费2: 竞品监控│              │ 消费2: 爆款拆解      │              │ 消费2: CRM入库 │
│ 消费3: 市场分析│              │ 消费3: 二创脚本      │              │ 消费3: 用户画像│
│ 消费4: 账号分级│              │ 消费4: 内容策略      │              │ 消费4: 区域分析│
└───────────────┘              │ 消费5: 标题公式      │              └───────────────┘
                               │ 消费6: 钩子模板      │
                               └───────────────────┘
                                        │
                                        ▼
                               ┌───────────────────┐
                               │ Content Intel     │
                               │ Asset             │
                               │ viral_analysis/   │
                               │ scripts_ai/       │
                               │ content_insight   │
                               └───────────────────┘
                                        │
                                        ▼
                               自有账号内容发布
                                       │
                                content_performance
                                content_to_lead_mapping
```

### 4.3 消费详细定义

#### Account Asset 消费

| 消费 | 输入 | 输出 | 模块 |
|------|------|------|------|
| 客户发现 | competitor_master (customer_source) | CommentRecord → Lead | Collector → Pipeline |
| 竞品监控 | competitor_master (全部 active) | 新增视频/评论变化 | Scheduler → TaskManager |
| 市场分析 | competitor_master (全量) | 区域分布/平台分布/内容趋势 | 人工分析 |
| 账号分级 | competitor_master (全量) | account_purpose/learning_priority 重评估 | competitor_discovery.py |

#### Video Asset 消费

| 消费 | 输入 | 输出 | 模块 |
|------|------|------|------|
| 评论采集源 | video_asset_store (有评论的视频) | CommentRecord | Collector |
| 爆款拆解 | video_asset_store (高互动视频) | VideoAnalysisResult (9维) | content_intelligence_agent |
| 二创脚本 | VideoAnalysisResult → 拆解模板 | AI二创脚本 .md | content_intelligence_agent |
| 内容策略 | video_asset_store (全量) | content_insight.json | content_intelligence_agent |
| 标题公式 | 爆款视频 title_pattern | 可复用标题模板 | ReusableElements |
| 钩子模板 | 爆款视频 hook_3_seconds | 可复用钩子公式 | ReusableElements |

#### Comment Asset 消费

| 消费 | 输入 | 输出 | 模块 |
|------|------|------|------|
| Lead评分 | CommentRecord → Pipeline | S/A/B/C + CRM路由 | lead_scoring_agent |
| CRM入库 | Lead评分结果 | leads_master.csv | CRM |
| 用户画像 | 全量评论 user_id 聚合 | 用户行为特征 | 未来 |
| 区域分析 | ip_location + content | 区域置信度 + region_score | region_engine |

### 4.4 资产更新策略

| 资产 | 新增 | 更新 | 永不删除 |
|------|:--:|:--:|:--:|
| Account Asset | 发现新账号 | 评分/状态/频率 | ✅ 标记 deprecated |
| Video Asset | 发现新视频 | AI分析字段填充 | ✅ |
| Comment Asset | 采集新评论 | intent_score/region_tag/lead_grade | ✅ |
| Content Intel | 新分析结果 | 重新分析 | ✅ 版本管理 |

---

## 五、Public Collector 唯一合法路线（锁定）

### 5.1 七步链路

```
Step 1: 关键词词根
    人工选定 2-3 个词根 (如: 光伏安装、别墅光伏)
        ↓
Step 2: AI关键词扩展
    keyword_expander.py
    平台联想词 + 区域组合 + 场景组合
        ↓
Step 3: 平台公开搜索
    public_search_base.py → search_by_keywords()
    mode=public → 公开搜索框输入关键词 → 获取搜索结果页
        ↓
Step 4: 竞品账号发现
    competitor_discovery.py
    搜索结果解析 → 7种初筛排除 → 六维评分 → competitor_master.csv
        ↓
Step 5: 视频发现
    douyin_public_collector.py → discover_videos()
    获取账号作品列表 → 筛选房屋场景匹配视频 → video_asset_store.csv
        ↓
Step 6: 评论采集
    collector_base.py → collect_comments()
    按视频采集评论 (首次7天 → 后续增量) → data_cleaner → comment_asset_library.csv
        ↓
Step 7: AI分析 + CRM
    Pipeline: region_engine → intent_model → comment_analyzer → lead_scoring → CRM
```

### 5.2 强制禁止清单

| # | 禁止项 | 替代方案 |
|:--:|------|------|
| 1 | ❌ 竞品账号 API 采集 | ✅ 公开搜索发现 |
| 2 | ❌ 直接爬取登录后数据 | ✅ 公开页面解析 |
| 3 | ❌ competitor_accounts.csv 作为主数据源 | ✅ AI发现 → competitor_master.csv |
| 4 | ❌ 绕过关键词发现直接采集 | ✅ 必须是关键词→搜索→发现→采集 |
| 5 | ❌ mode=live 作为"API采集" | ✅ mode=public 语义为"公开数据采集" |
| 6 | ❌ 绕过 data_cleaner 直入 Pipeline | ✅ 所有数据必经 data_cleaner |

### 5.3 三模式强制定义

| mode | 语义 | 数据源 | 实现文件 | 降级 |
|------|------|------|------|------|
| `mock` | 模拟数据 | 硬编码示例 | `MockPageFetcher` | 终极兜底（永不中断） |
| `public` | 公开页面解析 | 公开搜索页HTML | `DouyinPageParser` + `page_fetcher.py` | 失败→mock |
| `official` | 平台官方API/SDK | 平台开放平台 | 待实现 | 失败→public→mock |

### 5.4 降级链

```
mode=auto
    │
    ├── public 可用 → public
    │       ├── 成功 → 正常
    │       ├── 限流 → 冷却重试
    │       └── 封禁 → 通知人工 + 切 mock
    │
    └── public 不可用 → mock
            └── Pipeline 不受影响，继续运行
```

---

## 六、自有账号 Inbound 判断（锁定）

### 6.1 判断链路

```
CommentRecord 进入系统
    │
    ├── video_author_id 在 own_account_master.csv 中？
    │   → is_own_account = True
    │
    ├── source_url 匹配 own_account_master.csv 中的 account_url？
    │   → is_own_account = True
    │
    └── 以上都不匹配
        → is_own_account = False
            │
            ▼
        Outbound Pipeline (主动获客)
```

### 6.2 自有账号注册表

`02_DATA/02_COMPETITOR_DATABASE/own_account_master.csv`

| 字段 | 说明 |
|------|------|
| `account_id` | 内部ID |
| `platform` | douyin/xiaohongshu |
| `platform_account_id` | 平台账号唯一ID |
| `account_name` | 昵称 |
| `account_url` | 主页链接 |
| `monitor_comments` | 是否监控该账号评论 |
| `content_frequency` | 发布频率 |
| `primary_topic` | 主要内容方向 |
| `region` | 账号IP属性 (默认"四川") |
| `status` | active/paused/deprecated |

### 6.3 判断执行顺序

```
Collector 采集评论
    ↓
InboundCommentDetector.mark_own_accounts(records)
    ↓ 遍历所有 CommentRecord
    ├── video_author_id ∈ own_account_ids → record.is_own_account = True
    └── 否则 → record.is_own_account = False
    ↓
InboundCommentDetector.detect(record)
    ├── is_own_account=True → InboundDetectionResult(is_inbound=True, type="own_comment")
    └── is_own_account=False → InboundDetectionResult(is_inbound=False, type="competitor_comment")
    ↓
Pipeline 分流
    ├── is_inbound=True → Alert Engine (飞书提醒) + ContactJourney
    └── is_inbound=False → CRM leads_master (主动触达)
```

### 6.4 Inbound 提醒链

```
Inbound 评论 (is_own_account=True)
    ↓
Pipeline 分析 (region → intent → analyzer → lead_scoring)
    ↓ grade=S/A
AlertEngine.should_alert("S", is_inbound=True) → True
    ↓
AlertEngine.process_inbound_lead() → 去重检查
    ↓ 非重复
Alert 生成 + FeishuAlertPayload.to_feishu_message()
    ↓
飞书机器人 → 群消息 + @负责人
    ↓
运营人员点击链接 → 进入平台 → 人工私信回复
    ↓
ContactJourney: pending → contacted → ...
```

---

## 七、数据库 + 飞书双层存储架构（锁定）

### 7.1 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        第一层: 数据库                             │
│                        当前: CSV/JSON                            │
│                        未来: SQLite (>10K rows)                  │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Account Layer    │  │ Video Layer      │  │ Comment Layer │ │
│  │ competitor_      │  │ video_asset_     │  │ comment_asset_│ │
│  │ master.csv       │  │ store.csv        │  │ library.csv   │ │
│  │ own_account_     │  │ (9 AI分析维度)    │  │ (20+ fields)  │ │
│  │ master.csv       │  │                  │  │               │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Lead Layer       │  │ Journey Layer    │  │ Alert Layer   │ │
│  │ leads_master.csv │  │ contact_journey  │  │ alert_log.csv │ │
│  │ nurture_pool.csv │  │ .csv             │  │               │ │
│  │ hot/ qualified/  │  │ (7 states)       │  │               │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │ AI计算
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     第二层: 文件资产库                             │
│                                                                 │
│  04_CONTENT/                                                     │
│  ├── analytics/content_insight.json    # 选题发现               │
│  ├── analytics/content_performance.csv  # 内容效果              │
│  ├── analytics/content_to_lead_mapping.csv # 归因               │
│  ├── scripts_ai/*.md                   # AI二创脚本             │
│  ├── viral_analysis/*.json             # 爆款拆解               │
│  └── calendar/content_calendar.csv     # 发布日历               │
│                                                                 │
│  06_CASE_LIBRARY/                                                │
│  └── *.md                              # 成交案例               │
└────────────────────────────┬────────────────────────────────────┘
                             │ 人工审核
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     第三层: 飞书运营层                             │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ Alert Engine     │  │ 飞书多维表格      │                    │
│  │ 飞书机器人 → 群   │  │ Lead 看板         │                    │
│  │ S级 @负责人       │  │ 销售跟进状态      │                    │
│  │ A级 群消息        │  │ 转化漏斗          │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                 │
│  运营人员点击链接 → 进入平台 → 人工私信回复客户                     │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 数据流向规则（不可逆）

```
数据库 ──(AI计算)──→ 文件资产库 ──(人工审核)──→ 飞书运营层
                                    │
                            人工点击链接
                            进入平台回复客户
```

- 系统**永远不代替人工**发送私信
- 系统只提供: 客户信息 + 链接跳转
- 人工完成: 私信沟通、加微信、上门勘测、成交

### 7.3 各层职责

| 层 | 职责 | 谁操作 | 数据类型 |
|------|------|:--:|------|
| 数据库 | AI计算、数据持久化、查询分析 | 系统自动 | 结构化数据 (CSV/SQLite) |
| 文件资产库 | AI分析结果、脚本、策略文档 | 系统生成 + 人工审核 | 半结构化 (JSON/Markdown) |
| 飞书运营层 | 客户提醒、销售跟进、数据看板 | 人工 | 消息卡片 + 多维表格 |

### 7.4 迁移触发条件

| 条件 | 动作 |
|------|------|
| `comment_asset_library.csv` > 10,000 行 | CSV → SQLite 迁移 |
| `video_asset_store.csv` > 500 行 | CSV → SQLite 迁移 |
| 飞书 Webhook URL 配置完成 | `feishu_webhook_client.py` 上线 |
| 真实平台 public 模式验证通过 | `mode=public` 替换 `mode=mock` 作为默认 |

---

## 八、Phase 3 开发优先级重新排序

### 8.1 Phase 3 总览

| 阶段 | 名称 | 状态 | 测试 | 预计时间 |
|:--:|------|:--:|:--:|:--:|
| P0 | Pipeline + Analyzer + Lead Scoring + CRM | ✅ | 6 | — |
| P1 | Task Model + Intent Model + Scheduler | ✅ | 94 | — |
| P2A | 资产模型固化 (CommentRecord/VideoAsset/task_type) | ✅ | 39 | — |
| P2B | Video Asset → Content Intelligence → Script Library | ✅ | 40 | — |
| P2C | Inbound 闭环 (OwnAccount + Detector + Alert + Journey) | ✅ | 65 | — |
| **P3-1** | **飞书运营层接入** | ⬜ | ~20 | 1-2天 |
| **P3-2** | **Public Collector 真实化** | ⬜ | ~30 | 2-3天 |
| **P3-3** | **内容生产闭环验证** | ⬜ | ~15 | 1-2天 |
| **P3-4** | **数据基础设施强化** | ⬜ | ~10 | 1天 |

### 8.2 P3-1: 飞书运营层接入（最高优先级）

**为什么第一**: AlertEngine 数据结构已完成 (`FeishuAlertPayload.to_feishu_message()`)，只差 Webhook 发送。飞书接入后人工流程即可运转。

| # | 任务 | 输入 | 输出 | 新增文件 |
|:--:|------|------|------|------|
| 1 | 配置飞书机器人 Webhook URL | 飞书开放平台 | Webhook endpoint | 无 |
| 2 | `feishu_webhook_client.py` | `FeishuAlertPayload.to_feishu_message()` | HTTP POST 发送 | `08_SYSTEM/scripts/feishu_webhook_client.py` |
| 3 | 第一条飞书卡片发送 + 格式验证 | Mock Alert | 人工验证消息卡片 | 无 |
| 4 | @负责人机制 | 飞书 open_id 配置 | S级 alert @指定人 | 无 |
| 5 | 飞书多维表格 Lead 看板 | leads_master.csv | 运营看板 | 无（飞书端配置） |

### 8.3 P3-2: Public Collector 真实化

**为什么第二**: 当前全部用 Mock 数据跑通链路。真实化是最关键的价值验证。

| # | 任务 | 说明 | 新增/修改文件 |
|:--:|------|------|------|
| 1 | 单条抖音公开页面 HTTP 请求 | `page_fetcher.py` 发送真实请求，获取搜索结果页 HTML | 修改 `page_fetcher.py` |
| 2 | HTML → 结构化数据验证 | 验证 `douyin_page_parser.py` 能否解析真实 HTML | 修改 `douyin_page_parser.py` |
| 3 | UA 池 + 速率限制生效 | `collector_state.py` RateLimiter 与真实请求联动 | 修改 `collector_state.py` |
| 4 | 搜索 → 账号发现 → 视频发现端到端 | 完整真实链路单条验证 | 无新文件 |
| 5 | 首次采集 7 天时间窗口验证 | 限制首次采集范围为最近7天 | 已有（验证） |
| 6 | 增量 cursor 机制验证 | last_comment_id 或分页 cursor | 已有（验证） |
| 7 | public 模式开关上线 | production config 中启用 mode=public | 修改 `config_loader.py` |

**安全约束**:
- 每次请求间隔 ≥ 5 秒
- 每天总请求 ≤ 100 次（P3-2 期间）
- 仅请求公开页面，不携带 Cookie
- 不采集私信/手机号/真实姓名

### 8.4 P3-3: 内容生产闭环验证

**为什么第三**: 需 P3-2 采集到真实视频后才能进行爆款分析。

| # | 任务 | 输入 | 输出 |
|:--:|------|------|------|
| 1 | 第一条竞品视频九维拆解 | video_asset_store (真实) | VideoAnalysisResult |
| 2 | 第一条 AI 二创脚本 | 爆款拆解模板 | scripts_ai/*.md |
| 3 | 人工审核 + 差异化 (四川本地) | AI脚本 | 修改后脚本 |
| 4 | 拍摄 + 自有账号发布 | 脚本 | content_calendar 记录 |
| 5 | `content_performance.csv` 初始化 | 发布后数据 | 效果追踪 |

### 8.5 P3-4: 数据基础设施强化

| # | 任务 | 触发条件 |
|:--:|------|:--:|
| 1 | CSV → SQLite 迁移 | comment_asset_library > 10K 或 video_asset > 500 |
| 2 | Lead 转化漏斗看板 | CRM leads 积累 ≥ 50 条 |
| 3 | 飞书多维表格自动同步 | P3-1 Webhook 稳定 |

### 8.6 Phase 4+ 禁止提前开始

| 禁止项 | 前置条件 |
|------|------|
| ❌ 多平台扩展 (抖音→小红书→快手) | P3-2 抖音单平台跑通 |
| ❌ AI 视频生成 | P3-3 人工拍摄素材 ≥ 10 条 |
| ❌ 云端部署 | P3 全部完成 + 商业数据验证 |
| ❌ 真实大规模采集 (>100条/天) | P3-2 速率控制验证 + 风控 OK |

---

## 九、新增文件清单

### P3-1

| 文件 | 路径 | 说明 |
|------|------|------|
| `feishu_webhook_client.py` | `08_SYSTEM/scripts/` | 飞书 Webhook HTTP 发送 |

### 待初始化文件（已有模型，需创建数据实例）

| 文件 | 路径 | 状态 |
|------|------|:--:|
| `content_calendar.csv` | `04_CONTENT/calendar/` | 空目录 |
| `content_performance.csv` | `04_CONTENT/analytics/` | 空目录 |
| `content_to_lead_mapping.csv` | `04_CONTENT/analytics/` | 空目录 |
| `content_insight.json` | `04_CONTENT/analytics/` | 空目录 |

### 修改文件清单

| 文件 | 修改内容 | 阶段 |
|------|------|:--:|
| `PV_OS_PROJECT_STATUS.md` | 更新为 V3.2，标记 Phase 2C 完成 | P3-0 (进入前) |
| `PV_OS_MASTER_CONTEXT.md` | 补充 V3.0 资产模型 + Inbound 闭环说明 | P3-0 |
| `page_fetcher.py` | 增加真实 HTTP 请求路径 (非 Mock) | P3-2 |
| `douyin_page_parser.py` | 真实 HTML 解析逻辑 | P3-2 |
| `collector_state.py` | RateLimiter 与真实请求联动 | P3-2 |
| `config_loader.py` | mode=public 配置 | P3-2 |
| `competitor_master.csv` | 扩充 content_learning 类型账号 | P3-0 |

---

## 十、字段变化汇总

### 已实现字段（Phase 2C 完成）

| 数据模型 | 已实现字段数 | 文件 |
|------|:--:|------|
| CommentRecord | 20+ | `collector_base.py` |
| VideoAsset | 31 | `video_asset.py` |
| OwnAccount | 14 | `own_account_registry.py` |
| CompetitorCandidate | 24 | `competitor_discovery.py` |
| CollectionTask | 16+ | `task_manager.py` |
| Alert | 15 | `alert_engine.py` |
| ContactJourney | 16 | `alert_engine.py` |
| FeishuAlertPayload | 12 | `alert_engine.py` |

### Phase 3 新增字段（代码层面）

| 模型 | 新增字段 | 说明 | 阶段 |
|------|------|------|:--:|
| `leads_master.csv` | `is_inbound` (boolean) | 区分 Outbound/Inbound | P3-0 |
| `leads_master.csv` | `alert_sent_at` (datetime) | 飞书发送时间 | P3-1 |
| `leads_master.csv` | `journey_id` (string) | 关联 ContactJourney | P3-1 |
| `competitor_master.csv` | 已含 account_purpose/learning_priority | ✅ | — |
| `CommentRecord` | 已含 is_own_account/user_id/user_profile_url | ✅ | — |

---

## 十一、执行顺序

```
P3-0 (进入前准备):
  1. 更新 PV_OS_PROJECT_STATUS.md → V3.2
  2. 更新 PV_OS_MASTER_CONTEXT.md → V3.0 资产模型
  3. competitor_master.csv 扩充 content_learning 账号
  4. leads_master.csv 增加 is_inbound/alert_sent_at/journey_id
  5. 初始化 04_CONTENT 子目录 + CSV header

P3-1 (飞书运营层):
  6. 配置飞书 Webhook URL
  7. feishu_webhook_client.py
  8. 第一条飞书消息卡片测试
  9. @负责人 + 飞书多维表格 (可选)

P3-2 (Public Collector 真实化):
  10. page_fetcher.py 真实 HTTP 请求
  11. douyin_page_parser.py 真实 HTML 解析
  12. RateLimiter 联动验证
  13. 搜索→发现→采集 端到端单条验证
  14. 首次7天窗口 + 增量 cursor 验证

P3-3 (内容闭环):
  15. 第一条真实视频九维拆解
  16. 第一条 AI 二创脚本
  17. 人工拍摄 → 自有账号发布
  18. content_performance 追踪

P3-4 (基础设施):
  19. CSV → SQLite (按触发条件)
  20. Lead 转化漏斗
```

---

## 十二、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V3.0 | 2026-07-20 | 首次 V3.0 架构：双闭环、三层资产、九维拆解 |
| V3.1 | 2026-07-20 | 架构冻结：7 模块最终设计、602 测试基线 |
| **V3.2** | **2026-07-20** | **最终锁定：城市级区域模型、双信号分层判断、Competitor Knowledge Asset、四层消费矩阵、唯一合法路线、Inbound判断链、双层存储、P3重排序** |
