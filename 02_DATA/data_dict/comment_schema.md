# Comment Data Schema V1.0

> PV_OS 评论数据标准结构
> 用于抖音、小红书、快手、视频号评论数据统一格式
> 最后更新：2026-07-12

---

# 一、基础字段

## id

说明：

评论唯一编号。

格式：

平台_编号

示例：

douyin_000001


---

## platform

说明：

来源平台。

允许值：

douyin

xiaohongshu

kuaishou

wechat_video


---

## content

说明：

用户评论原始内容。


---

## author

说明：

用户昵称（脱敏）。

规则：

- 不保存真实身份信息
- 不保存手机号
- 不保存私人联系方式


---

## create_time

说明：

评论发布时间。

格式：

YYYY-MM-DD HH:MM:SS


---

## source_url

说明：

原始内容链接。

用途：

- 数据追踪
- 人工复核


---

# 二、内容来源字段

## video_title

说明：

评论对应的视频标题。


---

## video_url

说明：

视频原始链接。


---

## keyword

说明：

触发采集的关键词。

示例：

家庭光伏

别墅光伏

太阳能发电

光伏储能

屋顶发电


---

## collected_time

说明：

数据采集时间。

格式：

YYYY-MM-DD HH:MM:SS


---

# 三、AI分析字段

## sentiment

说明：

评论情绪分析。

类型：

positive

neutral

negative


---

## customer_intent

说明：

客户购买意向等级。


等级：

0 = 无需求

1 = 潜在兴趣

2 = 咨询意向

3 = 明确购买意向


判断：

0：

普通浏览，无购买信息。


1：

了解光伏，询问基础知识。


2：

询问价格、安装流程、收益。


3：

准备安装、要求报价、咨询联系方式。


---

## customer_type

说明：

客户类型。


分类：

家庭用户

别墅用户

小商业用户

同行用户

无关用户


---

## score

说明：

客户价值评分。


范围：

0-100


评分因素：

- 购买意向
- 评论关键词
- 地区信息
- 房屋类型
- 预算可能性
- 互动行为


---

# 四、客户标签字段

## tags

说明：

AI生成客户标签。


示例：

高意向

别墅客户

价格敏感

储能需求


---

## location

说明：

用户公开地区信息。


规则：

只保存公开信息，不推测私人地址。


---

## house_type

说明：

房屋类型。


分类：

普通住宅

别墅

农村自建房

商业建筑

未知


---

# 五、数据处理状态

## processing_status

说明：

数据处理流程状态。


状态：

raw

cleaned

analyzed

exported


---

## agent_version

说明：

AI分析Agent版本。


示例：

comment_analyzer_v1.0


---

# 六、数据流程

原始数据：

02_DATA/raw/


清洗数据：

02_DATA/processed/


AI分析：

03_AI_AGENT/agents/comment_analyzer/


客户线索：

05_CUSTOMER_CRM/leads/


---

# 七、数据示例

{
"id":"douyin_000001",
"platform":"douyin",
"content":"安装光伏多少钱？",
"customer_intent":2,
"customer_type":"家庭用户",
"score":75,
"tags":["价格咨询","潜在客户"]
}


---

# 八、版本记录

|版本|日期|说明|
|-|-|-|
|V1.0|2026-07-12|建立PV_OS评论数据标准结构|
