# PV_OS 用户画像数据 Schema V1.0

> PV_OS 光伏行业 AI 主动获客系统
>
> 用于定义评论用户数据结构。
>
> 更新时间：2026-07-14


# 一、目的


本文件定义：

PV_OS 从公开视频评论区发现用户后，
采集、保存、分析用户基础信息的数据标准。


核心目标：

通过 AI 判断用户价值，
并保留人工主动触达入口。


---

# 二、数据来源


来源：

- 抖音用户
- 快手用户
- 小红书用户
- 视频号用户


来源路径：


---

# 三、用户基础字段


|字段|类型|说明|
|-|-|-|
|platform|string|平台名称|
|user_id|string|平台用户唯一ID|
|user_name|string|用户昵称|
|user_url|string|用户主页链接|
|avatar_url|string|头像地址|
|collect_time|datetime|采集时间|


---

# 四、平台触达字段


|字段|说明|
|-|-|
|profile_url|用户主页访问链接|
|message_available|是否支持私信|
|follow_status|关注状态|
|contact_status|触达状态|


重点：


用途：

销售人员点击：

↓

进入平台用户主页

↓

人工私信

↓

建立联系


---

# 五、用户公开信息字段


|字段|类型|说明|
|-|-|-|
|bio|string|个人简介|
|location|string|公开地区|
|ip_region|string|公开IP属地|
|verified|boolean|认证状态|
|fans_count|number|粉丝数量|
|following_count|number|关注数量|


---

# 六、用户行为字段


|字段|说明|
|-|-|
|comment_count|评论次数|
|related_video_count|相关视频数量|
|interaction_level|互动程度|
|active_score|活跃评分|


---

# 七、AI用户分析字段


由 AI Agent 生成。


|字段|说明|
|-|-|
|customer_type|客户类型|
|intent_level|购买意向|
|region_tag|区域标签|
|house_scene|房屋场景|
|customer_score|客户评分|
|lead_grade|S/A/B/C等级|


---

# 八、用户价值判断


## 高价值信号


包括：

- 主动询价
- 询问安装条件
- 询问价格
- 要求联系方式
- 请求上门


处理：

进入销售线索库。


---

## 培育信号


包括：

- 关注案例
- 询问效果
- 了解方案


处理：

进入培育池。


---

## 低价值信号


包括：

- 免费安装期待
- 单纯政策询问
- 无购买意图互动


处理：

降低评分。


---

# 九、存储位置


原始用户数据：


处理后：


销售线索：


---

# 十、数据关系


关系：
|

||

||

|

---

# 十一、数据保存原则


用户数据长期保存。


原因：

- 客户资产积累
- 二次营销
- AI模型优化
- 用户画像


---

# 十二、版本记录


|版本|日期|说明|
|-|-|-|
|V1.0|2026-07-14|建立用户画像数据标准|
