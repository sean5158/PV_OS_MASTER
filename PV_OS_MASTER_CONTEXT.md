# PV_OS_MASTER_CONTEXT

版本：V1.1（已修正）
日期：2026-07-13
用途：PV_OS 项目全局上下文入口。AI（尤其是 Codex）进入项目后，应首先读取本文件以建立对项目的统一认知。

> 本文件系根据项目已有固化规则文件总结生成，不自行创造业务规则。
> 详细规则以各源文件为准。
>
> V1.1 修正说明：基于 PV_OS_CUSTOMER_MODEL_AUDIT.md（V2.0）审计结果，修正了区域分值表缺失、房屋场景精度不足、时间价值分档缺失等 9 项偏差。修正详情见 PV_OS_CONTEXT_CORRECTION_PLAN.md。

---

## 一、PV_OS 项目定位

**PV_OS = 光伏行业 AI 客户发现与销售自动化系统。**

核心业务流程：

```
竞品评论区采集 → AI 分析评论 → 识别潜在客户 → 需求判断 → 价值评分 → CRM 入库 → 销售跟进
```

PV_OS 不是单纯软件项目、AI 实验、数据收集系统或自动化工具。所有模块必须服务于商业结果：获客、识别客户、转化客户、提升销售效率、降低运营成本。

> 详见：`backup/PV_OS_BACKUP_MAP_V1.0.md`、`00_SYSTEM/PV_OS_GOVERNANCE_RULES.md`

---

## 二、核心商业目标

以下优先级来自治理规范：

| 优先级 | 目标 | 包含内容 |
|:------:|------|---------|
| **P0** | 客户获取 | 主动寻找客户、内容吸引客户、评论发现客户 |
| **P1** | 客户识别 | AI 评分、客户分类、意向判断 |
| **P2** | 客户跟进 | 自动提醒、方案生成、销售辅助 |
| **P3** | 成交管理 | 报价、合同、复购 |
| **P4** | 规模化自动化 | 工作流、调度、多 Agent 协作 |

当前阶段：商业验证阶段。核心验证两件事：主动获客（Outbound）和被动获客（Inbound）。

> 详见：`00_SYSTEM/PV_OS_GOVERNANCE_RULES.md`

---

## 三、目标客户模型

### 3.1 客户来源

- 竞品账号评论（抖音、快手、小红书、视频号）
- 光伏相关视频评论
- 家庭能源相关评论

### 3.2 客户类型（按房屋场景）

评论分析阶段使用高/中价值二分法识别：

| 场景 | 价值 | 关键词 |
|------|:----:|--------|
| 别墅 | 高 | 别墅、独栋、联排 |
| 阳光房 | 高 | 阳光房、玻璃房 |
| 叠拼 | 高 | 叠拼、叠墅 |
| 露台 | 高 | 露台、大露台 |
| 民宿 | 高 | 民宿、客栈 |
| 自建房 | 中 | 自建房、农村房、宅基地 |
| 楼顶 | 中 | 屋顶、楼顶、顶楼 |
| 商铺 | 中 | 门店、茶楼、棋牌室 |

规则：多个场景取最高价值。

在客户评分阶段，房屋场景使用精确分值：

| 场景 | 精确分值 |
|------|:----:|
| 别墅 | **20** |
| 叠拼 / 阳光房 / 露台 | **18** |
| 大平层 / 花园洋房 | **15** |
| 自建房（农村） | **12** |
| 普通住宅顶楼 | **10** |
| 普通住宅 | **5** |

> 来源：`02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md` §2.4

#### 城市客户定位

PV_OS 不设独立的"城市客户"分类。城市客户通过房屋场景高分值（别墅 20 / 叠拼 18 / 大平层 15）与城市区域高分值（成都核心区 20 / 重庆核心区 18 / 贵阳核心区 15）的乘积效应自然筛选出来。竞品发现系统也设有"城市家庭光伏匹配"评分维度（`COMPETITOR_SCORE_RULE.md` §2.2），商业验证阶段优先匹配城市高端住宅类型（别墅、独栋、叠拼、花园洋房、阳光房）。

> 城市客户是 PV_OS 评分模型的派生结果，不是独立分类。详见 `02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md` §2.3-2.4、`02_DATA/02_COMPETITOR_DATABASE/COMPETITOR_SCORE_RULE.md` §2.2。

### 3.3 农村客户分层原则

核心原则：**农村 ≠ 低价值**。真正判断标准：购买意愿 > 房屋条件 > 区域 > 农村标签。

PV_OS 将农村客户分为三类：

| 类型 | 判断 | 处理 |
|------|------|------|
| 农村自建房 + 明确想安装 | 真实购买需求 | 正常评分，进入客户池 |
| 农村自建房 + 主动询价 | 高价值农村客户 | 提升优先级 |
| 农村经营场景（民宿、农家乐、养殖、合作社） | 商业价值客户 | 按商业客户处理 |
| 农村客户询问安装条件 | 潜在客户 | 保留分析 |
| 农村客户只询问免费安装 | 政策型用户 | 降低评分 |
| 农村客户只等待政府项目 | 非即时成交 | 进入观察池 |
| 农村客户只关注补贴 | 低转化概率 | 降低优先级 |

> 详见：`02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md`（第八章）、`02_DATA/04_COMMENT_DATABASE/COMMENT_ANALYZER_RULE.md`

### 3.4 消费能力判断

PV_OS 不以独立维度评估客户消费能力。消费能力通过以下方式间接体现：

- **房屋场景**间接反映资产水平：别墅客户(20 分) → 普通住宅(5 分)
- **安装意愿**反映支付意愿：主动询价 = 具备支付意愿，免费期待 = 无支付意愿(-25 分)
- **农村经营场景**（民宿、农家乐、养殖、合作社）被识别为商业支付能力，按商业客户处理

> PV_OS 以"购买意愿 > 房屋条件 > 区域 > 农村标签"为核心判断链，消费能力是依赖房屋场景和安装意愿派生的间接信号。详见 `CUSTOMER_SCORE_MODEL.md` §2.4 和 §8.2-8.3。

### 3.5 多维分类体系

PV_OS 在不同环节使用不同维度的客户分类，互不冲突：

| 环节 | 分类维度 | 取值 |
|------|---------|------|
| CRM 入库 | `customer_type` | 家庭用户 / 别墅用户 / 小商业用户 / 同行用户 / 未知 |
| CRM 入库 | `house_type` | 普通住宅 / 别墅 / 农村自建房 / 商业建筑 / 未知 |
| AI 评分 | `intent_level` | 0 无需求 / 1 潜在兴趣 / 2 咨询意向 / 3 明确购买 |
| 评价等级 | S/A/B/C | S≥80 / A 60-79 / B 35-59 / C<35 |
| 商业验证 | 客户等级 | A 别墅用户 / B 农村自建房用户 / C 小商业用户 |

> 详见 `05_CUSTOMER_CRM/leads/lead_schema.md`、`02_DATA/data_dict/comment_schema.md`、`05_CUSTOMER_LEADS/FIELD_MAPPING_RULE.md`。

---

## 四、客户价值判断逻辑（五维评分模型）

总分 100 分，五维评分：

| 维度 | 满分 | 核心问题 |
|------|:----:|---------|
| 安装需求强度 | **40** | 用户有多想装光伏？ |
| 区域匹配价值 | **20** | 用户在不在川渝黔核心市场？ |
| 房屋场景价值 | **20** | 用户住别墅还是普通住宅？ |
| 用户真实性 | **10** | 这是真人还是机器人？ |
| 时间价值 | **10** | 这个评论是最近的吗？ |

### 4.1 需求强度（0-40 分）

| 分数 | 等级 | 标准 |
|:----:|------|------|
| 40 | 极强需求 | 明确说想安装 / 要求报价 / 要求上门测量 / 询问施工时间 |
| 30 | 强需求 | 询问多少钱 / 询问安装流程 |
| 20 | 明确兴趣 | 询问效果 / 询问发电量 |
| 10 | 普通了解 | 一般性了解，无明确购买信号 |
| 0 | 无需求 | 评论与光伏安装无关 |

**需求叠加规则**：同时命中多个分数段关键词时取最高分。

**负向修正**：免费安装期望（-25）、政策等待（-20）、补贴咨询（-15）、观望型（-10）。若仅出现免费/政策信号而无购买信号，需求强度最高不超过 10 分。

### 4.2 最终客户等级

| 等级 | 分数 | 动作 |
|:----:|:----:|------|
| **S 级** | ≥80 | 立即人工跟进 |
| **A 级** | 60-79 | 重点培育 |
| **B 级** | 35-59 | 长期运营 |
| **C 级** | <35 | 分析保存 |

> 详见：`02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md`（第二章）

### 4.3 时间价值精确分档

时间价值的 10 分按评论时间距离当前时间分配：

| 时间范围 | 分值 |
|---------|:----:|
| 视频发布后 1 小时以内 | **10** |
| 1 小时 - 24 小时 | **9** |
| 1 - 7 天 | **7** |
| 7 - 30 天 | **5** |
| 30 - 90 天 | **3** |
| 90 - 180 天 | **1** |
| 超过 180 天 | **0** |

> 来源：`02_DATA/04_COMMENT_DATABASE/COMMENT_TIME_AND_MATCH_RULE.md` §2.1

---

## 五、区域价值判断逻辑

### 5.1 区域识别优先级

1. 评论文本地点（最高）
2. IP 属地（较高）
3. 用户昵称地名（中等）
4. 账号资料（最低）

模糊识别原则：不强行猜测下级行政区（"四川想装光伏"不推断为成都），多来源融合（评论正文 > IP > 昵称 > 资料）。

> 详见：`02_DATA/03_REGION_LIBRARY/REGION_MATCH_RULE.md`

### 5.2 核心市场区域分值：川渝黔

PV_OS 核心市场覆盖四川、重庆、贵州三省，区域分值如下：

| 省份 | 区域 | 分值 |
|------|------|:----:|
| 四川 | 成都核心区（锦江/青羊/金牛/武侯/成华/高新区/天府新区） | **20** |
| 四川 | 成都外围区（龙泉驿/青白江/新都/温江/双流/郫都） | **18** |
| 重庆 | 重庆核心区（渝中/江北/南岸/沙坪坝/九龙坡/大渡口/渝北/巴南） | **18** |
| 四川 | 成都郊县（新津/简阳/都江堰/彭州/邛崃/崇州/金堂/大邑/蒲江） | **16** |
| 四川 | 四川主要城市（绵阳/德阳/宜宾/南充/泸州） | **15** |
| 重庆 | 重庆外围区（北碚/涪陵/长寿/江津/合川/永川/南川/綦江/大足/铜梁/璧山/荣昌/万州） | **15** |
| 贵州 | 贵阳核心区（南明/云岩/花溪/乌当/白云/观山湖） | **15** |
| 四川 | 四川其余城市（达州/乐山/眉山/遂宁/广安/内江/自贡/广元/雅安/巴中/资阳/攀枝花） | **13** |
| 贵州 | 贵州重点城市（遵义/毕节/安顺） | **13** |
| 贵州 | 贵州其余（六盘水/铜仁/黔东南/黔南/黔西南） | **10** |
| — | 省级未知城市（川渝黔省级但无法定位城市） | **10** |
| — | 区域未知（不在川渝黔范围或完全无法判断） | **0** |

> 来源：`02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md` §2.3、`02_DATA/03_REGION_LIBRARY/REGION_MATCH_RULE.md` §五

---

## 六、评论分析规则

### 6.1 评论时间价值窗口

所有评论均进入分析库，时间不是过滤条件而是价值权重：

| 时间窗口 | 定位 | 处理方式 |
|---------|------|---------|
| 最近 7 天 | 当前销售机会池 | 优先人工跟进 |
| 7 - 30 天 | 潜在成交池 | 进入跟进流程 |
| 30 - 180 天 | 长期客户资产库 | 保留标签用于 AI 训练和二次营销 |
| 超过 180 天 | 历史分析数据 | 降低权重，不删除 |

> 详见：`02_DATA/04_COMMENT_DATABASE/COMMENT_TIME_AND_MATCH_RULE.md`、`COMMENT_DATA_LIFECYCLE_RULE.md`

### 6.2 评论价值等级

| 等级 | 含义 | 处理 |
|:----:|------|------|
| S 级 | 高价值客户（明确安装需求） | 立即进入 CRM |
| A 级 | 明确兴趣客户 | 进入重点跟进池 |
| B 级 | 培育客户 | 进入培育池 |
| C 级 | 普通互动 | 只保存分析数据 |

> 详见：`02_DATA/04_COMMENT_DATABASE/COMMENT_ANALYZER_RULE.md`

### 6.3 区域模糊识别原则

区域不要求精确。识别优先级：1 评论文本地点 > 2 IP 属地 > 3 昵称地名 > 4 账号资料。无法精确时保留上级区域，不丢弃。

### 6.4 房屋场景识别原则

多场景匹配时取最高价值。

---

## 七、评分模型规则

### 7.1 五维评分（同第四章）

总分 100 = 需求强度 40 + 区域价值 20 + 房屋场景 20 + 用户真实性 10 + 时间价值 10。等级阈值：S ≥ 80、A 60-79、B 35-59、C < 35。

### 7.2 农村客户动态修正

农村客户不因"农村"标签自动降低价值。若出现"想装 + 报价 + 联系方式 + 上门测量"，必须进入正常销售流程。免费政策期待型客户降低需求评分（详见 §3.3）。

### 7.3 人工反馈闭环

销售跟进后标记状态（已联系 / 已回复 / 已加微信 / 已测量 / 已成交 / 无需求），反馈数据用于反向优化 AI 评分。

### 7.4 版本管理

语义化版本号（V主.次），`06_SCORE_MODEL/` 下保留当前版本和历史备份。

> 详见：`02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md`

---

## 八、CRM 流转规则

### 8.1 CRM 目录结构

```
05_CUSTOMER_CRM/
├── leads/
│   ├── raw          # 原始线索（所有采集评论）
│   ├── qualified    # A 级 / B 级客户
│   └── hot          # S 级客户
├── customers        # 已转化客户
├── follow_ups       # 跟进记录
└── funnel           # 漏斗分析
```

### 8.2 Lead Schema 核心字段

| 字段 | 说明 | 示例值 |
|------|------|--------|
| `lead_id` | 唯一编号 | `PV_LEAD_000001` |
| `source_platform` | 来源平台 | `douyin` / `xiaohongshu` / `kuaishou` |
| `source_content` | 原始评论内容 | — |
| `customer_type` | 客户类型 | 家庭用户 / 别墅用户 / 小商业用户 |
| `location` | 地区信息 | — |
| `house_type` | 房屋类型 | 普通住宅 / 别墅 / 农村自建房 / 商业建筑 |
| `intent_level` | 购买意向 | 0 无需求 / 1 潜在兴趣 / 2 咨询意向 / 3 明确购买 |
| `lead_score` | AI 评分 | 0-100 |
| `tags` | 客户标签 | 高意向 / 价格咨询 / 储能需求 / 别墅客户 |
| `status` | 销售状态 | new / contacted / follow_up / quoted / closed |
| `next_action` | 下一步动作 | 电话联系 / 发送方案 / 报价 / 等待回复 |

### 8.3 自动化流转管道

```
新评论采集 → comment_analyzer（分析）
    → lead_scoring_agent（评分）
    → 05_CUSTOMER_LEADS（中间层：字段映射 + 等级转换）
    → 05_CUSTOMER_CRM（入库）
        → S 级进 hot / A-B 级进 qualified / C 级进 raw
```

AI 等级到 CRM 意向转换：S → 3 明确购买 / A → 2 咨询意向 / B → 1 潜在兴趣 / C → 0 无需求。

工作流文件：`10_AI_AUTOMATION_ENGINE/workflows/comment_to_lead_pipeline.yml`

> 详见：`05_CUSTOMER_CRM/leads/lead_schema.md`、`05_CUSTOMER_LEADS/FIELD_MAPPING_RULE.md`、`backup/PV_OS_BACKUP_MAP_V1.0.md`

---

## 九、当前开发状态

### 9.1 已完成模块

| 模块 | 路径 |
|------|------|
| ✅ 评论分析规则 | `02_DATA/04_COMMENT_DATABASE/COMMENT_ANALYZER_RULE.md` |
| ✅ 评论时间资产规则 | `02_DATA/04_COMMENT_DATABASE/COMMENT_TIME_AND_MATCH_RULE.md` |
| ✅ 评论生命周期规则 | `02_DATA/04_COMMENT_DATABASE/COMMENT_DATA_LIFECYCLE_RULE.md` |
| ✅ 区域识别规则 | `02_DATA/03_REGION_LIBRARY/` |
| ✅ 农村客户价值规则 | `02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md`（第八章） |
| ✅ 客户评分模型 | `02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md` |
| ✅ CRM 结构 | `05_CUSTOMER_CRM/` |
| ✅ 自动化流程 | `10_AI_AUTOMATION_ENGINE/workflows/` |
| ✅ 备份系统 | `99_BACKUP_ENGINE/` |
| ✅ 客户模型审计 | `PV_OS_CUSTOMER_MODEL_AUDIT.md` |
| ✅ 修正计划 | `PV_OS_CONTEXT_CORRECTION_PLAN.md` |

### 9.2 当前开发位置

**模块**：`03_AI_AGENT`  
**当前任务**：`lead_scoring_agent`  
**当前状态**：`agent.yml` 开发中

### 9.3 下一步计划

1. 完成 `lead_scoring_agent/agent.yml`
2. 连接 `comment_analyzer` 输出
3. 模拟评论测试
4. 验证 S/A/B/C 流转
5. CRM 自动入库测试

> 详见：`backup/PV_OS_STATUS.md`、`backup/PV_OS_CODEX_STATUS.md`

---

## 十、AI 进入项目后的读取顺序

### 10.1 推荐读取顺序

| 顺序 | 文件 | 用途 |
|:----:|------|------|
| 1 | `PV_OS_MASTER_CONTEXT.md`（本文件） | 建立项目全局认知 |
| 2 | `backup/PV_OS_BACKUP_MAP_V1.0.md` | 恢复系统上下文，了解架构与模块 |
| 3 | `backup/PV_OS_BUSINESS_TREE.md` | 理解核心业务流 |
| 4 | `backup/PV_OS_RULE_INDEX.md` | 快速定位各规则文件 |
| 5 | `backup/PV_OS_STATUS.md` | 了解当前开发进度 |
| 6 | `backup/PV_OS_CODEX_STATUS.md` | 了解 Codex 的当前任务和记忆 |
| 7 | `00_SYSTEM/PV_OS_CODEX_RULES.md` | Codex 行为约束（允许/禁止的目录、任务流程） |
| 8 | `00_SYSTEM/PV_OS_AI_RULES.md` | 全平台 AI 协作规则（四平台分工、执行流程等） |
| 9 | `00_SYSTEM/PV_OS_GOVERNANCE_RULES.md` | 项目治理规范（优先级、模块审批、商业验证） |

### 10.2 按任务按需深入

| 涉及任务 | 深入文件 |
|----------|---------|
| 评论分析 / 客户识别 | `02_DATA/04_COMMENT_DATABASE/COMMENT_ANALYZER_RULE.md` |
| 评论时间 / 区域模糊匹配 | `02_DATA/04_COMMENT_DATABASE/COMMENT_TIME_AND_MATCH_RULE.md` |
| 客户评分 / 等级划分 | `02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md` |
| CRM / 线索字段 | `05_CUSTOMER_CRM/leads/lead_schema.md` |
| 自动化工作流 | `10_AI_AUTOMATION_ENGINE/workflows/comment_to_lead_pipeline.yml` |
| Agent 开发 | `03_AI_AGENT/agents/` 下各 agent 的 `agent.yml` |
| 区域数据 | `02_DATA/03_REGION_LIBRARY/` |

### 10.3 Codex 启动最小读取集

根据 `PV_OS_CODEX_RULES.md`，Codex 启动时必须读取的五个 backup 文件：

- `backup/PV_OS_BACKUP_MAP_V1.0.md`
- `backup/PV_OS_RULE_INDEX.md`
- `backup/PV_OS_BUSINESS_TREE.md`
- `backup/PV_OS_STATUS.md`
- `backup/PV_OS_CODEX_STATUS.md`

加上 `00_SYSTEM/PV_OS_CODEX_RULES.md`，共 6 个文件即可建立 Codex 工作上下文。

---

## 附录：文件索引速查

| 类别 | 文件 | 路径 |
|------|------|------|
| 项目定位 | PV_OS_BOOTSTRAP.md | 项目根 |
| 恢复导航 | PV_OS_BACKUP_MAP_V1.0.md | `backup/` |
| 业务流 | PV_OS_BUSINESS_TREE.md | `backup/` |
| 规则索引 | PV_OS_RULE_INDEX.md | `backup/` |
| 项目状态 | PV_OS_STATUS.md | `backup/` |
| Codex 状态 | PV_OS_CODEX_STATUS.md | `backup/` |
| AI 协作规则 | PV_OS_AI_RULES.md | `00_SYSTEM/` |
| 治理规范 | PV_OS_GOVERNANCE_RULES.md | `00_SYSTEM/` |
| Codex 约束 | PV_OS_CODEX_RULES.md | `00_SYSTEM/` |
| 评论分析规则 | COMMENT_ANALYZER_RULE.md | `02_DATA/04_COMMENT_DATABASE/` |
| 时间资产规则 | COMMENT_TIME_AND_MATCH_RULE.md | `02_DATA/04_COMMENT_DATABASE/` |
| 评论生命周期 | COMMENT_DATA_LIFECYCLE_RULE.md | `02_DATA/04_COMMENT_DATABASE/` |
| 客户评分模型 | CUSTOMER_SCORE_MODEL.md | `02_DATA/06_SCORE_MODEL/` |
| CRM 线索字段 | lead_schema.md | `05_CUSTOMER_CRM/leads/` |
| 自动化管道 | comment_to_lead_pipeline.yml | `10_AI_AUTOMATION_ENGINE/workflows/` |
| 客户模型审计 | PV_OS_CUSTOMER_MODEL_AUDIT.md | 项目根 |
| 修正计划 | PV_OS_CONTEXT_CORRECTION_PLAN.md | 项目根 |

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0（草案） | 2026-07-13 | 基于已有固化规则文件汇总生成，包含 10 个板块 |
| V1.1（已修正） | 2026-07-13 | 基于 AUDIT V2.0 修正 9 项偏差：完整川渝黔区域表、房屋精确分值、时间分档、城市客户定位、消费能力判断、农村标题、维度顺序、LEADS 中间层、多维分类 |

