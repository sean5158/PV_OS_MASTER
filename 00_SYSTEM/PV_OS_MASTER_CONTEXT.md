# PV_OS MASTER 项目上下文 V1.0

> 光伏行业 AI 自动化运营系统
>
> 用于新 AI / 新账号恢复项目上下文

更新时间：
2026-07-12


# 一、项目名称

PV_OS_MASTER


# 二、项目定位

PV_OS 是光伏行业 AI 自动化运营系统。

目标：

通过 AI Agent + 数据采集 + 内容生产 + CRM 自动化，
实现：

潜在客户发现 → 客户分析 → 客户评分 → 销售转化 → 案例沉淀。


核心方向：

1. 城市家庭光伏
2. 别墅/叠拼/花园洋房/阳光房光伏
3. 小商业光伏（民宿、酒店、茶楼、美容院等）


禁止方向：

- 大型工商业光伏
- 地面电站
- 光伏供应链


# 三、系统架构

项目目录：

00_SYSTEM
系统规则与项目入口

01_PROJECT_MANAGEMENT
项目管理

02_DATA
数据资产

03_AI_AGENT
AI Agent定义

04_CONTENT
内容生产

05_CUSTOMER_CRM
客户管理

06_CASE_LIBRARY
案例库

07_FINANCE
财务

08_SYSTEM
技术实现

09_AI_OPERATION
AI运营

10_AI_AUTOMATION_ENGINE
自动化引擎

11_AI_PRODUCTIZATION
产品化

12_AI_RUNTIME
AI运行环境

99_BACKUP
备份


# 四、已完成内容


## 00_SYSTEM 已完成

文件：

PV_OS_ARCHITECTURE.md

PV_OS_DIRECTORY_MAP.md

PV_OS_AI_RULES.md

PV_OS_PROJECT_STATUS.md


作用：

定义系统架构、AI规则、目录规则、项目状态。


## 02_DATA 已完成设计

已完成：

- 关键词库规则
- 竞品数据库规则
- 评论分析规则
- 客户评分模型


# 五、当前项目阶段


Phase 1：

基础设施搭建


当前完成：

15%


已完成：

✅ 系统架构

✅ AI协作规则

✅ 文件管理规范

✅ 数据规则设计


待完成：

⬜ 创建业务目录结构

⬜ 创建数据采集框架

⬜ 创建第一个AI Agent


# 六、第一个开发目标


Comment Analyzer Agent V1.0


作用：

分析公开平台评论，
发现潜在光伏客户。


流程：

平台评论数据

↓

Comment Analyzer

↓

客户意向判断

↓

Customer Score

↓

05_CUSTOMER_CRM/leads/


输出：

- 客户类型
- 地区
- 房屋类型
- 需求强度
- 购买意愿
- 客户评分


# 七、AI平台分工


ChatGPT：

负责：

战略规划
商业分析
Prompt设计
内容策略


Codex Desktop：

负责：

文件管理
代码开发
项目结构维护


Codex CLI：

负责：

Shell执行
数据处理
自动化脚本


DeepSeek：

负责：

中文批处理
大规模文本分类


# 八、AI进入项目规则


任何AI进入项目：

第一步读取：

00_SYSTEM/PV_OS_DIRECTORY_MAP.md

00_SYSTEM/PV_OS_AI_RULES.md

00_SYSTEM/PV_OS_PROJECT_STATUS.md


然后执行任务。


禁止：

- 随意创建目录
- 修改无关文件
- 数据和代码混放
- 编造客户案例数据


# 九、当前下一步任务


Phase 1.6：

创建 Comment Analyzer Agent 基础设施


目标目录：

03_AI_AGENT/

05_CUSTOMER_CRM/

08_SYSTEM/

09_AI_OPERATION/


完成后：

更新：

00_SYSTEM/PV_OS_PROJECT_STATUS.md


# 十、新账号恢复指令


请读取：

00_SYSTEM/PV_OS_MASTER_CONTEXT.md

然后读取：

PV_OS_ARCHITECTURE.md

PV_OS_AI_RULES.md

PV_OS_PROJECT_STATUS.md


恢复 PV_OS_MASTER 项目上下文。

继续当前 Phase 1 开发任务。


END
