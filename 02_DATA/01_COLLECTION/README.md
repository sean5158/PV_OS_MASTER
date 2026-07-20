# PV_OS 评论采集模块 (02_DATA/01_COLLECTION)

版本：V1.0 | 日期：2026-07-20
用途：PV_OS 数据采集入口——连接视频平台，采集竞品评论，输出标准化数据

> 设计依据：PV_OS_COMMENT_COLLECTION_STRATEGY.md V2.0 / COMMENT_COLLECTOR_AGENT_DESIGN.md V2.0

## 模块定位

```
视频平台 → 02_DATA/01_COLLECTION/(配置+规则) → 08_SYSTEM/scripts/(连接器+清洗) → 02_DATA/raw/ → Pipeline → CRM
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `README.md` | 本文件 |
| `COLLECTION_RULE.md` | 采集规则（平台策略、频率、竞品选择） |
| `config.yml` | 采集配置（竞品列表、关键词、调度参数） |
| `platform_credentials.template.yml` | 平台凭证模板（不纳入版本管理） |

## 当前状态

- ✅ 模块骨架建立
- ✅ 采集规则定义
- ✅ 连接器基座实现 (08_SYSTEM/scripts/)
- ⬜ 抖音采集管道跑通
- ⬜ 小红书采集管道跑通

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-20 | 模块骨架 + 规则定义 |
