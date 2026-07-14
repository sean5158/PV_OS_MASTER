# FIELD_MAPPING_RULE —— PV_OS客户数据字段映射规则 V1.0

> 作用：
>
> 统一评论采集、AI分析、评分模型、客户线索、CRM字段。


---

# 一、数据流向


COMMENT_DATABASE
        ↓

COMMENT_ANALYZER_RULE

        ↓

CUSTOMER_SCORE_MODEL

        ↓

05_CUSTOMER_LEADS

        ↓

05_CUSTOMER_CRM



---

# 二、评论资产 → 客户线索字段


|来源字段|线索字段|说明|
|-|-|-|
|platform|platform|来源平台|
|source_video_id|source_video_id|视频ID|
|source_author|source_author|竞品账号|
|comment_id|comment_id|评论ID|
|comment_text|source_comment|原始评论|
|comment_time|comment_time|评论时间|


---

# 三、AI分析字段映射


|AI分析字段|客户线索字段|CRM字段|
|-|-|-|
|province|province|location|
|city|city|location|
|district|district|location|
|region_confidence|region_confidence|location_confidence|
|housing_type|housing_type|house_type|
|housing_detail|housing_detail|house_detail|
|demand_signals|tags|tags|
|total_score|ai_score|lead_score|
|lead_grade|priority|intent_level|


---

# 四、评分等级转换


## PV_OS等级

|AI等级|CRM意向|
|-|-|
|S|3 明确购买|
|A|2 咨询意向|
|B|1 潜在兴趣|
|C|0 无需求|


---

# 五、时间字段规则


评论时间拆分：


## 销售时间

字段：

comment_recency


用途：

判断是否立即跟进。


## 数据资产时间

字段：

asset_age_days


用途：

历史评论分析。


原则：

7天以内：

销售优先。


7天以后：

继续保存，进入资产库。


---

# 六、客户标签规则


tags 自动生成：


示例：


---

# 七、状态映射


|线索状态|CRM状态|
|-|-|
|new|new|
|contacted|contacted|
|follow_up|follow_up|
|quoted|quoted|
|closed|closed|


---

# 八、版本记录


|版本|日期|说明|
|-|-|-|
|V1.0|2026-07-12|建立客户数据字段统一映射|

