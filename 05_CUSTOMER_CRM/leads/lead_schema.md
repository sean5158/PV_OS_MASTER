# PV_OS Lead Schema V1.0

> 光伏行业AI客户线索标准结构

最后更新：2026-07-12


# 一、基础信息

## lead_id

客户线索编号


示例：

PV_LEAD_000001


---

## source_platform

来源平台

示例：

douyin

xiaohongshu

kuaishou

wechat_video


---

## source_content

原始评论内容


---

## source_url

来源链接


---

# 二、客户信息


## customer_type

客户类型：

家庭用户

别墅用户

小商业用户

同行用户

未知


---

## location

地区信息


---

## house_type

房屋类型：

普通住宅

别墅

农村自建房

商业建筑

未知


---

# 三、AI评分


## intent_level

购买意向：

0 无需求

1 潜在兴趣

2 咨询意向

3 明确购买


---

## lead_score

客户评分：

0-100


---

## tags

客户标签


示例：

高意向

价格咨询

储能需求

别墅客户


---

# 四、销售状态


## status

状态：

new

contacted

follow_up

quoted

closed


---

## next_action

下一步动作：

电话联系

发送方案

报价

等待回复


---

# 五、版本记录


|版本|日期|说明|
|-|-|-|
|V1.0|2026-07-12|建立CRM客户线索标准|
