# 02_DATA —— 数据资产层

> PV_OS 数据存储、清洗、管理与目录约定
>
> 最后更新：2026-07-11

---

## 一、目录结构

```
02_DATA/
├── README.md           # 本文件 · 数据层说明
├── raw/                # 原始采集数据（不可修改）
├── processed/          # 清洗后结构化数据
├── datasets/           # 训练 / 评估用数据集
├── exports/            # 对外导出数据报表
└── data_dict/          # 数据字典 · 字段定义
```

---

## 二、各级目录说明

### 2.1 raw/ —— 原始数据

**定位：** 数据采集管道的第一落点。存放从平台直接采集的原始数据，**保持采集时的原始形态，不做任何修改**。

**目录组织规则：**
```
raw/
├── douyin/             # 抖音原始数据
│   ├── videos/         #   视频元数据
│   ├── comments/       #   评论数据
│   └── accounts/       #   账号数据
├── xiaohongshu/        # 小红书原始数据
│   ├── notes/
│   ├── comments/
│   └── accounts/
├── kuaishou/           # 快手原始数据
│   ├── videos/
│   ├── comments/
│   └── accounts/
└── shipinhao/          # 视频号原始数据
    ├── videos/
    └── interactions/
```

**命名约定：** `{平台}_{内容类型}_{日期}.{格式}`
- 示例：`douyin_comments_20260711.json`

**规则：**
- 原始文件一旦写入，**禁止人工编辑**
- 每次采集增量追加，不覆盖已有文件
- 采集失败的批次标注 `_FAILED` 后缀

---

### 2.2 processed/ —— 处理后数据

**定位：** 经过清洗、去重、结构化后的数据，供 AI Agent 和分析流程直接消费。

**目录组织规则：**
```
processed/
├── douyin/
│   ├── comments_clean.csv       # 清洗后的评论
│   ├── leads_identified.csv     # 识别出的潜在客户
│   └── accounts_clean.csv       # 清洗后的账号数据
├── xiaohongshu/
├── kuaishou/
├── shipinhao/
└── cross_platform/              # 跨平台汇总数据
    ├── competitor_list.csv      # 竞品账号总表
    └── leads_master.csv         # 潜在客户主表
```

**数据质量标准：**
| 维度 | 标准 |
|------|------|
| 去重 | 按平台 ID + 时间戳去重，零冗余 |
| 脱敏 | 用户昵称以外的个人信息已脱敏 |
| 结构化 | 统一字段名、统一编码（UTF-8） |
| 可追溯 | 每条数据标注 `source_file` 指向 raw/ 来源 |

---

### 2.3 datasets/ —— 数据集

**定位：** 从 processed/ 中按任务需求筛选、标注后的专用数据集，用于 AI 模型训练、Prompt 测试、Agent 评估。

**目录组织规则：**
```
datasets/
├── train/               # 训练集
│   ├── comment_intent_labeled.csv    # 评论意图标注数据
│   └── customer_score_labeled.csv    # 客户评分标注数据
├── eval/                # 评估集
│   ├── agent_eval_cases.json         # Agent 评估用例
│   └── prompt_test_set.csv           # Prompt 测试集
└── seed/                # 种子数据
    ├── seed_competitors.csv          # 初始竞品种子列表
    └── seed_keywords.csv             # 初始关键词库
```

---

### 2.4 exports/ —— 导出数据

**定位：** 对外交付的数据报表、客户名单导出、运营周报等。

**命名约定：** `{类型}_{日期}_{版本}.{格式}`
- 示例：`weekly_report_20260711_v1.xlsx`

---

### 2.5 data_dict/ —— 数据字典

**定位：** 定义所有数据表的字段含义、数据类型、取值范围、业务含义。

**核心文件：**
- `fields_definition.md` — 通用字段定义
- `comment_fields.md` — 评论相关字段定义
- `customer_fields.md` — 客户相关字段定义
- `competitor_fields.md` — 竞品相关字段定义

---

## 三、数据命名全局约定

### 3.1 文件命名模式

```
{平台/来源}_{内容类型}_{日期}[_{版本}].{格式}
```

| 组成部分 | 说明 | 示例 |
|---------|------|------|
| 平台/来源 | `douyin`、`xiaohongshu`、`kuaishou`、`shipinhao`、`cross` | `douyin` |
| 内容类型 | `comments`、`videos`、`accounts`、`leads`、`competitors` | `comments` |
| 日期 | `YYYYMMDD` | `20260711` |
| 版本 | 可选，`v1`、`v2` | `v1` |
| 格式 | `json`、`csv`、`xlsx` | `csv` |

### 3.2 字段命名

- 全小写蛇形命名：`user_id`、`comment_text`、`publish_time`
- 时间字段统一 ISO 8601：`2026-07-11T14:30:00+08:00`
- 布尔字段 `is_` 前缀：`is_potential_lead`、`is_verified`
- 枚举字段 `_type` 后缀：`customer_type`、`platform_type`

---

## 四、数据流向

```
平台公开数据
     │
     ▼
02_DATA/raw/              ← 原始落盘，不可修改
     │
     │ 数据清洗管道
     ▼
02_DATA/processed/         ← 清洗后结构化，供 Agent 消费
     │
     ├──→ 03_AI_AGENT/     ← Comment Analyzer、Customer Scorer
     ├──→ 04_CONTENT/      ← 爆款数据 → 拆解分析
     ├──→ 05_CUSTOMER_CRM/ ← 客户线索入库
     └──→ 09_AI_OPERATION/ ← 竞品分析、运营洞察
           │
           ▼
02_DATA/datasets/          ← 标注数据用于训练和评估
02_DATA/exports/           ← 对外报表和交付物
```

---

## 五、当前数据清单

| 数据集 | 状态 | 预计来源 |
|--------|------|---------|
| 抖音评论区数据 | ⬜ 待采集 | 抖音公开内容 |
| 小红书笔记数据 | ⬜ 待采集 | 小红书公开内容 |
| 快手视频数据 | ⬜ 待采集 | 快手公开内容 |
| 竞品种子账号列表 | ⬜ 待建立 | 人工筛选 |
| 光伏关键词库 | ⬜ 待建立 | 行业调研 |

---

## 六、变更记录

| 日期 | 变更 | 操作者 |
|------|------|--------|
| 2026-07-11 | 创建 02_DATA 子目录结构 + README | Codex |
