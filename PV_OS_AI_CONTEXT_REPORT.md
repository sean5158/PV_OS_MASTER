# PV OS AI CONTEXT REPORT

更新时间:
2026年 7月18日 星期六 15时20分00秒 CST

## 项目目标
中国城市家庭光伏 AI 主动获客系统

## 业务边界

目标客户:
- 城市家庭光伏
- 别墅
- 叠拼
- 花园洋房
- 高价值住宅
- 小商业

禁止方向:
- 农村光伏
- 大型工商业光伏
- 地面电站
- 供应链客户

## 数据平台
- 抖音
- 快手
- 小红书
- 视频号

## 系统规则
开发前必须读取 00_SYSTEM 规则文件
不重复创建已有模块
优先读取已有设计文件

## 当前状态
# PV_OS_CURRENT_STATE

version:
  PV_OS_V2.x


last_update:
  2026-07-15


project_goal:

  建立中国城市家庭光伏AI主动获客系统


business_boundary:


  target:

    - 城市家庭光伏
    - 别墅
    - 叠拼
    - 花园洋房
    - 高价值住宅
    - 小商业


  forbidden:

    - 农村光伏
    - 大型工商业光伏
    - 地面电站
    - 供应链客户



platform:

  data_source:

    - 抖音
    - 快手
    - 小红书
    - 视频号



completed:


  system:

    - 基础架构
    - 数据目录
    - Agent规范


  agents:

    - customer_finder_agent
    - comment_analyzer
    - lead_scoring_agent


  workflow:

    - comment_to_lead_pipeline



developing:


  current:

    AI Context Boot


  next:

    competitor_account_agent

    comment_collector_agent

    competitor_intelligence_pipeline



important_rules:


  - 开发前读取00_SYSTEM规则

  - 不重复创建已有文件

  - 不偏离主动获客目标

  - 优先城市家庭光伏客户
