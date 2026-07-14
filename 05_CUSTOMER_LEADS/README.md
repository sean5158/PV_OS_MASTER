# 05_CUSTOMER_LEADS —— PV_OS客户线索出口库

本目录负责承接评论分析后的客户数据。

数据来源：

02_DATA/04_COMMENT_DATABASE/
        ↓
COMMENT_ANALYZER_RULE.md

02_DATA/06_SCORE_MODEL/
        ↓
CUSTOMER_SCORE_MODEL.md


---

## 数据分层


## 1. leads_master.csv

销售主线索库。

进入条件：

- S级客户
- A级客户
- 高价值B级客户


用途：

- 人工回复评论
- 私信沟通
- 加好友
- 电话跟进


---

## 2. nurture_pool.csv

长期培育池。

进入条件：

- B级客户
- 兴趣用户
- 观望用户


用途：

- 内容触达
- 后续培养
- AI再次分析升级


---

## 3. comment_asset_library.csv

评论资产库。

保存：

- 全部历史有效评论
- 7天以前评论
- 30天以前评论
- 长周期需求


用途：

- 关键词优化
- 城市需求分析
- 用户画像
- 竞品研究


核心原则：

7天 = 销售优先窗口

不是：

7天以后删除。


历史评论 = PV_OS长期数据资产。


