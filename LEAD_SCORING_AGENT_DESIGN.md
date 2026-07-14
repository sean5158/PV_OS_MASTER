# LEAD_SCORING_AGENT_DESIGN

版本：V2.1
日期：2026-07-13
用途：PV_OS 客户价值评分 Agent（lead_scoring_agent）完整设计文档。

> 设计依据（仅引用已有固化规则）：
> - `02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md` — 评分模型源文件
> - `02_DATA/04_COMMENT_DATABASE/COMMENT_ANALYZER_RULE.md` — 上游输入规则
> - `05_CUSTOMER_CRM/leads/lead_schema.md` — CRM 目标结构
> - `05_CUSTOMER_LEADS/FIELD_MAPPING_RULE.md` — 字段映射规则
> - `backup/PV_OS_BACKUP_MAP_V1.0.md` — CRM 目录结构
> - `03_AI_AGENT/agents/lead_scoring_agent/agent.yml` — 现有配置
>
> 原则：不自行创造评分规则。所有逻辑均来自已有固化文件。
>
> V2.1 更新：所有测试案例增加完整计算过程（公式线）；测试分区重组为"主要测试（城市小区）"与"边界测试（农村/低价值/信息不足）"。

---

## 一、Agent 定位

### 1.1 在 PV_OS 中的作用

Lead Scoring Agent 是 PV_OS 客户价值评分的核心 Agent。其上游是 `comment_analyzer`（评论分析与客户识别），下游是 `05_CUSTOMER_CRM`（客户关系管理）。

```
竞品评论区采集
    ↓
comment_analyzer（评论分析 + 客户识别）
    ↓ 输出：customer_type / intent_level / tags / location / housing_type / comment_time
lead_scoring_agent（本 Agent）★
    ↓ 输出：total_score / lead_grade / 五维得分 / urgency / routing
05_CUSTOMER_LEADS（中间层：字段映射 + 等级转换）
    ↓
05_CUSTOMER_CRM（入库）
    ├── leads/hot/       ← S 级（≥80）
    ├── leads/qualified/ ← A 级（60-79）+ B 级（35-59）
    ├── leads/raw/       ← C 级（<35）
    ├── follow_ups/      ← 销售跟进后
    └── customers/       ← 成交后
```

### 1.2 职责清单

| 职责 | 说明 | 来源 |
|------|------|------|
| 接收上游输出 | 消费 comment_analyzer 的完整分析结果 | 现有 agent.yml |
| 执行五维评分 | 严格按 CUSTOMER_SCORE_MODEL.md §2.1 打分 | `CUSTOMER_SCORE_MODEL.md` |
| 判定 S/A/B/C | S≥80 / A 60-79 / B 35-59 / C<35 | `CUSTOMER_SCORE_MODEL.md` §2.1 |
| 生成 CRM 路由 | S→hot / A,B→qualified / C→raw | 现有 agent.yml routing |
| 输出 urgency | high / medium / low | 现有 agent.yml output |
| 标记 contact_intent | 是否值得立即联系 | 现有 agent.yml output |

---

## 二、输入数据结构

### 2.1 上游来源

Lead Scoring Agent 的输入全部来自 `comment_analyzer` 的输出：

| 输入字段 | 类型 | 说明 | 来源 |
|---------|------|------|------|
| `customer_type` | string | 家庭用户/别墅用户/小商业用户/同行业用户/无关用户 | comment_analyzer agent.yml |
| `intent_level` | integer(0-3) | 0=无需求/1=潜在兴趣/2=咨询意向/3=明确购买 | comment_analyzer agent.yml |
| `source_platform` | string | douyin/xiaohongshu/kuaishou/wechat_video | agent.yml |
| `source_content` | string | 原始评论内容 | agent.yml |
| `tags` | array | comment_analyzer 生成的客户标签 | agent.yml |
| `province` | string | 省份 | FIELD_MAPPING_RULE.md §三 |
| `city` | string | 城市 | FIELD_MAPPING_RULE.md §三 |
| `district` | string | 区县 | FIELD_MAPPING_RULE.md §三 |
| `housing_type` | string | 普通住宅/别墅/农村自建房/商业建筑/未知 | FIELD_MAPPING_RULE.md §三 |
| `comment_time` | datetime | 评论发布时间 | COMMENT_TIME_AND_MATCH_RULE.md §2.1 |

> 当前 agent.yml 的 input.fields 仅列出前 5 个字段。为实现完整五维评分，需扩展 input.fields 至 10 个字段。

### 2.2 各字段在评分中的用途

| 字段 | 评分维度 | 用法 |
|------|:------:|------|
| `source_content` | 需求强度 + 真实性 | 关键词匹配 + 自然度分析 |
| `province`/`city`/`district` | 区域匹配价值 | 对照川渝黔区域分值表 |
| `housing_type` | 房屋场景价值 | 对照房屋场景分值表（20/18/15/12/10/5） |
| `comment_time` | 时间价值 | 计算距当前时间的差值 |
| `customer_type` | 房屋场景价值（辅助） | 当 housing_type 为"未知"时作为备用判断依据 |
| `intent_level` | 需求强度（辅助） | 参考上游的初步意向判断 |

---

## 三、评分流程

严格依据 `CUSTOMER_SCORE_MODEL.md` 第二章。

### 3.1 五维评分总览

| 维度 | 满分 | 权重 | 核心问题 | 来源 |
|------|:----:|:----:|---------|------|
| 安装需求强度 | **40** | 40% | 用户有多想装光伏？ | §2.2 |
| 区域匹配价值 | **20** | 20% | 用户在不在川渝黔核心市场？ | §2.3 |
| 房屋场景价值 | **20** | 20% | 用户住别墅还是普通住宅？ | §2.4 |
| 用户真实性 | **10** | 10% | 这是真人还是机器人？ | §2.5 |
| 时间价值 | **10** | 10% | 评论是最近的吗？ | `COMMENT_TIME_AND_MATCH_RULE.md` §2.1 |

### 3.2 维度一：安装需求强度（0-40 分）

来自 `CUSTOMER_SCORE_MODEL.md` §2.2。

| 分数 | 等级 | 判断标准 | 关键词示例 |
|:----:|------|---------|-----------|
| 40 | 极强需求 | 想安装 / 要求报价 / 要求上门测量 / 询问施工时间 | 想装、报价、上门、什么时候装 |
| 30 | 强需求 | 询问多少钱 / 询问安装流程 | 多少钱、价格、怎么装、安装流程 |
| 20 | 明确兴趣 | 询问效果 / 询问发电量 | 效果怎么样、发电多少、好用吗 |
| 10 | 普通了解 | 一般性了解，无明确购买信号 | 了解下、看看 |
| 0 | 无需求 | 与光伏安装无关 | — |

**叠加规则：** 同时命中多个分数段时**取最高分**。

**负向修正（来自 §2.2）：**

| 类型 | 关键词 | 修正 |
|------|--------|:----:|
| 免费安装期待 | 免费装、免费安装、不花钱装、国家免费装 | **-25** |
| 政策等待 | 政府什么时候装、国家项目、政策下来了吗 | **-20** |
| 补贴咨询 | 有没有补贴、补贴多少钱、政府补助 | **-15** |
| 观望型 | 了解一下、看看政策、以后再说 | **-10** |

规则：若**仅有**免费/政策信号而没有购买行为 → 需求强度最高不超过 10 分。

### 3.3 维度二：区域匹配价值（0-20 分）

来自 `CUSTOMER_SCORE_MODEL.md` §2.3 + `REGION_MATCH_RULE.md` §五。

| 分值 | 省份 | 区域 |
|:----:|------|------|
| 20 | 四川 | 成都核心区（锦江/青羊/金牛/武侯/成华/高新区/天府新区） |
| 18 | 四川 | 成都外围区（龙泉驿/青白江/新都/温江/双流/郫都） |
| 18 | 重庆 | 重庆核心区（渝中/江北/南岸/沙坪坝/九龙坡/大渡口/渝北/巴南） |
| 16 | 四川 | 成都郊县 |
| 15 | 四川 | 四川主要城市（绵阳/德阳/宜宾/南充/泸州） |
| 15 | 重庆 | 重庆外围区 |
| 15 | 贵州 | 贵阳核心区（南明/云岩/花溪/乌当/白云/观山湖） |
| 13 | 四川 | 四川其余城市 |
| 13 | 贵州 | 贵州重点城市（遵义/毕节/安顺） |
| 10 | — | 贵州其余 + 省级未知城市 |
| 0 | — | 区域未知 |

### 3.4 维度三：房屋场景价值（0-20 分）

来自 `CUSTOMER_SCORE_MODEL.md` §2.4。

| 分值 | 场景 |
|:----:|------|
| 20 | 别墅 |
| 18 | 叠拼 / 阳光房 / 露台 |
| 15 | 大平层 / 花园洋房 |
| 12 | 自建房（农村） |
| 10 | 普通住宅顶楼 |
| 5 | 普通住宅 |

多场景匹配时取最高分。`housing_type` 为"未知"时尝试从 `source_content` 关键词推断。

### 3.5 维度四：用户真实性（0-10 分）

来自 `CUSTOMER_SCORE_MODEL.md` §1.2（细则见 §2.5）。

| 分数区间 | 判定 |
|:------:|------|
| 8-10 | 真实用户：评论内容自然，有个人表达 |
| 4-7 | 可疑用户：内容模板化、营销口吻 |
| 0-3 | 机器人/水军/同行试探：纯广告、纯专业术语无购买意愿 |

### 3.6 维度五：时间价值（0-10 分）

来自 `COMMENT_TIME_AND_MATCH_RULE.md` §2.1。

| 分值 | 时间范围 |
|:----:|---------|
| 10 | 1 小时以内 |
| 9 | 1-24 小时 |
| 7 | 1-7 天 |
| 5 | 7-30 天 |
| 3 | 30-90 天 |
| 1 | 90-180 天 |
| 0 | 超过 180 天 |

### 3.7 统一计算公式

```
total_score = demand_score + region_score + housing_score + authenticity_score + time_score
lead_grade  = S(≥80) / A(60-79) / B(35-59) / C(<35)
```

---

## 四、S/A/B/C 输出规则

以下阈值全部来自 `CUSTOMER_SCORE_MODEL.md` §2.1，不自行创造。

### 4.1 等级定义

| 等级 | 分数阈值 | 业务含义 | CRM 动作 |
|:----:|:--------:|---------|---------|
| **S** | **≥ 80** | 高价值客户：需求强 + 核心区域 + 高价值房屋 | 立即人工跟进 → hot/ |
| **A** | **60-79** | 优质客户：有明确兴趣 + 匹配区域 | 重点培育 → qualified/ |
| **B** | **35-59** | 潜在客户：有兴趣但条件未完全匹配 | 长期运营 → qualified/ |
| **C** | **< 35** | 低优先级：无明确需求或不匹配 | 分析保存 → raw/ |

### 4.2 urgency 判定

| urgency | 条件 |
|:------:|------|
| high | 需求强度 ≥ 30 **且** 时间价值 ≥ 7 |
| medium | 需求强度 ≥ 20 **或** 时间价值 ≥ 5 |
| low | 其余情况 |

### 4.3 contact_intent 判定

| 值 | 条件 |
|:--:|------|
| true | 需求强度 ≥ 30 |
| false | 需求强度 < 30 |

---

## 五、CRM 映射

### 5.1 CRM 目录结构

来自 `backup/PV_OS_BACKUP_MAP_V1.0.md`：

```
05_CUSTOMER_CRM/
├── leads/
│   ├── raw/          ← C 级（< 35），仅存档分析
│   ├── qualified/    ← A 级（60-79）+ B 级（35-59），培育+运营
│   └── hot/          ← S 级（≥ 80），立即跟进
├── customers/        ← 已成交客户（status: closed）
├── follow_ups/       ← 跟进记录（status: contacted / follow_up / quoted）
└── funnel/           ← 漏斗分析数据
```

### 5.2 评分结果路由

| 等级 | 分数 | 路径 | 初始 status | next_action |
|:----:|:----:|------|:----------:|------------|
| S | ≥80 | `leads/hot/` | new | 电话联系 |
| A | 60-79 | `leads/qualified/` | new | 发送方案 |
| B | 35-59 | `leads/qualified/` | new | 等待回复 |
| C | <35 | `leads/raw/` | new | 等待回复 |

### 5.3 从 leads 到 customers 的完整流转

```
leads/{hot,qualified,raw}/
    │ status: new
    ↓ 销售首次触达
    │ status: contacted → 记录到 follow_ups/
    ↓ 客户回复
    │ status: follow_up → 追加到 follow_ups/
    ↓ 发送报价
    │ status: quoted → 更新 follow_ups/
    ↓ 签约成交
    │ status: closed → 迁移到 customers/ + 写入反馈数据
    ↓
customers/  → 反馈数据用于反向优化 AI 评分（§六）
```

### 5.4 字段映射

来自 `FIELD_MAPPING_RULE.md` §三-§四 和 `lead_schema.md`：

| Agent 输出 | CRM 字段 | 说明 |
|-----------|---------|------|
| `lead_id` | `lead_id` | 唯一编号 |
| `platform` | `source_platform` | 来源平台 |
| `comment_text` | `source_content` | 原始评论 |
| `province`/`city`/`district` | `location` | 地区信息 |
| `customer_type` | `customer_type` | 客户类型 |
| `housing_type` | `house_type` | 房屋类型 |
| `demand_signals` | `tags` | 客户标签 |
| `total_score` | `lead_score` | AI 评分 0-100 |
| `lead_grade` → 转换 | `intent_level` | S→3 / A→2 / B→1 / C→0 |

---

## 六、与 comment_analyzer 的连接关系

### 6.1 连接架构

```
comment_analyzer                          lead_scoring_agent
┌──────────────────────┐                ┌──────────────────────┐
│ 输入：02_DATA/raw/    │                │ 输入：上游输出对象     │
│                      │                │                      │
│ 输出：               │───────────────→│ 处理：               │
│  - customer_type     │  10 个字段      │  五维评分 → 等级判定  │
│  - intent_level      │                │                      │
│  - tags              │                │ 输出：               │
│  - location          │                │  total_score + grade  │
│  - housing_type      │                │  + routing           │
│  - comment_time      │                │                      │
│  - source_content    │                └──────────┬───────────┘
│  - source_platform   │                           │
└──────────────────────┘                           ↓
                                        05_CUSTOMER_LEADS
                                        （字段映射 + 等级转换）
                                                  ↓
                                        05_CUSTOMER_CRM
```

### 6.2 数据协议

comment_analyzer 必须向 lead_scoring_agent 提供：

| 字段 | 必要性 | 用途 |
|------|:------:|------|
| `source_content` | **必须** | 需求强度关键词匹配 + 真实性分析 |
| `province`/`city`/`district` | **必须** | 区域分值匹配 |
| `housing_type` | **必须** | 房屋场景分值匹配 |
| `comment_time` | **必须** | 时间价值计算 |
| `customer_type` | **必须** | 辅助房屋场景判断 + CRM |
| `intent_level` | **必须** | 辅助需求强度判断 |
| `source_platform` | **必须** | CRM 溯源 |
| `tags` | 建议 | CRM 客户标签 |
| `source_url` | 建议 | CRM 追溯 |

---

## 七、测试方案

### 7.1 测试结构

```
┌─────────────────────────────────────────┐
│ 主要测试：城市小区光伏客户（案例 1-4）    │
│ - 高价值城市客户（案例 1、2）            │
│ - 普通城市客户（案例 3、4）              │
├─────────────────────────────────────────┤
│ 边界测试：非典型场景（案例 5-7）          │
│ - 农村客户（案例 5）                     │
│ - 低价值需求（案例 6）                   │
│ - 信息不足客户（案例 7）                 │
└─────────────────────────────────────────┘
```

### 7.2 主要测试：城市小区光伏客户

#### 案例 1：成都别墅 — 高价值城市客户 S 级

```
输入：
  source_content: "成都锦江区别墅，想装一套光伏，大概多少钱？能上门看看吗？"
  customer_type: "别墅用户"
  housing_type: "别墅"
  province: "四川"  city: "成都"  district: "锦江区"
  comment_time: "2026-07-13 10:00"（0.5 小时前）

评分过程：
  需求强度：
    - 命中关键词："想装"(40分) + "多少钱"(30分) + "上门"(40分)
    - 叠加规则：取最高分 → 40
    - 无负向修正信号 → 最终 demand_score = 40
  区域价值：成都核心区 + 锦江区明确 → region_score = 20
  房屋场景：别墅 → housing_score = 20
  真实性：真实个人表达，有具体场景和需求 → authenticity_score = 10
  时间价值：0.5 小时前 → time_score = 10

计算：
  total_score = 40 + 20 + 20 + 10 + 10 = 100

结果：
  lead_grade: S
  contact_intent: true
  urgency: high（需求 40 ≥ 30 且 时间 10 ≥ 7）
  routing: 05_CUSTOMER_CRM/leads/hot/
  next_action: 电话联系
```

#### 案例 2：重庆叠拼 — 高价值城市客户 A 级

```
输入：
  source_content: "重庆渝北叠拼，装光伏效果怎么样？发电够用吗？"
  customer_type: "别墅用户"
  housing_type: "叠拼"
  province: "重庆"  city: "重庆"  district: "渝北区"
  comment_time: "2026-07-12 15:00"（1 天前）

评分过程：
  需求强度：
    - 命中关键词："效果怎么样"(20分) + "发电"(20分)
    - 叠加规则：取最高分 → 20
    - 无负向修正信号 → 最终 demand_score = 20
  区域价值：重庆核心区 + 渝北区明确 → region_score = 18
  房屋场景：叠拼 → housing_score = 18
  真实性：真实个人表达 → authenticity_score = 10
  时间价值：1 天前 → time_score = 9

计算：
  total_score = 20 + 18 + 18 + 10 + 9 = 75

结果：
  lead_grade: A
  contact_intent: false（需求 20 < 30）
  urgency: medium（时间 9 ≥ 5）
  routing: 05_CUSTOMER_CRM/leads/qualified/
  next_action: 发送方案
```

#### 案例 3：成都大平层 — 普通城市客户 S 级

```
输入：
  source_content: "成都高新区大平层，安装光伏需要什么流程？大概多久装好？"
  customer_type: "家庭用户"
  housing_type: "大平层"
  province: "四川"  city: "成都"  district: "高新区"
  comment_time: "2026-07-10 08:00"（3 天前）

评分过程：
  需求强度：
    - 命中关键词："安装流程"(30分) + "多久装好"(施工时间，40分)
    - 叠加规则：取最高分 → 40
    - 无负向修正信号 → 最终 demand_score = 40
  区域价值：成都核心区 + 高新区明确 → region_score = 20
  房屋场景：大平层/花园洋房 → housing_score = 15
  真实性：真实个人表达 → authenticity_score = 10
  时间价值：3 天前 → time_score = 7

计算：
  total_score = 40 + 20 + 15 + 10 + 7 = 92

结果：
  lead_grade: S
  contact_intent: true（需求 40 ≥ 30）
  urgency: high（需求 40 ≥ 30 且 时间 7 ≥ 7）
  routing: 05_CUSTOMER_CRM/leads/hot/
  next_action: 电话联系
```

#### 案例 4：贵阳普通住宅 — 普通城市客户 B 级

```
输入：
  source_content: "贵阳观山湖普通住宅能装光伏吗？想了解一下。"
  customer_type: "家庭用户"
  housing_type: "普通住宅"
  province: "贵州"  city: "贵阳"  district: "观山湖区"
  comment_time: "2026-07-06 12:00"（7 天前）

评分过程：
  需求强度：
    - 命中关键词："能装"(询问安装条件，20分) + "了解一下"(观望型)
    - 叠加规则：取最高分 → 20
    - 负向修正："了解一下"触发观望型 → -10
    - 最终 demand_score = 20 - 10 = 10
  区域价值：贵阳核心区 + 观山湖区明确 → region_score = 15
  房屋场景：普通住宅 → housing_score = 5
  真实性：真实询问，但"了解一下"削弱意图 → authenticity_score = 8
  时间价值：7 天前 → time_score = 7

计算：
  total_score = 10 + 15 + 5 + 8 + 7 = 45

结果：
  lead_grade: B
  contact_intent: false（需求 10 < 30）
  urgency: low（需求 10 < 20，时间 7 ≥ 5 但需求不足）
  routing: 05_CUSTOMER_CRM/leads/qualified/
  next_action: 等待回复
```

### 7.3 边界测试：非典型场景

#### 案例 5（边界）：农村免费政策等待 — 低价值 B 级

```
输入：
  source_content: "农村免费安装光伏什么时候开始？政府有补贴吗？"
  customer_type: "家庭用户"
  housing_type: "农村自建房"
  province: "四川"  city: "unknown"  district: "unknown"
  comment_time: "2026-06-15 10:00"（28 天前）

评分过程：
  需求强度：
    - 命中关键词："免费安装"(免费期待) + "补贴"(补贴咨询)
    - 叠加规则：无购买行为关键词 → 取最高 0
    - 负向修正：免费安装期待(-25) + 补贴咨询(-15) → 但需求基数为 0
    - 规则：仅有免费/政策信号无购买行为 → demand_score 最高不超过 10
    - 判定：无任何购买意向表达 → demand_score = 0
  区域价值：省级未知城市（四川 but 城市未知） → region_score = 10
  房屋场景：自建房(农村) → housing_score = 12
  真实性：真实询问 → authenticity_score = 10
  时间价值：28 天前 → time_score = 5

计算：
  total_score = 0 + 10 + 12 + 10 + 5 = 37

结果：
  lead_grade: B
  contact_intent: false
  urgency: low
  routing: 05_CUSTOMER_CRM/leads/qualified/
  tags 追加: [政策型用户]
  说明：虽总分达 B 级（因区域+房屋仍有基础分），但需在 tags 中标记为"政策型用户"，
        在销售流程中降低人工跟进优先级，区别于有真实购买意向的 B 级客户。
```

#### 案例 6（边界）：无光伏需求评论 — 低价值 C 级

```
输入：
  source_content: "这个视频拍得不错"
  customer_type: "未知"
  housing_type: "未知"
  province: "unknown"  city: "unknown"  district: "unknown"
  comment_time: "2026-07-01 08:00"（12 天前）

评分过程：
  需求强度：
    - 未命中任何需求关键词 → demand_score = 0
  区域价值：区域完全未知 → region_score = 0
  房屋场景：未知 → housing_score = 0
  真实性：普通表达，非广告/水军 → authenticity_score = 10
  时间价值：12 天前 → time_score = 5

计算：
  total_score = 0 + 0 + 0 + 10 + 5 = 15

结果：
  lead_grade: C
  contact_intent: false
  urgency: low
  routing: 05_CUSTOMER_CRM/leads/raw/
```

#### 案例 7（边界）：信息不足 — 仅区域无房屋 B 级

```
输入：
  source_content: "成都有安装光伏的吗？"
  customer_type: "未知"
  housing_type: "未知"
  province: "四川"  city: "成都"  district: "unknown"
  comment_time: "2026-07-08 14:00"（5 天前）

评分过程：
  需求强度：
    - 命中关键词："有安装XX的吗" → 询问安装条件，视为潜在兴趣
    - 叠加规则 → 20
    - 无负向修正 → demand_score = 20
  区域价值：成都城市级明确（区县未知） → region_score = 18
  房屋场景：未知，source_content 无法推断 → housing_score = 0
  真实性：真实询问 → authenticity_score = 10
  时间价值：5 天前 → time_score = 7

计算：
  total_score = 20 + 18 + 0 + 10 + 7 = 55

结果：
  lead_grade: B
  contact_intent: false（需求 20 < 30）
  urgency: medium（时间 7 ≥ 5）
  routing: 05_CUSTOMER_CRM/leads/qualified/
  说明：信息不足（缺房屋类型导致 housing_score=0），进入 qualified/ 培育池。
        如后续 comment_analyzer 能补充 housing_type，可重新评分。
```

### 7.4 测试覆盖总结

**主要测试（城市小区客户）：**

| 类型 | 案例 | demand | region | housing | auth | time | 总分 | 等级 | routing |
|------|:--:|:------:|:------:|:-------:|:----:|:----:|:----:|:----:|---------|
| 高价值城市 | 案例 1（成都别墅+S+上门） | 40 | 20 | 20 | 10 | 10 | **100** | **S** | hot/ |
| 高价值城市 | 案例 2（重庆叠拼+效果） | 20 | 18 | 18 | 10 | 9 | **75** | **A** | qualified/ |
| 普通城市 | 案例 3（成都大平层+流程） | 40 | 20 | 15 | 10 | 7 | **92** | **S** | hot/ |
| 普通城市 | 案例 4（贵阳普通住宅+了解） | 10 | 15 | 5 | 8 | 7 | **45** | **B** | qualified/ |

**边界测试（非典型场景）：**

| 类型 | 案例 | demand | region | housing | auth | time | 总分 | 等级 | routing |
|------|:--:|:------:|:------:|:-------:|:----:|:----:|:----:|:----:|---------|
| 农村客户 | 案例 5（免费政策等待） | 0 | 10 | 12 | 10 | 5 | **37** | **B** | qualified/ |
| 低价值 | 案例 6（无光伏评论） | 0 | 0 | 0 | 10 | 5 | **15** | **C** | raw/ |
| 信息不足 | 案例 7（仅区域无房屋） | 20 | 18 | 0 | 10 | 7 | **55** | **B** | qualified/ |

---

## 八、与现有 agent.yml 的差异

| 差异项 | 现有 agent.yml | 设计目标 | 建议 |
|--------|:------------:|:------:|------|
| 评分逻辑 | intent(40/30/15)+type(20/20/10)+keyword(10/15/10) | 五维评分（需求/区域/房屋/真实性/时间） | 替换 |
| 区域维度 | 无 | CUSTOMER_SCORE_MODEL §2.3 的 12 行区域表 | 新增 |
| 时间维度 | 无 | COMMENT_TIME_AND_MATCH_RULE §2.1 的 7 档 | 新增 |
| 真实性维度 | 无 | CUSTOMER_SCORE_MODEL §2.5 | 新增 |
| 路由阈值 | 50-79 qualified / 0-49 raw | A 60-79 / B 35-59 / C<35 | 对齐 |
| 输入字段 | 5 个 | 10 个 | 扩展 |

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-13 | 初始设计：7 章节 + 7 测试案例 |
| V2.0 | 2026-07-13 | 增强 CRM 完整流转（customers/follow_ups）、重组测试为 4 种覆盖类型 |
| V2.1 | 2026-07-13 | 所有案例增加完整【评分过程→计算→结果】三步展开；测试分区重组为"主要测试（城市小区）"与"边界测试（农村/低价值/信息不足）" |

