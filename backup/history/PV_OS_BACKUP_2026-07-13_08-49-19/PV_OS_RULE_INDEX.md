# PV_OS_RULE_INDEX

版本：
V1.0

日期：
2026-07-12


# 一、系统规则

| 文件 | 路径 | 功能 |
|-|-|-|
| PV_OS_AI_RULES.md | 00_SYSTEM | AI总体运行规则 |
| PV_OS_GOVERNANCE_RULES.md | 00_SYSTEM | 项目治理规则 |


# 二、数据规则


## 区域规则

| 文件 | 路径 | 功能 |
|-|-|-|
| REGION_MATCH_RULE.md | 02_DATA/03_REGION_LIBRARY | 区域匹配 |
| REGION_MASTER.md | 02_DATA/03_REGION_LIBRARY | 区域基础库 |


## 评论规则

| 文件 | 路径 | 功能 |
|-|-|-|
| COMMENT_ANALYZER_RULE.md | 02_DATA/04_COMMENT_DATABASE | 评论客户识别 |
| COMMENT_TIME_AND_MATCH_RULE.md | 02_DATA/04_COMMENT_DATABASE | 
时间资产和区域模糊识别 |
| COMMENT_DATA_LIFECYCLE_RULE.md | 02_DATA/04_COMMENT_DATABASE | 
评论生命周期 |


## 客户评分规则

| 文件 | 路径 | 功能 |
|-|-|-|
| CUSTOMER_SCORE_MODEL.md | 02_DATA/06_SCORE_MODEL | 客户价值评分 |
| CUSTOMER_SCORE_MODEL_V1.0_backup.md | 02_DATA/06_SCORE_MODEL | 历史备份 
|


# 三、CRM规则

| 文件 | 路径 | 功能 |
|-|-|-|
| lead_schema.md | 05_CUSTOMER_CRM/leads | 客户字段标准 |


# 四、AI Agent


| Agent | 文件 | 功能 |
|-|-|-|
| comment_analyzer | agent.yml | 评论分析 |
| lead_scoring_agent | agent.yml | 客户评分 |
| customer_finder_agent | agent.yml | 客户发现 |


# 五、自动化流程


| 文件 | 路径 | 功能 |
|-|-|-|
| comment_to_lead_pipeline.yml | 10_AI_AUTOMATION_ENGINE/workflows | 
评论转客户流程 |
