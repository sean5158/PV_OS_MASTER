# Phase 3-3.2 Content Intelligence Enhancement 设计

**版本**: V1.0
**日期**: 2026-07-21
**状态**: 设计阶段 — 不执行代码
**项目**: PV_OS V3.3
**上游**: Phase 3-3 Content Intelligence Core（V2.0，已完成）
**测试基线**: 761 测试（Phase 3-2.2 Public Parser Core）

> **本文档定义 Content Intelligence 的六项增强设计。**
> 在 Phase 3-3 V2.0 八维分析基础上，增加评分模型、标签体系、Hook 分析、
> 内容学习规则、二创规则和 Insight 升级。
> 不修改任何已有代码。

---

## 一、爆款视频评分模型（Video Viral Score）

### 1.1 设计动机

Phase 3-3 V2.0 已有的 `viral_score` 是一个单一整数（如 85、100），缺乏解释性。
需要升级为多维度、可解释的评分体系，回答"为什么爆"而非仅"爆不爆"。

### 1.2 评分维度

| # | 维度 | 权重 | 数据来源 | 说明 |
|:--:|------|:--:|------|------|
| 1 | **播放表现** | 20% | `like_count` / `comment_count` / `collect_count` / `share_count` | 归一化后的综合互动分 |
| 2 | **点赞率** | 15% | `like_count` ÷ 估计播放量 | 点赞 = 认可信号。光伏内容正向点赞比例越高，越说明内容有说服力 |
| 3 | **评论率** | 20% | `comment_count` ÷ 估计播放量 | 评论 = 需求信号。光伏安装类视频评论率天然高（都在问价格/能不能装） |
| 4 | **收藏率** | 15% | `collect_count` ÷ 估计播放量 | 收藏 = 决策信号。用户收藏意味着「以后可能用得上」，光伏决策周期长，收藏权重高于一般内容 |
| 5 | **转发率** | 10% | `share_count` ÷ 估计播放量 | 转发 = 传播信号。「帮朋友省钱」是最强转发动机 |
| 6 | **内容完整度** | 10% | `duration_seconds` + AI 结构分析 | 结构完整 + 有钩子 + 有数据 + 有 CTA 的完整视频得分更高 |
| 7 | **用户共鸣程度** | 5% | 评论语义分析 | 评论区出现"真的吗""我家也想装""太实用了"等高共鸣词频 |
| 8 | **光伏客户相关性** | 5% | `housing_signal` + `relevance_score` | 视频内容与 PV_OS 目标客户（城市家庭光伏）的相关程度 |

**权重总计: 100%**

### 1.3 评分公式

```
ViralScore =
    engagement_score × 0.20
  + like_rate_score  × 0.15
  + comment_rate_score × 0.20
  + collect_rate_score × 0.15
  + share_rate_score  × 0.10
  + completeness_score × 0.10
  + resonance_score   × 0.05
  + relevance_score   × 0.05
```

每个子维度先归一化到 0-100，再加权求和。

### 1.4 分级标准

| 等级 | 分数范围 | 含义 | 动作 |
|:--:|:--:|------|------|
| **S+** | 90-100 | 现象级爆款 | 深度拆解，存入爆款模板库 |
| **S** | 80-89 | 强爆款 | 八维全量分析 + 生成二创脚本 |
| **A** | 65-79 | 优质内容 | 八维分析 + 提取可复用元素 |
| **B** | 40-64 | 普通内容 | 仅记录，不深入分析 |
| **C** | 0-39 | 低质/不相关 | 标记跳过 |

### 1.5 与现有 viral_score 的关系

| 维度 | Phase 3-3 V2.0 | Phase 3-3.2 |
|------|:--:|:--:|
| 评分方式 | 单一整数 `viral_score` | 八维加权 `ViralScore` |
| 可解释性 | 无 | 每个子维度独立评分 |
| 输出字段 | `viral_score` | `viral_score` + `viral_score_detail` (JSON) |
| 兼容性 | — | 向后兼容，`viral_score` 保留为总分 |

### 1.6 输出格式

```json
{
  "video_id": "dy_v01234",
  "viral_score": 78,
  "viral_score_grade": "A",
  "viral_score_detail": {
    "engagement_score": 75,
    "like_rate_score": 82,
    "comment_rate_score": 90,
    "collect_rate_score": 68,
    "share_rate_score": 55,
    "completeness_score": 85,
    "resonance_score": 72,
    "relevance_score": 95
  },
  "viral_score_explanation": "评论率极高（90分），说明内容精准触达有需求的用户。收藏率偏低（68分），建议加强CTA引导收藏。"
}
```

---

## 二、光伏行业内容标签体系

### 2.1 设计动机

Phase 3-3 V2.0 的 VideoAnalysisResult 已有 `customer_type`、`housing_signal` 等字段，但缺少体系化的光伏行业专属标签。
需要一个结构化的标签体系，支持视频分类检索、趋势分析、选题推荐。

### 2.2 标签体系结构

```
PV_OS 内容标签体系
│
├── 一、客户需求标签（Customer Needs）
│   标注: 视频解决了用户的什么需求？
│
├── 二、用户心理标签（User Psychology）
│   标注: 视频击中用户什么心理状态？
│
└── 三、内容形式标签（Content Format）
    标注: 视频采用了什么形式？
```

### 2.3 一、客户需求标签（Customer Needs）

| # | 标签 | 含义 | 典型内容特征 | 需求强度 |
|:--:|------|------|------|:--:|
| 1 | `电费降低` | 用户想降低电费 | "电费从 X 降到 Y"、"一个月省了 XX" | ⭐⭐⭐⭐⭐ |
| 2 | `收益计算` | 用户想知道收益 | "XX 年回本"、"装了多久能赚回来" | ⭐⭐⭐⭐ |
| 3 | `屋顶利用` | 用户有空置屋顶 | "屋顶空着也是空着"、"露台做光伏" | ⭐⭐⭐⭐ |
| 4 | `别墅光伏` | 别墅/高端住宅场景 | 别墅实拍、叠拼安装、花园洋房改造 | ⭐⭐⭐⭐⭐ |
| 5 | `阳光房` | 阳光房+光伏结合 | "阳光房改光伏"、"阳光房顶做光伏" | ⭐⭐⭐⭐ |
| 6 | `自建房` | 城市自建房光伏 | "自建房装光伏划算吗"、"自建房屋顶" | ⭐⭐⭐ |
| 7 | `安装效果` | 想看装完什么样子 | 安装前后对比、外观展示、邻居参观 | ⭐⭐⭐⭐ |
| 8 | `政策咨询` | 了解政策/补贴 | "现在还有补贴吗"、"并网政策" | ⭐⭐⭐ |
| 9 | `品牌对比` | 对比不同品牌 | "XX 和 XX 哪个好"、"选什么牌子" | ⭐⭐⭐ |
| 10 | `小商业光伏` | 民宿/酒店/茶楼等 | "民宿装光伏"、"茶楼屋顶做光伏" | ⭐⭐⭐⭐ |

### 2.4 二、用户心理标签（User Psychology）

| # | 标签 | 含义 | 评论典型表达 |
|:--:|------|------|------|
| 1 | `想了解` | 认知阶段，没决定装 | "这是什么"、"光伏怎么用"、"能发多少电" |
| 2 | `对比价格` | 在多家比价 | "多少钱一瓦"、"XX 家多少钱"、"贵不贵" |
| 3 | `担心被骗` | 信任顾虑 | "靠谱吗"、"会不会是套路"、"有没有坑" |
| 4 | `想安装` | 决策阶段，接近行动 | "怎么联系"、"成都能装吗"、"给我算一下" |
| 5 | `等待决策` | 有兴趣但犹豫 | "再看看"、"考虑一下"、"问一下家人" |
| 6 | `信任建立` | 看到案例后消除顾虑 | "原来真的可以"、"我也要装"、"太实用了" |
| 7 | `炫耀心理` | 装了之后想展示 | "我家装了"、"邻居都来看了"、"电费0元" |

### 2.5 三、内容形式标签（Content Format）

| # | 标签 | 含义 |
|:--:|------|------|
| 1 | `安装实拍` | 真实安装过程记录 |
| 2 | `前后对比` | 安装前 vs 安装后 |
| 3 | `客户见证` | 客户出镜讲体验 |
| 4 | `电费展示` | 电费账单前后对比 |
| 5 | `知识科普` | 光伏技术/政策讲解 |
| 6 | `避坑指南` | 揭露行业套路 |
| 7 | `案例合集` | 多个案例聚合 |
| 8 | `效果展示` | 只展示结果，不展示过程 |

### 2.6 标签存储

每个标签体系独立存储，互不覆盖：

```
video_asset_store.csv 新增列:
├── tags_customer_needs    # 逗号分隔: "电费降低,别墅光伏,收益计算"
├── tags_user_psychology   # 逗号分隔: "想了解,信任建立"
└── tags_content_format    # 逗号分隔: "安装实拍,前后对比,电费展示"

video_analysis JSON 新增字段:
{
  "tags": {
    "customer_needs": ["电费降低", "别墅光伏"],
    "user_psychology": ["想了解", "信任建立"],
    "content_format": ["安装实拍", "前后对比"]
  }
}
```

### 2.7 标签的业务用途

| 用途 | 依赖标签 | 说明 |
|------|------|------|
| ContentInsight 趋势分析 | customer_needs | 哪种需求标签的视频在增长？ |
| 选题推荐 | customer_needs + content_format | "别墅光伏"+"前后对比" = 推荐选题 |
| 用户心理匹配 | user_psychology | 不同心理阶段匹配不同内容 |
| 竞品内容地图 | 全部三类 | 绘制竞品内容覆盖热力图 |

---

## 三、Hook 分析模型

### 3.1 设计动机

Phase 3-3 V2.0 已有 `hook_3_seconds` 字段（文字描述），但缺少分类。
需要建立结构化的 Hook 分类体系，支持：
- 快速检索同类型 Hook
- 统计哪种 Hook 类型效果最好
- 生成新脚本时自动推荐最佳 Hook 类型

### 3.2 四种 Hook 类型

```
Hook 分类（互斥，每条视频唯一类型）
│
├── 类型 A: 问题型 Hook
│   定义: 前 3 秒抛出一个让目标用户停下来思考的问题
│   典型: "你家一个月电费多少？"
│         "别墅装光伏划算吗？"
│         "你知道屋顶空着每年损失多少钱吗？"
│   适用: 认知阶段 → 想了解的用户
│
├── 类型 B: 冲突型 Hook
│   定义: 前 3 秒制造矛盾/反差/对立
│   典型: "物业不让装光伏，我偏装"
│         "邻居都说我被骗了，三个月后..."
│         "花5万装光伏，被家人骂疯了"
│   适用: 有顾虑 → 担心被骗的用户
│
├── 类型 C: 数据型 Hook
│   定义: 前 3 秒用数字制造冲击
│   典型: "电费从3000降到300，我只做了一件事"
│         "成都别墅光伏，一年省了1万8"
│         "装了光伏，每天发50度电"
│   适用: 比价阶段 → 对比价格的用户
│
└── 类型 D: 场景型 Hook
    定义: 前 3 秒用真实场景代入
    典型: "这是我家屋顶，以前空着，现在..."
          "带你看成都别墅光伏安装全过程"
          "站在阳光房里，头顶就是光伏板"
    适用: 决策阶段 → 想安装的用户
```

### 3.3 Hook 效果评分维度

| 维度 | 权重 | 说明 |
|------|:--:|------|
| 停留率 | 40% | 用户是否看完前 3 秒（从完播率推断） |
| 完播率 | 30% | 视频整体完播率 |
| 评论触发 | 20% | 评论中是否出现 Hook 相关内容 |
| 复用性 | 10% | 是否可移植到 PV_OS 场景 |

### 3.4 Hook 存储字段

```
video_analysis JSON 新增:
{
  "hook_analysis": {
    "hook_type": "数据型",           # 问题型 / 冲突型 / 数据型 / 场景型
    "hook_text": "电费从3000降到300，我只做了一件事",
    "hook_effectiveness": "high",     # high / medium / low
    "hook_score": 85,                 # 0-100
    "why_it_works": "数字对比制造认知差，让用户产生'我也想省'的冲动",
    "pv_os_adaptability": "high"      # 是否可复用到 PV_OS 内容
  }
}
```

### 3.5 Hook 类型与客户心理的映射

| Hook 类型 | 最佳匹配心理 | 投放阶段 |
|------|------|------|
| 问题型 | 想了解 | 认知 → 兴趣 |
| 冲突型 | 担心被骗 | 破除顾虑 |
| 数据型 | 对比价格 | 兴趣 → 决策 |
| 场景型 | 想安装 | 决策 → 行动 |

---

## 四、内容学习规则

### 4.1 核心原则

**内容学习 ≠ 客户发现。两种商业目的，两种账号池，不可混淆。**

### 4.2 A 类账号：内容学习资产

| 维度 | 规则 |
|------|------|
| **地域** | **四川以外**。全国范围内光伏/新能源优秀内容创作者 |
| **判定依据** | `account_purpose = "content_learning"` 或 `"both"` |
| **学习优先级** | `learning_priority` 1-10，由视频 ViralScore 和复用性决定 |
| **采集内容** | 视频 + 视频分析（不采集评论） |
| **分析深度** | 八维分析 + ViralScore + 标签 + Hook 分类 |
| **输出用途** | 爆款拆解 → 二创脚本 → 自有账号发布 |
| **禁止用途** | ❌ 不得从这类账号的评论区找客户 |

**为什么优先四川以外？**

PV_OS 自身是四川 IP 博主。学习四川同行的内容 = 模仿邻居 = 同质化。
学习省外优秀同行 = 借鉴结构 + 替换本地元素 = 差异化。

### 4.3 B 类账号：客户发现资产

| 维度 | 规则 |
|------|------|
| **地域** | **四川、重庆、贵州**。本地安装商、案例号 |
| **判定依据** | `account_purpose = "customer_source"` 或 `"both"` |
| **采集内容** | 评论区（全量）+ 视频元数据 |
| **分析深度** | CommentIntent → RegionDetection → LeadScoring |
| **输出用途** | 客户发现 → CRM → 人工触达 |
| **禁止用途** | ❌ 不得用于内容学习（四川同行内容不具备全国爆款参考价值） |

### 4.4 "both" 类账号的二次分流

```
account_purpose = "both" 的视频
│
├── 内容端: 八维分析 + ViralScore + 标签
│    → 条件: learning_priority ≥ 5 或 ViralScore ≥ 65
│    → 输出: 二创脚本
│
└── 客户端: 评论采集 + CommentIntent
     → 条件: 目标区域（川渝黔）评论用户
     → 输出: Lead → CRM
```

### 4.5 强制禁止

| 禁止行为 | 原因 |
|------|------|
| ❌ 从 A 类账号评论区找客户 | 评论用户不在目标市场（川渝黔以外） |
| ❌ 用 B 类账号视频做爆款学习 | 四川同行内容同质化，无法提供差异化参考 |
| ❌ 不区分 account_purpose 全量分析 | 浪费计算资源，污染分析结果 |
| ❌ 对 A 类账号做区域过滤 | content_learning 不应受地域限制 |

---

## 五、二创脚本生成规则

### 5.1 设计动机

Phase 3-3 V2.0 的 ScriptLibrary 已有 `ScriptEntry` 结构，但缺少**生成规则**。
需要明确脚本是如何从分析结果中推导出来的，而非"AI 自由发挥"。

### 5.2 生成流程

```
竞品爆款视频（S 级以上）
│
▼
Step 1: 结构分析
  提取: video_structure（开头-中段-结尾的结构模式）
  输出: structure_template
│
▼
Step 2: 提取有效元素
  提取: hook_template / title_formula / key_phrases / comment_trigger
  注意: 只提取可复用的"模式"，不复制具体内容
│
▼
Step 3: 差异化角度
  判定: 竞品内容属于哪个用户心理阶段？
  选择: PV_OS 切入的差异化角度
  原则: 
    - 竞品用"电费对比"→ PV_OS 用"阳光房美学"
    - 竞品用"省钱逻辑"→ PV_OS 用"品质生活"
    - 竞品用"数据说服"→ PV_OS 用"真实案例"
│
▼
Step 4: 结合四川城市家庭光伏场景
  替换: 竞品全国通用元素 → 四川本地元素
  示例:
    竞品: "别墅光伏一年省2万"
    PV_OS: "成都叠拼装光伏，半年省了8千"
  要求: 必须有明确的地域标识（成都/绵阳/重庆/贵阳...）
│
▼
Step 5: 生成原创脚本
  组合: structure_template + new_hook + local_scene + CTA
  输出: ScriptEntry（review_status=pending）
│
▼
Step 6: 人工审核
  检查: 真实性 / 专业度 / 本地化 / 差异化 / 合规
  通过 → review_status=approved → 进入拍摄
```

### 5.3 有效元素提取规则

| 提取元素 | 定义 | 提取方式 | 示例 |
|------|------|------|------|
| `structure_template` | 视频结构骨架 | 从 video_structure 抽象 | "痛点→方案→数据→见证→CTA" |
| `hook_template` | 钩子模板 | 从 hook_3_seconds 抽象 | "[数字]从[旧]变成[新]，我只做了一件事" |
| `title_formula` | 标题公式 | 从 title_pattern 提取 | "数字对比型：XX平米装了光伏，省了XX" |
| `key_phrases` | 高频话术 | 评论触发词 + 完播位置文本 | "装了光伏""真实案例""本地安装" |
| `pain_point_angle` | 痛点切入角度 | 从 pain_point 抽象 | 电费焦虑 → 品质生活 → 信任顾虑 |

### 5.4 差异化角度决策树

```
竞品视频主题
│
├── 电费降低类
│   └── PV_OS 差异化: 不只省钱，还提升生活品质
│       标题: "装了光伏之后，我家的阳光房成了全小区最好看的"
│
├── 收益计算类
│   └── PV_OS 差异化: 不算账，看结果
│       标题: "成都别墅光伏真实电费对比（附详细数据）"
│
├── 安装效果类
│   └── PV_OS 差异化: 不只拍照，讲体验
│       标题: "装了光伏一年，我最真实的三个感受"
│
└── 避坑指南类
    └── PV_OS 差异化: 不只说坑，给方案
        标题: "成都装光伏避坑指南：这三件事没人告诉你"
```

### 5.5 脚本质量检查清单

二创脚本在进入人工审核前，必须通过以下自动检查：

| # | 检查项 | 要求 |
|:--:|------|------|
| 1 | 地域标识 | 包含至少一个四川/重庆/贵州城市名或区域特征 |
| 2 | 场景匹配 | 匹配 PV_OS 目标客群（别墅/叠拼/阳光房/小商业） |
| 3 | 结构完整 | 包含 钩子 → 痛点 → 方案 → 数据 → CTA |
| 4 | 差异化 | 与源视频有至少 3 个维度的差异 |
| 5 | 合规 | 不含虚假宣传、不含"100%""绝对"等绝对化用语 |
| 6 | 时长 | 15-60 秒（短视频）或 60-180 秒（深度内容） |

---

## 六、Content Insight 升级

### 6.1 设计动机

Phase 3-3 V2.0 的 ContentInsight 已有 `top_topics` 和 `demand_gaps`。
Phase 3-3.2 增加 ViralScore 和标签体系后，ContentInsight 的数据源从"几条视频"升级为"结构化多维度数据"。
需要实现从"描述性统计"到"预测性推荐"的升级。

### 6.2 四大输出升级

```
ContentInsight V2.0                              ContentInsight V3.0
─────────────────                                ─────────────────
top_topics                                       → 爆款规律
  (话题 + 视频数)                                  (话题 × Hook × 标签 × ViralScore 交叉分析)
                                               │
demand_gaps                                      → 用户痛点趋势
  (内容空白)                                       (需求强度变化 × 时间序列)
                                               │
recommended_topics                               → 内容机会
  (推荐选题)                                       (标签组合 × 市场空白 × 竞争力评估)
                                               │
+ 新增 →                                          → 推荐选题
                                                    (可执行选题 × 预期效果 × 差异化角度)
```

### 6.3 输出一：爆款规律

```json
{
  "viral_patterns": [
    {
      "pattern_id": "vp_001",
      "description": "数据型Hook + 别墅光伏标签 = 高爆概率",
      "evidence": {
        "hook_type": "数据型",
        "tag_combination": ["别墅光伏", "安装效果", "电费降低"],
        "avg_viral_score": 85,
        "sample_count": 12,
        "success_rate": "83% (10/12 S级以上)"
      },
      "actionable_insight": "涉及别墅光伏时，优先使用数据型Hook。单纯场景型Hook在别墅场景表现一般（avg 62）。"
    }
  ]
}
```

### 6.4 输出二：用户痛点趋势

```json
{
  "pain_point_trends": [
    {
      "pain_point": "电费焦虑",
      "trend": "declining",
      "current_strength": "medium",
      "shift_to": "品质生活焦虑",
      "evidence": "近30天'电费降低'类视频 ViralScore 均值从78降至62，'阳光房美学'从55升至72",
      "recommendation": "减少纯省钱角度内容，增加品质提升角度"
    }
  ]
}
```

### 6.5 输出三：内容机会

```json
{
  "content_opportunities": [
    {
      "opportunity_id": "co_001",
      "topic": "叠拼/花园洋房光伏美学",
      "why_now": "竞品空白 + 目标市场需求增长 + PV_OS差异化切入",
      "tag_combination": ["别墅光伏", "安装效果", "屋顶利用"],
      "hook_recommendation": "场景型 (带入感强) + 冲突型 (叠拼物业沟通故事)",
      "expected_viral_score": "预估 75-85",
      "competitive_landscape": {
        "competitive_intensity": "low",
        "competitor_count": 3,
        "avg_competitor_viral_score": 58
      },
      "differentiation_angle": "用美学角度讲光伏，而不是用省钱角度"
    }
  ]
}
```

### 6.6 输出四：推荐选题

```json
{
  "recommended_topics": [
    {
      "topic_id": "rt_001",
      "title": "成都叠拼装了光伏，邻居以为我请了设计师",
      "scene_type": "叠拼/花园洋房",
      "target_audience": "成都叠拼/花园洋房业主",
      "user_psychology_stage": "认知 → 兴趣",
      "hook_type": "冲突型",
      "hook_suggestion": "装了光伏之后，邻居天天来敲门",
      "structure": "冲突开场 → 安装过程 → 效果展示 → 邻居反应 → CTA",
      "expected_duration": 45,
      "tags": ["别墅光伏", "安装效果", "屋顶利用"],
      "priority": "P0",
      "deadline": "本周内完成拍摄"
    }
  ]
}
```

### 6.7 ContentInsight 版本管理

```
04_CONTENT/strategy/
├── content_insight_CI_{timestamp}.json     # 历史快照（每次生成独立文件）
├── content_insight_latest.json             # 最新版本（供 Agent/飞书读取）
└── content_insight_trend_{week}.json        # 周趋势对比
```

---

## 七、模块边界（不修改清单）

### 7.1 锁定模块

| 模块 | 路径 | 原因 |
|------|------|------|
| **Agent** | `03_AI_AGENT/agents/` | 5 个 Agent 全部验证，不在本阶段范围 |
| **Pipeline** | `10_AI_AUTOMATION_ENGINE/workflows/comment_to_lead_pipeline.yml` | Outbound 闭环独立运行 |
| **CRM** | `05_CUSTOMER_CRM/` | 数据格式不变 |
| **Lead Score** | `CUSTOMER_SCORE_MODEL.md` | 评分规则不变 |
| **Business Rules** | `PV_OS_GOVERNANCE_RULES.md` | 治理规则不变 |
| **Public Collector** | `08_SYSTEM/scripts/` | 已在 Phase 3-2 交付 |
| **Region Rules** | `PV_OS_REGION_DETECTION_RULES.md` | 区域判断不变 |

### 7.2 本模块依赖

| 依赖 | 状态 | 说明 |
|------|:--:|------|
| Phase 3-3 Core (V2.0) | ✅ | 八维分析 + VideoAnalysisResult + ScriptLibrary |
| Phase 3-2.2 Public Parser | ✅ | VideoCandidate → VideoAsset |
| video_asset_store.csv | ✅ | 已有 400+ 条分析记录 |
| competitor_master.csv | ✅ | account_purpose 字段已就绪 |
| PV_OS_V3.2_ARCHITECTURE_LOCK.md | ✅ | 架构约束 |

### 7.3 本次设计新增的数据字段

| 文件 | 新增字段 | 说明 |
|------|------|------|
| `video_analysis JSON` | `viral_score_detail` | 八维子评分 |
| `video_analysis JSON` | `tags` | 三类标签体系 |
| `video_analysis JSON` | `hook_analysis` | Hook 类型 + 效果评分 |
| `video_asset_store.csv` | `tags_customer_needs` | 客户需求标签 |
| `video_asset_store.csv` | `tags_user_psychology` | 用户心理标签 |
| `video_asset_store.csv` | `tags_content_format` | 内容形式标签 |
| `video_asset_store.csv` | `hook_type` | Hook 类型枚举 |
| `video_asset_store.csv` | `viral_score_grade` | S+/S/A/B/C |
| `ContentInsight JSON` | `viral_patterns` | 爆款规律 |
| `ContentInsight JSON` | `pain_point_trends` | 痛点趋势 |
| `ContentInsight JSON` | `content_opportunities` | 内容机会 |
| `ContentInsight JSON` | `recommended_topics` (升级) | 可执行选题 × 预期效果 |

---

## 八、Phase 3-3.2 实施计划

| # | 任务 | 依赖 | 预计影响范围 |
|:--:|------|------|------|
| 1 | ViralScore 模型实现 | 无 | `video_analysis_model.py` 新增 ViralScore 类 |
| 2 | 标签体系实现 | ViralScore | `content_intelligence_agent.py` 新增 TagEngine |
| 3 | Hook 分析实现 | 标签体系 | `video_analysis_model.py` 新增 HookAnalysis |
| 4 | 二创规则实现 | Hook 分析 | `script_library_model.py` 新增 ScriptGenerator |
| 5 | ContentInsight 升级 | 全部以上 | `content_intelligence_agent.py` 新增 InsightEngine V3 |
| 6 | 全量测试 | ContentInsight | 30+ 新测试用例 |

---

## 九、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-21 | Phase 3-3.2 Enhancement 设计：六项增强、八维 ViralScore、三类标签、四型 Hook、A/B 分离、五步二创、四大 Insight |
