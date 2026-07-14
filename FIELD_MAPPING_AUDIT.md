# FIELD_MAPPING_AUDIT

版本：V1.0
日期：2026-07-13
用途：审计 comment_analyzer 输出字段与 lead_scoring_agent 输入字段的匹配情况

> 被审计文件：
> - `03_AI_AGENT/agents/comment_analyzer/agent.yml` — 上游输出定义
> - `03_AI_AGENT/agents/lead_scoring_agent/agent.yml` — 下游输入定义（V2.1）
> - `02_DATA/data_dict/comment_schema.md` — 数据标准结构
> - `02_DATA/04_COMMENT_DATABASE/COMMENT_ANALYZER_RULE.md` — 评论分析规则
> - `02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md` — 评分模型
> - `05_CUSTOMER_LEADS/FIELD_MAPPING_RULE.md` — 已有字段映射规则

---

## 一、comment_analyzer 实际输出字段

### 1.1 agent.yml 声明的输出

comment_analyzer 的 agent.yml **未定义完整的 `output.schema`**。仅声明：

```yaml
output:
  path:
    - 05_CUSTOMER_CRM/leads/
```

### 1.2 agent.yml analysis 块声明

```yaml
analysis:
  customer_type: 家庭用户/别墅用户/小商业用户/同行业用户/无关用户
  intent_level:  0 无需求/1 潜在兴趣/2 咨询意向/3 明确购买意向
  score:         0-100
```

仅 3 个维度。**无结构化字段声明**。

### 1.3 从 comment_schema.md 推断的标准结构

comment_analyzer 的 `input.schema` 指向 `comment_schema.md`，该文件定义了完整的评论数据结构：

| 字段 | 类型 | 分类 |
|------|------|------|
| `id` | string | 基础字段 |
| `platform` | string（douyin/xiaohongshu/kuaishou/wechat_video） | 基础字段 |
| `content` | string | 基础字段 |
| `author` | string（脱敏） | 基础字段 |
| `create_time` | datetime | 基础字段 |
| `source_url` | string | 基础字段 |
| `video_title` | string | 内容来源 |
| `video_url` | string | 内容来源 |
| `keyword` | string | 内容来源 |
| `collected_time` | datetime | 内容来源 |
| `sentiment` | string（positive/neutral/negative） | AI分析字段 |
| `customer_intent` | integer（0-3） | AI分析字段 |
| `customer_type` | string | AI分析字段 |
| `score` | integer（0-100） | AI分析字段 |
| `tags` | array | 客户标签 |
| `location` | string | 客户标签 |
| `house_type` | string（普通住宅/别墅/农村自建房/商业建筑/未知） | 客户标签 |
| `processing_status` | string | 数据处理状态 |
| `agent_version` | string | 数据处理状态 |

### 1.4 comment_analyzer 当前真实输出能力总结

| 输出能力 | 声明方式 | 状态 |
|---------|---------|:--:|
| `customer_type` | agent.yml analysis 块 | ✅ 已声明 |
| `intent_level` | agent.yml analysis 块 | ✅ 已声明 |
| `score` | agent.yml analysis 块 | ✅ 已声明 |
| `platform` | 依赖 schema | ⚠️ 透传能力，未声明为输出 |
| `content` | 依赖 schema | ⚠️ 透传能力，未声明为输出 |
| `create_time` | 依赖 schema | ⚠️ 透传能力，未声明为输出 |
| `tags` | 依赖 schema | ⚠️ 生成能力，未声明为输出 |
| `location` | 依赖 schema | ⚠️ 解析能力，未声明为输出 |
| `house_type` | 依赖 schema | ⚠️ 识别能力，未声明为输出 |
| `province` | 无任何声明 | ❌ 未声明 |
| `city` | 无任何声明 | ❌ 未声明 |
| `district` | 无任何声明 | ❌ 未声明 |

---

## 二、lead_scoring_agent 实际输入字段

V2.1 agent.yml 声明的 10 个输入字段：

| # | 字段 | required | 评分维度 |
|:-:|------|:------:|:------:|
| 1 | `source_content` | true | demand + authenticity |
| 2 | `intent_level` | true | demand（辅助） |
| 3 | `province` | true | region |
| 4 | `city` | true | region |
| 5 | `district` | false | region |
| 6 | `housing_type` | true | housing |
| 7 | `customer_type` | true | housing（辅助） |
| 8 | `comment_time` | true | time |
| 9 | `source_platform` | true | CRM 透传 |
| 10 | `tags` | false | CRM 透传 |

上游声明：`upstream: comment_analyzer`，中间层：`intermediate: 05_CUSTOMER_LEADS`。

---

## 三、字段匹配分析

### 3.1 名称完全一致

| lead_scoring_agent 输入 | comment_analyzer/schema 中 | 匹配？ |
|------------------------|--------------------------|:----:|
| `customer_type` | `customer_type` | ✅ |
| `intent_level` | `customer_intent` | ❌ 名称不一致 |
| `tags` | `tags` | ✅ |

### 3.2 名称不一致但功能对应

| lead_scoring_agent 输入 | schema/analyzer 对应 | 差异 |
|------------------------|---------------------|------|
| `source_content` | `content` | 名称不同 |
| `source_platform` | `platform` | 名称不同 |
| `comment_time` | `create_time` | 名称不同 |
| `housing_type` | `house_type` | 名称不同 |
| `intent_level` | `customer_intent` | 名称不同 |

### 3.3 comment_analyzer agent.yml 完全未声明

| lead_scoring_agent 需要 | comment_analyzer 状态 |
|------------------------|---------------------|
| `province` | ❌ agent.yml 无任何声明 |
| `city` | ❌ agent.yml 无任何声明 |
| `district` | ❌ agent.yml 无任何声明 |
| `housing_type` | ❌ agent.yml 未声明输出（规则文件有定义但 agent.yml 缺失） |
| `comment_time` | ❌ agent.yml 未声明输出（规则文件有定义但 agent.yml 缺失） |

---

## 四、缺口汇总

| 严重度 | 数量 | 说明 |
|:------:|:----:|------|
| 🔴 严重 | 5 | province / city / district / housing_type / comment_time 在 comment_analyzer agent.yml 中完全未声明为输出 |
| 🟡 中等 | 5 | source_content↔content / source_platform↔platform / comment_time↔create_time / housing_type↔house_type / intent_level↔customer_intent 字段名不一致 |
| 🟢 轻微 | 1 | comment_analyzer agent.yml 缺少完整 output.schema 定义 |

**核心问题：** comment_analyzer 的 agent.yml 只声明了分析能力（analysis 块的 3 个维度），但没有定义结构化输出 schema。lead_scoring_agent 期望 10 个字段，但 comment_analyzer 实际只声明了 3 个。

---

## 五、字段映射层分析

### 5.1 已有映射规则

`FIELD_MAPPING_RULE.md` 定义了从数据库到 CRM 的字段映射，包含 agent 间映射：

| 来源字段 | 中间字段 | CRM字段 |
|---------|---------|--------|
| comment_text | source_comment | — |
| platform | platform | — |
| comment_time | comment_time | — |
| province | province | location |
| city | city | location |
| district | district | location |
| housing_type | housing_type | house_type |
| total_score | ai_score | lead_score |
| lead_grade | priority | intent_level |

### 5.2 已有映射覆盖情况

FIELD_MAPPING_RULE.md 已覆盖 agent-to-agent 层的部分映射，但缺少明确的 agent 间字段适配说明。

### 5.3 建议补全

方案一：在 comment_analyzer agent.yml 中补全 output.schema

| comment_analyzer 应声明输出 | 字段名 | 对应 lead_scoring_agent 输入 |
|--------------------------|--------|---------------------------|
| 省份 | province | province |
| 城市 | city | city |
| 区县 | district | district |
| 房屋类型 | house_type | housing_type |
| 评论发布时间 | create_time | comment_time |
| 来源平台 | platform | source_platform |
| 原始评论 | content | source_content |
| 意向等级 | customer_intent | intent_level |
| 客户类型 | customer_type | customer_type |
| 客户标签 | tags | tags |
| 客户评分 | score | （透传至 CRM） |

方案二：在 05_CUSTOMER_LEADS 层建立 agent-to-agent 适配映射

```
comment_analyzer 输出              →  lead_scoring_agent 输入
─────────────────────────────────────────────────────────────
content                            →  source_content
platform                           →  source_platform
create_time                        →  comment_time
customer_intent                    →  intent_level
house_type                         →  housing_type
province / city / district         →  名称一致，直接透传
customer_type / tags               →  名称一致，直接透传
```

---

## 六、结论

1. **comment_analyzer agent.yml 没有定义完整的 output.schema**，仅声明了 output.path 和 3 个 analysis 维度
2. **lead_scoring_agent 需要 10 个字段**，其中 5 个（province/city/district/housing_type/comment_time）在 comment_analyzer agent.yml 中完全未声明
3. **5 个字段名称不一致**：content↔source_content、platform↔source_platform、create_time↔comment_time、house_type↔housing_type、customer_intent↔intent_level
4. **FIELD_MAPPING_RULE.md 已覆盖部分映射**，但作为数据库→CRM 层的规则，agent 间适配需在 agent.yml 层面显式声明
5. **推荐方案**：在 comment_analyzer agent.yml 中补全 output.schema，将 province/city/district/housing_type/comment_time/platform/content 显式声明为输出

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-13 | 首次字段映射审计：4 核心文件 + 2 补充文件，识别 5 严重缺口 + 5 名称不一致 |
