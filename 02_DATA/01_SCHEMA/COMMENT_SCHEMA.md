# PV_OS 评论数据 Schema V1.0

> PV_OS 光伏行业 AI 主动获客系统
>
> 用于定义平台评论采集数据结构。
>
> 更新时间：2026-07-14


# 一、目的


本文件定义：

PV_OS 自动采集公开视频评论的数据标准。


支持：

- 抖音
- 快手
- 小红书
- 视频号


主要用途：

1. AI识别潜在客户
2. 建立评论资产库
3. 生成销售线索
4. 支持主动触达


---

# 二、数据来源


来源：


采集对象：

- 一级评论
- 回复评论
- 高互动评论


---

# 三、评论基础字段


|字段|类型|说明|
|-|-|-|
|platform|string|平台名称|
|comment_id|string|评论ID|
|video_id|string|来源视频ID|
|parent_comment_id|string|父评论ID|
|comment_time|datetime|评论时间|
|collector_time|datetime|采集时间|


---

# 四、评论用户字段


|字段|类型|说明|
|-|-|-|
|user_id|string|用户平台ID|
|user_name|string|用户昵称|
|user_url|string|用户主页链接|
|avatar|string|头像地址|
|user_region|string|用户地区信息|


重点字段：


用途：

人工点击进入用户主页：

- 私信
- 添加好友
- 后续销售触达


---

# 五、评论内容字段


|字段|类型|说明|
|-|-|-|
|comment_text|string|评论正文|
|comment_like_count|number|评论点赞|
|reply_count|number|回复数量|
|keyword_tags|array|关键词标签|


---

# 六、AI分析字段


由 comment_analyzer 生成。


|字段|说明|
|-|-|
|intent_type|用户意图|
|customer_need|需求描述|
|region_tag|区域标签|
|house_type|房屋场景|
|purchase_probability|购买概率|
|lead_value|客户价值|


---

# 七、时间价值字段


|字段|说明|
|-|-|
|comment_age_days|评论距离当前天数|
|time_value_level|时间价值等级|


规则：

最近7天：

销售优先。


历史评论：

长期资产保存。


---

# 八、评论分类输出


AI输出：

|等级|处理|
|-|-|
|S|立即销售跟进|
|A|重点培育|
|B|长期运营|
|C|资产保存|


---

# 九、存储位置


原始评论：


分析后：


客户线索：


---

# 十、数据保存原则


所有评论：

永久保存。


原因：

- AI训练
- 用户画像
- 趋势分析
- 二次营销


---

# 十一、版本记录


|版本|日期|说明|
|-|-|-|
|V1.0|2026-07-14|建立评论数据标准|
