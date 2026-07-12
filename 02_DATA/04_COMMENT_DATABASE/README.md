# 04_COMMENT_DATABASE —— 评论数据库

## 目录用途

存放经过清洗和结构化后的平台评论数据，是评论潜客发现系统的直接数据源。支撑 Comment Analyzer Agent 进行潜在客户识别。

典型内容：
- 清洗后的评论内容（去重、去噪、格式化）
- 评论元数据（来源平台、发布时间、互动量）
- 评论关联的视频 / 笔记信息

## 数据类型

- CSV 格式的结构化评论主表（comments_master.csv）
- JSON 格式的单条评论完整数据
- 按平台分目存储清洗结果：douyin/、xiaohongshu/、kuaishou/、shipinhao/

## 未来 AI 读取方式

Comment Analyzer Agent 批量读取此目录的最新评论数据，执行潜在客户意图识别。AI 按平台 + 时间范围定向读取增量数据，识别结果输出到 05_CUSTOMER_LEADS。
