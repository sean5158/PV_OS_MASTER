# Lead Scoring Agent V2.1

> PV_OS 光伏客户价值评分 Agent。基于 CUSTOMER_SCORE_MODEL.md 五维评分模型。

最后更新：2026-07-13


## 一、Agent 定位

| 项目 | 说明 |
|------|------|
| 名称 | Lead Scoring Agent |
| 版本 | V2.1 |
| 上游 | comment_analyzer（消费其输出） |
| 下游 | 05_CUSTOMER_CRM（输出 lead 到对应目录） |
| 中间层 | 05_CUSTOMER_LEADS（字段映射 + 等级转换） |


## 二、评分逻辑

五维评分（来自 CUSTOMER_SCORE_MODEL.md §2）：

| 维度 | 满分 | 来源 |
|------|:----:|------|
| 安装需求强度 | 40 | §2.2 |
| 区域匹配价值 | 20 | §2.3 |
| 房屋场景价值 | 20 | §2.4 |
| 用户真实性 | 10 | §2.5 |
| 时间价值 | 10 | COMMENT_TIME_AND_MATCH_RULE.md §2.1 |

```
lead_score = demand_score + region_score + housing_score + authenticity_score + time_score
```

## 三、核心输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `lead_score` | integer | 五维评分总分（0-100） |
| `lead_grade` | enum(S/A/B/C) | S≥80 / A 60-79 / B 35-59 / C<35 |
| `crm_target` | string | CRM 入库路径 |
| `follow_up_priority` | enum(high/medium/low) | 销售跟进优先级 |

## 四、CRM 路由

| 等级 | crm_target |
|:----:|-----------|
| S | `05_CUSTOMER_CRM/leads/hot/` |
| A | `05_CUSTOMER_CRM/leads/qualified/` |
| B | `05_CUSTOMER_CRM/leads/qualified/` |
| C | `05_CUSTOMER_CRM/leads/raw/` |

## 五、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-12 | 初始版本（简化评分） |
| V2.0 | 2026-07-13 | 替换为完整五维评分模型 |
| V2.1 | 2026-07-13 | 输出字段精确对齐：lead_score / lead_grade / crm_target / follow_up_priority |
