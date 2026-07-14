# PV_OS 客户线索输出 Schema V1.0

> PV_OS 光伏行业 AI 主动获客系统
>
> 定义 AI 分析后输出的销售线索数据结构。
>
> 更新时间：2026-07-14


# 一、目的


本文件定义：

PV_OS 将评论用户经过 AI 分析后，
转换为销售可执行线索的数据标准。


目标：

发现潜在客户。

判断客户价值。

提供主动触达入口。


---

# 二、数据来源


输入：


处理：
    ↓   
    ↓


---

# 三、线索基础字段


|字段|类型|说明|
|-|-|-|
|lead_id|string|线索唯一编号|
|platform|string|来源平台|
|user_id|string|用户ID|
|user_name|string|用户名称|
|user_url|string|用户主页链接|
|create_time|datetime|生成时间|


---

# 四、客户来源字段


|字段|说明|
|-|-|
|source_video_id|来源视频ID|
|source_video_url|视频链接|
|source_author|视频发布者|
|comment_id|触发评论ID|
|comment_text|用户原始评论|


用途：

销售查看：

客户为什么被发现。


---

# 五、客户需求分析字段


|字段|说明|
|-|-|
|intent_type|客户意图类型|
|need_description|需求描述|
|purchase_stage|购买阶段|
|urgency_level|紧迫程度|
|customer_type|客户类型|


---

# 六、客户标签字段


|字段|说明|
|-|-|
|region|区域|
|house_scene|房屋场景|
|energy_scene|能源应用场景|
|customer_tags|客户标签|


示例：


---

# 七、AI评分字段


|字段|说明|
|-|-|
|need_score|需求评分|
|region_score|区域评分|
|house_score|场景评分|
|time_score|时间评分|
|real_score|真实性评分|
|total_score|综合评分|


---

# 八、客户等级


|等级|分数|处理|
|-|-|-|
|S|80-100|立即销售触达|
|A|60-79|重点跟进|
|B|35-59|长期培育|
|C|0-34|资产保存|


---

# 九、销售动作字段


|字段|说明|
|-|-|
|follow_priority|跟进优先级|
|recommended_action|建议动作|
|contact_status|联系状态|
|owner|负责人|
|follow_time|下次跟进时间|


---

# 十、触达入口字段


核心字段：

|字段|说明|
|-|-|
|profile_url|用户主页链接|
|message_entry|私信入口|
|platform_account|平台账号|


用途：

销售人员：


---

# 十一、存储位置


主线索：


培育池：


CRM：


---

# 十二、飞书同步字段


同步：


---

# 十三、数据生命周期


原则：

所有线索长期保存。


状态变化：


---

# 十四、版本记录


|版本|日期|说明|
|-|-|-|
|V1.0|2026-07-14|建立客户线索输出标准|
