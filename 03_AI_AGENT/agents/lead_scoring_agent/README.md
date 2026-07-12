# Lead Scoring Agent V1.0

> PV_OS 光伏客户价值评分 Agent

最后更新：2026-07-12


# 一、Agent定位

名称：

Lead Scoring Agent


目标：

根据客户评论分析结果，
自动判断客户价值和销售跟进优先级。


---

# 二、输入数据


来源：

05_CUSTOMER_CRM/leads/


输入字段：

- customer_type
- intent_level
- source_platform
- tags
- source_content


---

# 三、评分逻辑


评分范围：

0-100


购买意向：

明确购买：

+40


咨询价格：

+30


了解产品：

+15


客户类型：

别墅用户：

+20


商业用户：

+20


家庭用户：

+10


关键词：

安装：

+10


报价：

+15


收益：

+10


---

# 四、输出规则


高价值客户：

80-100


输出：

05_CUSTOMER_CRM/leads/hot/


---

潜在客户：

50-79


输出：

05_CUSTOMER_CRM/leads/qualified/


---

普通数据：

0-49


输出：

05_CUSTOMER_CRM/leads/raw/


---

# 五、版本记录


|版本|日期|说明|
|-|-|-|
|V1.0|2026-07-12|创建客户评分Agent|
