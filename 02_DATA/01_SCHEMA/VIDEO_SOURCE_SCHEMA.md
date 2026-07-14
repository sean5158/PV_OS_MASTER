# PV_OS 视频来源数据 Schema V1.0

> PV_OS 光伏行业 AI 主动获客系统
>
> 用于定义视频平台采集数据结构。
>
> 更新时间：2026-07-14


# 一、目的

本文件定义：

PV_OS 从公开视频平台采集的视频基础数据字段。


支持：

- 抖音
- 快手
- 小红书
- 视频号


数据用途：

1. 发现高价值行业内容
2. 发现潜在客户评论入口
3. 分析竞品账号
4. 支撑 AI 客户识别


---

# 二、数据来源


平台：

- Douyin
- Kuaishou
- Xiaohongshu
- WeChat Video


---

# 三、视频基础字段


|字段|类型|说明|
|-|-|-|
|platform|string|平台名称|
|video_id|string|视频唯一ID|
|video_url|string|视频链接|
|publish_time|datetime|发布时间|
|collector_time|datetime|采集时间|


---

# 四、发布者字段


|字段|类型|说明|
|-|-|-|
|author_id|string|作者平台ID|
|author_name|string|作者昵称|
|author_url|string|作者主页链接|
|author_region|string|作者地区|
|author_fans|number|粉丝数量|
|author_verified|boolean|认证状态|


---

# 五、视频表现数据


|字段|类型|说明|
|-|-|-|
|title|string|视频标题|
|description|string|视频描述|
|tags|array|视频标签|
|views|number|播放量|
|likes|number|点赞数量|
|comments_count|number|评论数量|
|collect_count|number|收藏数量|
|share_count|number|分享数量|


---

# 六、业务分析字段


|字段|说明|
|-|-|
|industry_category|行业分类|
|content_type|内容类型|
|competitor_flag|是否竞品内容|
|customer_intent_probability|潜客概率|
|priority_level|采集优先级|


---

# 七、存储位置


原始数据：

