# PV_OS_CURRENT_STATE

version:
  PV_OS_V2.x


last_update:
  2026-07-20


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
    - comment_collector_agent (代码层完成)


  workflow:

    - comment_to_lead_pipeline (P0 验证通过)


  collection:

    - 采集模块骨架 (02_DATA/01_COLLECTION/)
    - 连接器基座 + 平台连接器 (Mock)
    - 数据清洗管道 (data_cleaner.py)
    - 调度器 (collection_scheduler.py)



developing:


  current:

    P1-1: 采集任务模型已完成

  next_task:

    P1-2: comment_intent_model 语义层实现


  next:

    - 抖音真实评论数据接入
    - 小红书真实评论数据接入
    - competitor_account_agent Pipeline 接入
    - competitor_intelligence_pipeline



important_rules:


  - 开发前读取00_SYSTEM规则

  - 不重复创建已有文件

  - 不偏离主动获客目标

  - 优先城市家庭光伏客户
