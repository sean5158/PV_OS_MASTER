# Competitor Account Agent — README

版本：V1.0 | 日期：2026-07-20
Agent 定义：`agent.yml` V1.1

## 定位

PV_OS 竞品账号智能发现 Agent。全国发现光伏相关账号，判断其是否具有川渝黔家庭光伏客户来源价值。

```
competitor_accounts.csv → competitor_account_agent → Pipeline analyze_source_account
```

## 文件结构

| 文件 | 用途 |
|------|------|
| `agent.yml` | Agent 定义 (V1.1) |
| `README.md` | 本文件 |

## Pipeline 接入 (P1-3)

`analyze_source_account` 步骤 (step 2/10) 已注册 handler：

- **CSV 精确匹配**：按 `platform|account_id` 查找竞品主表
- **CSV 名称匹配**：按 `name|account_name` 模糊查找
- **启发式分析**：基于账号名+视频标题推断分类和评分

输出字段：`account_category`, `account_authority_score`, `customer_source_score`, `monitor_level`

## 账号分类

| 类型 | 名称 | 优先级 |
|------|------|:--:|
| A | 个人光伏内容博主 | 最高 |
| B | 光伏企业/品牌/安装公司 | 高 |
| C | 行业媒体/科普账号 | 中 |
| D | 无法判断/无价值 | 低 |

## 评分维度

| 维度 | 权重 | 说明 |
|------|:--:|------|
| 区域评论信号 | 40% | 川渝黔地名出现频率 |
| 客户意向信号 | 30% | 询价/联系/安装意愿 |
| 房屋场景信号 | 20% | 别墅/叠拼/阳光房 |
| 账号活跃度 | 10% | 平台+内容匹配度 |

## 当前状态

- ✅ Agent 定义 (agent.yml V1.1)
- ✅ Pipeline 接入 (P1-3)
- ✅ CSV 精确/名称匹配
- ✅ 启发式分类+评分
- ⬜ 竞品主表填充真实账号（P2）

## 设计文档

- `02_DATA/02_COMPETITOR_DATABASE/COMPETITOR_ACCOUNT_MODEL.md` V2.0
- `02_DATA/02_COMPETITOR_DATABASE/COMPETITOR_SCORE_RULE.md`
- `02_DATA/02_COMPETITOR_DATABASE/COMPETITOR_DISCOVERY_ALGORITHM.md`
- `PV_OS_COMPETITOR_ACCOUNT_MODEL.md` V1.0
