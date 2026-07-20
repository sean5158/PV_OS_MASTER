# PV_OS_ACCOUNT_MODEL V3.0

版本：V3.0
日期：2026-07-20
用途：PV_OS 账号模型 — 区分自有账号与竞品账号，竞品账号按用途重新分类

> 本次不做代码修改。本文为架构设计文件。
> 替代/升级 `PV_OS_COMPETITOR_ACCOUNT_MODEL.md` V1.0。

---

## 一、账号总分类

```
PV_OS 账号体系
│
├── 自有账号 (Own Account)
│   └── 用于: 内容发布 + Inbound评论采集
│
└── 竞品账号 (Competitor Account)
    ├── Customer Source Account  → 用于: 找客户
    └── Content Learning Account → 用于: 学爆款
```

---

## 二、Own Account（自有账号）🆕

### 2.1 定位

PV_OS 自身运营的视频平台账号。

| 维度 | 说明 |
|------|------|
| 用途 | 发布光伏内容 → 吸引客户主动咨询 |
| 注册 | own_account_master.csv |
| 监控 | 采集自有账号评论 → Inbound Pipeline |
| IP属性 | 四川本地IP博主 |

### 2.2 存储

```
02_DATA/02_COMPETITOR_DATABASE/own_account_master.csv
```

### 2.3 字段

| 字段 | 说明 |
|------|------|
| `account_id` | 内部ID |
| `platform` | douyin / xiaohongshu |
| `platform_account_id` | 平台账号ID |
| `account_name` | 昵称 |
| `account_url` | 主页链接 |
| `monitor_comments` | 是否监控该账号评论 (默认true) |
| `content_frequency` | 发布频率 |
| `primary_topic` | 主要内容方向 |

---

## 三、Competitor Account（竞品账号）

### 3.1 重新分类原则

竞品账号必须按**商业用途**分为两类，不再仅按内容类型分四级：

| 旧分类 (V1.0) | 新分类 (V3.0) |
|:---|:---|
| 一级 全国品牌 | → Customer Source 或 Content Learning |
| 二级 区域安装商 | → Customer Source (主要) |
| 三级 城市案例 | → Customer Source + Content Learning |
| 四级 装修改造 | → Content Learning (主要) |

### 3.2 Customer Source Account（客户来源账号）

**用途**: 采集评论区，从中发现真实客户。

**特征**:
- 评论区有大量客户询价/咨询
- 内容面向终端消费者
- 四川/重庆/贵州客户密度高 → 最高优先级

**典型账号**:
- 川渝黔本地安装商账号
- 城市别墅光伏案例账号
- 全国品牌中川渝黔评论集中的账号

**采集策略**:
- 全量评论采集
- 最高频率 (S级 6h, A级 daily)
- IP属地过滤川渝黔

### 3.3 Content Learning Account（内容学习账号）

**用途**: 分析爆款内容结构，学习选题和表达方式。

**特征**:
- 内容质量高、互动好
- 结构清晰、可拆解
- 不限地域（全国优秀同行均可）

**重要原则**: PV_OS 自身是四川IP博主。

| 竞品地域 | 用途 | 优先级 |
|---------|------|:--:|
| 四川同行 | 市场观察（了解本地竞争格局） | 中 |
| **四川以外优秀同行** | **爆款学习（差异化参考）** | **高** |
| 全国头部品牌 | 内容策略参考 | 中 |

**典型账号**:
- 全国优秀光伏内容创作者
- 爆款频出的装修/改造账号
- 阳光房/别墅改造类高互动账号

**采集策略**:
- 仅采集视频资产（不需要全量评论）
- learning_priority 排序 (1-10)
- 定期 AI 内容分析

### 3.4 新增核心字段

在 `competitor_master.csv` 中增加：

| 字段 | 类型 | 说明 |
|------|------|------|
| **`account_purpose`** | enum | `customer_source` / `content_learning` / `both` |
| **`learning_priority`** | int 1-10 | 内容学习优先级（仅 content_learning/both 时有效） |

### 3.5 account_purpose 判定规则

```
账号入库
    │
    ├── 川渝黔本地安装商/案例号？
    │       → account_purpose = customer_source
    │       → 全量评论采集
    │
    ├── 全国品牌评论区川渝黔客户密度高？
    │       → account_purpose = customer_source
    │       → IP属地过滤采集
    │
    ├── 四川以外优秀同行，内容质量高？
    │       → account_purpose = content_learning
    │       → 仅采集视频资产，AI分析
    │       → learning_priority = 7-10
    │
    ├── 本地同行，内容有参考价值？
    │       → account_purpose = both
    │       → 评论采集 + 内容分析
    │       → learning_priority = 3-6
    │
    └── 纯资讯号/供应商号？
            → 不入库
```

---

## 四、与采集策略的关系

| account_purpose | 评论采集 | 视频采集 | 内容分析 | 监控频率 |
|:---|:--:|:--:|:--:|:--:|
| `customer_source` | ✅ 全量 | ✅ | — | 6h/daily |
| `content_learning` | — | ✅ 全量 | ✅ | weekly |
| `both` | ✅ 全量 | ✅ 全量 | ✅ | daily |

---

## 五、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V3.0 | 2026-07-20 | 重新分类：增加 Own Account，竞品按用途分 customer_source / content_learning / both |
