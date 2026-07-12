# PV_OS Customer Finder Agent V1.0

> 主动客户发现AI Agent


## 一、目标

发现具有光伏安装潜力的客户。


核心任务：

从公开信息或输入数据中：

识别客户需求信号

判断客户类型

生成销售线索



---

# 二、输入


输入数据：

- 评论
- 内容文本
- 平台数据
- 用户行为信号



格式：

{
"platform":"",
"content":"",
"url":"",
"time":""
}



---

# 三、AI分析


AI判断：


客户类型：

- 家庭用户
- 别墅用户
- 农村用户
- 商业用户


需求信号：

- 装修
- 建房
- 电费高
- 新能源兴趣
- 安装咨询



---

# 四、输出


生成：

客户线索


格式：


lead_id

source

content

customer_type

intent_level

lead_score

next_action



---

# 五、连接模块


输入：

13_BUSINESS_VALIDATION/outbound_customer_finding/sources


规则：

13_BUSINESS_VALIDATION/outbound_customer_finding/filters


评分：

13_BUSINESS_VALIDATION/outbound_customer_finding/scoring


输出：

05_CUSTOMER_CRM/leads



---

# 六、版本


V1.0

2026-07-12

建立主动客户发现Agent
