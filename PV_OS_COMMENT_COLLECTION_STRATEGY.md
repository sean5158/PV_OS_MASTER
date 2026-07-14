# PV_OS_COMMENT_COLLECTION_STRATEGY

版本：V2.0
日期：2026-07-13
用途：PV_OS 评论采集模块设计。围绕城市小区光伏客户主动发现，定义采集定位、平台策略、竞品体系、关键词体系、数据标准、进入规则及系统连接方式。

> 设计原则：仅基于已有固化规则文件设计，不自行创造业务规则。
> 核心聚焦：城市小区光伏客户。
>
> 依赖规则：
> - `PV_OS_MASTER_CONTEXT.md` — 项目全局上下文
> - `COMMENT_COLLECTION_AUDIT.md` — 采集能力审计（审计结论：模块完全缺失）
> - `02_DATA/04_COMMENT_DATABASE/COMMENT_ANALYZER_RULE.md` — 评论来源与分析对象
> - `02_DATA/04_COMMENT_DATABASE/COMMENT_TIME_AND_MATCH_RULE.md` — 时间价值、区域识别
> - `02_DATA/04_COMMENT_DATABASE/COMMENT_DATA_LIFECYCLE_RULE.md` — 数据生命周期
> - `02_DATA/02_COMPETITOR_DATABASE/COMPETITOR_SCORE_RULE.md` — 竞品评分、城市家庭光伏匹配
> - `02_DATA/02_COMPETITOR_DATABASE/COMPETITOR_DISCOVERY_ALGORITHM.md` — 竞品发现算法
> - `02_DATA/06_SCORE_MODEL/CUSTOMER_SCORE_MODEL.md` — 区域分值、房屋分值、五维评分
> - `02_DATA/03_REGION_LIBRARY/REGION_MASTER.md` — 川渝黔三级区域主数据
> - `02_DATA/data_dict/comment_schema.md` — 评论数据标准结构
> - `03_AI_AGENT/agents/comment_analyzer/agent.yml` — 下游分析入口
> - `03_AI_AGENT/agents/lead_scoring_agent/agent.yml` — 下游评分入口（V2.1）
> - `10_AI_AUTOMATION_ENGINE/workflows/comment_to_lead_pipeline.yml` — 下游自动 pipeline

---

## 一、评论采集模块定位

### 1.1 PV_OS 完整链路中的位置

引用自 `PV_OS_MASTER_CONTEXT.md` 定义的业务流程：

```
视频平台（抖音/小红书/快手/视频号）
    │
    ▼
┌─────────────────────────────────────┐
│  评论采集模块（本文档定义）           │  ← 当前缺失，P0 优先级
│  02_DATA/01_COLLECTION/             │
│  输出：02_DATA/raw/                  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  数据清洗                             │  ← 当前空脚本，待实现
│  08_SYSTEM/scripts/data_cleaner.py   │
│  输出：02_DATA/04_COMMENT_DATABASE/   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  comment_analyzer（✅ 已定义）        │
│  03_AI_AGENT/agents/comment_analyzer/ │
│  功能：客户识别、意向判断、标签生成     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  lead_scoring_agent（✅ V2.1）       │
│  03_AI_AGENT/agents/lead_scoring_agent/│
│  功能：五维评分、S/A/B/C 等级、CRM 路由│
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  CRM（✅ 已定义）                     │
│  05_CUSTOMER_CRM/leads/              │
│  hot/ qualified/ raw/                │
└─────────────────────────────────────┘
```

### 1.2 采集模块职责

| 职责 | 说明 |
|------|------|
| 输入 | 竞品账号列表（来自 `02_DATA/02_COMPETITOR_DATABASE/`） + 关键词配置 |
| 处理 | 按平台策略采集竞品视频评论 |
| 输出 | `02_DATA/raw/` 目录下符合 `comment_schema.md` 格式的标准化评论数据 |
| 触发 | 完成后发布 `new_comment_received` 事件，启动 `comment_to_lead_pipeline` |

### 1.3 当前状态

引用自 `COMMENT_COLLECTION_AUDIT.md`：

> ❌ `02_DATA/raw/` 空目录
> ❌ `collector_base.py` 空脚本
> ❌ `data_cleaner.py` 空脚本
> ⚠️ 仅 1 条手工测试数据（成都别墅客户）
> ✅ 下游（分析→评分→CRM）规则已完整固化

**结论：下游链路已就绪，上游数据入口缺失。这是 PV_OS 当前最紧急的缺口。**

---

## 二、平台策略

### 2.1 平台价值判断模型

针对五平台（抖音、小红书、快手、视频号、B站），建立四维价值判断。以下判断基于各平台公开特征与 PV_OS 城市小区客户定位推导，具体数据需待采集验证。

| 维度 | 权重 | 说明 |
|------|:----:|------|
| 城市用户比例 | 30% | 平台用户中城市中高收入家庭占比 |
| 光伏需求密度 | 30% | 光伏/家庭能源/装修相关内容的评论密度 |
| 评论商业意图 | 25% | 评论中询价/安装/效果类意图占比 |
| 数据可获取性 | 15% | API 开放程度、反爬策略、技术可行性 |

### 2.2 分平台价值评估

#### 抖音（🔴 P0 最高优先级）

| 维度 | 评级 | 判断 |
|------|:--:|------|
| 城市用户比例 | ⭐⭐⭐⭐⭐ | 覆盖全人群，城市家庭用户基数最大 |
| 光伏需求密度 | ⭐⭐⭐⭐⭐ | 川渝黔本地光伏安装商集中运营，安装实拍类视频评论需求密度高 |
| 评论商业意图 | ⭐⭐⭐⭐⭐ | 用户评论直接，"多少钱""怎么装""联系我"类高频出现 |
| 数据可获取性 | ⭐⭐⭐ | 有官方 API，但评论数据需通过爬虫或第三方工具获取 |

**城市小区客户采集优势：** 抖音上川渝黔本地光伏安装商（竞品）的别墅/叠拼/阳光房安装实拍类视频评论区是城市高价值客户的集中来源。用户看到本地案例后更容易产生"我家能不能装"的需求。

> 引用：`COMPETITOR_SCORE_RULE.md` §2.4 四川重庆贵州区域权重评分，§2.2 城市家庭光伏匹配评分。

#### 小红书（🟠 P1 高优先级）

| 维度 | 评级 | 判断 |
|------|:--:|------|
| 城市用户比例 | ⭐⭐⭐⭐⭐ | 一线/新一线城市女性用户为主，消费力强 |
| 光伏需求密度 | ⭐⭐⭐ | 光伏内容偏向"阳光房改造""露台光伏""家庭能源"生活分享 |
| 评论商业意图 | ⭐⭐⭐⭐ | 用户习惯主动询问品牌/价格/推荐，商业意图自然且直接 |
| 数据可获取性 | ⭐⭐ | 反爬严格，API 受限 |

**城市小区客户采集优势：** 小红书上的"阳光房光伏""露台改造""花园洋房光伏"等内容精准命中城市女性用户。用户评论风格为"这个在哪里做的？""大概多少钱？""求推荐"，商业意图自然且转化率高。阳光房场景（CUSTOMER_SCORE_MODEL 分值 18）在小红书上有独特的内容生态。

#### B站（🟡 P1 中优先级）

| 维度 | 评级 | 判断 |
|------|:--:|------|
| 城市用户比例 | ⭐⭐⭐⭐ | 一二线城市年轻用户为主 |
| 光伏需求密度 | ⭐⭐ | 光伏内容以科普/评测为主，安装类偏少 |
| 评论商业意图 | ⭐⭐ | 评论以讨论技术参数为主，购买意图密度低于抖快 |
| 数据可获取性 | ⭐⭐⭐⭐ | API 相对开放 |

**城市小区客户采集优势：** B站光伏科普视频下的评论以技术了解和效果咨询为主，属于"明确兴趣"层级（CUSTOMER_SCORE_MODEL 需求强度 20 分）。城市年轻用户对家庭能源有好奇心，适合长期培育。但明确购买意图密度低，采集优先级低于抖音和小红书。

#### 快手（🟡 P2 低优先级）

| 维度 | 评级 | 判断 |
|------|:--:|------|
| 城市用户比例 | ⭐⭐ | 下沉市场为主，城市用户占比低于抖音/小红书 |
| 光伏需求密度 | ⭐⭐⭐ | 农村自建房光伏内容多，城市小区客户密度较低 |
| 评论商业意图 | ⭐⭐⭐ | 评论直接，"多少钱""怎么装"类常见 |
| 数据可获取性 | ⭐⭐⭐ | 与抖音同体系，技术路径相似 |

**城市小区客户采集定位：** 快手上的光伏内容以农村自建房为主，城市小区客户浓度低于抖音和小红书。采集时不作为城市客户的主要来源，但农村经营场景（民宿、农家乐、养殖——CUSTOMER_SCORE_MODEL §8.1 A类）值得关注，按商业客户处理。

#### 视频号（⚪ P2 最低优先级）

| 维度 | 评级 | 判断 |
|------|:--:|------|
| 城市用户比例 | ⭐⭐⭐ | 微信生态，全年龄段覆盖 |
| 光伏需求密度 | ⭐⭐ | 光伏内容以公众号关联为主，评论生态弱 |
| 评论商业意图 | ⭐⭐ | 微信熟人社交环境，公开评论商业意图弱 |
| 数据可获取性 | ⭐ | 无公开 API，几乎不可自动化采集 |

**采集定位：** 视频号评论生态弱，且数据获取极难。商业验证阶段不主动采集。作为未来私域补充渠道预留。

### 2.3 平台采集优先级矩阵

| 优先级 | 平台 | 城市客户浓度 | 采集频率 | 商业验证阶段 |
|:------:|------|:----------:|---------|:----------:|
| **P0** | 抖音 | 最高 | 每 6 小时 | ✅ 第一批 |
| **P1** | 小红书 | 高 | 每日 | ✅ 第二批 |
| **P1** | B站 | 中 | 每日 | ✅ 第二批 |
| **P2** | 快手 | 中低 | 每日（仅城市+经营场景） | ⚪ 第三批 |
| **P2** | 视频号 | 低 | 不主动采集 | ⚪ 预留 |

---

## 三、竞品账号体系

### 3.1 四级竞品分类

竞品账号的核心价值取决于其评论区的城市小区客户密度。以下分类围绕"城市小区光伏客户主动发现"这一目标设计。

> 引用自 `COMPETITOR_SCORE_RULE.md` 六维评分体系（业务匹配+城市家庭光伏匹配+别墅/阳光房/小商业权重+川渝黔区域+评论区需求价值+活跃度）和 `COMPETITOR_DISCOVERY_ALGORITHM.md` 竞品定义。

#### 一级：全国光伏品牌

| 属性 | 说明 |
|------|------|
| 定位 | 全国性光伏安装品牌/连锁，账号以品牌展示和案例分享为主 |
| 评论特征 | 覆盖面广，评论中"这个品牌怎么样""哪个城市有"类信息型提问多 |
| 城市客户信号 | 中等。评论通常按地区分流，川渝黔客户占比受总体基数稀释 |
| 采集优先级 | 🟠 高（有城市客户，但需大量过滤） |
| 竞品评分参考 | 业务匹配 25-30 + 城市家庭光伏 11-15 + 区域 3-6（全国性但含川渝黔内容） |

#### 二级：区域安装商

| 属性 | 说明 |
|------|------|
| 定位 | 川渝黔本地光伏安装公司/团队，服务范围明确在核心市场区域 |
| 评论特征 | 评论中本地客户咨询密度最高，"成都这边怎么联系""重庆能上门看吗" |
| 城市客户信号 | 🔴 最高。本地化程度高，城市客户占比和转化率最高 |
| 采集优先级 | 🔴 最高 |
| 竞品评分参考 | 业务匹配 25-30 + 城市家庭光伏 11-20 + 区域 12-15 |

> 引用：`COMPETITOR_SCORE_RULE.md` §2.4 四川重庆贵州区域权重评分（本地直营 12-15 分）。

#### 三级：城市小区案例账号

| 属性 | 说明 |
|------|------|
| 定位 | 以高端住宅（别墅、叠拼、阳光房）案例展示为主的光伏安装账号，内容高度聚焦城市家庭场景 |
| 评论特征 | 评论区以"我家也是别墅""这个多少钱""能来我家看吗"为主，城市客户意图最集中 |
| 城市客户信号 | 🔴 极高。内容本身筛选了受众，评论精准度远高于泛光伏视频 |
| 采集优先级 | 🔴 最高 |
| 竞品评分参考 | 城市家庭光伏 16-20 + 别墅/阳光房权重 12-15 + 评论区需求价值 8-10 |

> 引用：`COMPETITOR_SCORE_RULE.md` §2.2 城市家庭光伏匹配（专注家庭光伏 16-20 分）、§2.3 别墅/阳光房/小商业权重（强覆盖 12-15 分）。

#### 四级：装修、别墅、住宅改造相关账号

| 属性 | 说明 |
|------|------|
| 定位 | 非纯光伏账号，以高端住宅装修/别墅改造/阳光房设计为主题，内容中涉及光伏/新能源 |
| 评论特征 | 评论以装修咨询为主，但交叉关注光伏的用户是潜在客户（如：阳光房设计视频下评论"能做光伏吗"） |
| 城市客户信号 | 🟡 中高。受众本身为有装修预算的城市业主，光伏需求是交叉转化 |
| 采集优先级 | 🟡 中（仅采集含光伏/新能源相关视频的评论） |
| 竞品评分参考 | 业务匹配 10-17（中度匹配）+ 别墅/阳光房权重 7-11 |

### 3.2 竞品入库采集优先级

| 竞品层级 | 采集优先级 | 采集频率 | 评论全量 | 城市过滤策略 |
|:--------:|:--------:|---------|:------:|------------|
| 二级（区域安装商） | 🔴 最高 | 每 6 小时 | ✅ | 不预设过滤，全量进入 |
| 三级（城市案例账号） | 🔴 最高 | 每 6 小时 | ✅ | 不预设过滤，全量进入 |
| 一级（全国品牌） | 🟠 高 | 每日 | ⚠️ | 仅采集 IP 属地为川渝黔的评论 |
| 四级（装修/别墅账号） | 🟡 中 | 每日 | ⚠️ | 仅采集含光伏/新能源关键词的视频评论 |

---

## 四、关键词体系

### 4.1 体系设计原则

关键词体系围绕**城市小区光伏客户主动发现**设计。农村相关关键词不作为主力模型，仅保留边界覆盖（引用 CUSTOMER_SCORE_MODEL §8 原则，农村经营场景按商业客户处理）。

所有词根来源引用已有规则文件中的关键字库，不自行创造。

### 4.2 A类：光伏需求词根

锁定"用户对光伏有基础认知和兴趣"。引用自 `CUSTOMER_SCORE_MODEL.md` §2.2 需求强度关键字库 + `COMMENT_ANALYZER_RULE.md` §五 房屋场景。

| 词根 | 类型 | 来源 | 采集用途 |
|------|:--:|------|---------|
| 光伏 | 核心词 | 规则通用 | 基础搜索，与其它词根组合 |
| 太阳能 | 核心词 | 规则通用 | 基础搜索 |
| 家庭光伏 | 组合词 | COMPETITOR_SCORE_RULE §2.2 | 精准匹配家庭客户 |
| 户用光伏 | 行业词 | COMPETITOR_SCORE_RULE §2.2 | 同家庭光伏 |
| 光伏储能 | 组合词 | comment_schema.md | 高价值客户关注点 |
| 家庭能源 | 泛词 | COMMENT_ANALYZER_RULE §一 | 补充覆盖 |

### 4.3 B类：安装意图词根

锁定"用户有明确安装意向"。引用自 `CUSTOMER_SCORE_MODEL.md` §2.2 40 分关键字库。

| 词根 | 等级 | 来源 |
|------|:--:|------|
| 想装 / 要装 / 准备装 / 考虑装 | 极强需求（40分） | CUSTOMER_SCORE_MODEL §2.2 |
| 安装一套 / 搞一套 / 装一套 | 极强需求（40分） | CUSTOMER_SCORE_MODEL §2.2 |
| 上门测量 / 勘测 / 来看看 | 极强需求（40分） | CUSTOMER_SCORE_MODEL §2.2 |
| 施工时间 / 工期 / 多久装好 | 极强需求（40分） | CUSTOMER_SCORE_MODEL §2.2 |
| 安装流程 / 怎么装 | 强需求（30分） | CUSTOMER_SCORE_MODEL §2.2 |

### 4.4 C类：价格咨询词根

锁定"用户有价格敏感和购买意向"。引用自 `CUSTOMER_SCORE_MODEL.md` §2.2 30 分关键字库。

| 词根 | 等级 | 来源 |
|------|:--:|------|
| 多少钱 / 价格 / 费用 / 怎么收费 | 强需求（30分） | CUSTOMER_SCORE_MODEL §2.2 |
| 报价 | 极强需求（40分） | CUSTOMER_SCORE_MODEL §2.2 |
| 贵不贵 / 预算 / 成本 | 极强需求（40分） | CUSTOMER_SCORE_MODEL §2.2 |

### 4.5 D类：收益关注词根

锁定"用户关注光伏效果和收益"。引用自 `CUSTOMER_SCORE_MODEL.md` §2.2 20 分关键字库。

| 词根 | 等级 | 来源 |
|------|:--:|------|
| 效果怎么样 / 好用吗 / 靠谱吗 | 明确兴趣（20分） | CUSTOMER_SCORE_MODEL §2.2 |
| 发电多少 / 一天几度 / 够用吗 | 明确兴趣（20分） | CUSTOMER_SCORE_MODEL §2.2 |
| 省电 / 能带多少电器 / 多少千瓦 | 明确兴趣（20分） | CUSTOMER_SCORE_MODEL §2.2 |

### 4.6 E类：房屋场景词根

锁定"城市高价值房屋场景"。引用自 `CUSTOMER_SCORE_MODEL.md` §2.4 房屋场景精确分值表 + `COMMENT_ANALYZER_RULE.md` §五 房屋场景。

| 词根 | 分值 | 来源 | 城市客户相关性 |
|------|:--:|------|:------------:|
| 别墅 / 独栋 / 联排 | 20 | CUSTOMER_SCORE_MODEL §2.4 | 🔴 最高 |
| 叠拼 / 叠墅 | 18 | CUSTOMER_SCORE_MODEL §2.4 | 🔴 最高 |
| 阳光房 / 玻璃房 | 18 | CUSTOMER_SCORE_MODEL §2.4 | 🔴 最高 |
| 露台 / 大露台 | 18 | CUSTOMER_SCORE_MODEL §2.4 | 🔴 最高 |
| 大平层 | 15 | CUSTOMER_SCORE_MODEL §2.4 | 🟠 高 |
| 花园洋房 | 15 | CUSTOMER_SCORE_MODEL §2.4 | 🟠 高 |
| 普通住宅顶楼 | 10 | CUSTOMER_SCORE_MODEL §2.4 | 🟡 中 |
| 民宿 / 客栈 | 高价值（商业） | COMMENT_ANALYZER_RULE §五 | 🟡 中（商业客户） |

> 注意：自建房、农村房、宅基地（分值 12）为农村场景词根，保留但不作为城市客户采集的主力模型。

### 4.7 F类：城市区域词根

锁定"川渝黔核心城市区域"。引用自 `REGION_MASTER.md` 和 `CUSTOMER_SCORE_MODEL.md` §2.3 区域分值表。

| 词根类型 | 词根 | 分值 | 来源 |
|---------|------|:--:|------|
| 省 | 四川、重庆、贵州 | — | REGION_MASTER.md |
| 成都核心区 | 锦江、青羊、金牛、武侯、成华、高新、天府新区 | 20 | CUSTOMER_SCORE_MODEL §2.3 |
| 成都外围 | 龙泉驿、青白江、新都、温江、双流、郫都 | 18 | CUSTOMER_SCORE_MODEL §2.3 |
| 重庆核心区 | 渝中、江北、南岸、沙坪坝、九龙坡、大渡口、渝北、巴南 | 18 | CUSTOMER_SCORE_MODEL §2.3 |
| 贵阳核心区 | 南明、云岩、观山湖、花溪 | 15 | CUSTOMER_SCORE_MODEL §2.3 |
| 四川主要城市 | 绵阳、德阳、宜宾、南充、泸州 | 15 | CUSTOMER_SCORE_MODEL §2.3 |

### 4.8 关键词三层组合策略

采集时使用三层叠加命中城市高价值客户：

```
第一层：房屋场景词根（别墅/叠拼/阳光房/大平层/花园洋房）
    ×
第二层：城市区域词根（成都/重庆/贵阳/绵阳/...）
    ×
第三层：需求/意图/价格/收益词根（想装/多少钱/效果/...）
```

示例组合：

| 层次 | 关键词示例 | 得分潜力 |
|------|----------|:------:|
| 别墅 × 成都 × 想装报价 | "成都 别墅 光伏 多少钱" | 房屋 20 + 区域 20 + 需求 40 = **80（S级）** |
| 叠拼 × 重庆 × 效果 | "重庆 叠拼 光伏 效果怎么样" | 房屋 18 + 区域 18 + 需求 20 = **56（B级）** |
| 阳光房 × 贵阳 × 安装 | "贵阳 阳光房 光伏 怎么装" | 房屋 18 + 区域 15 + 需求 30 = **63（A级）** |

---

## 五、评论数据标准

### 5.1 采集输出格式

采集模块输出必须符合 `comment_schema.md` 标准，确保 `comment_analyzer` 可直接消费。

#### 采集阶段必填字段

| # | 字段 | 类型 | 采集来源 | schema 对应 |
|:-:|------|------|---------|-----------|
| 1 | `id` | string | 平台评论 ID + 平台前缀 | `comment_schema` 基础字段 |
| 2 | `platform` | enum | 采集时已知 | `comment_schema` 基础字段 |
| 3 | `content` | string | 平台评论区原始文本 | `comment_schema` 基础字段 |
| 4 | `author` | string | 平台评论区（脱敏，不保存手机号/真实姓名） | `comment_schema` 基础字段 |
| 5 | `create_time` | datetime | 平台评论区发布时间 | `comment_schema` 基础字段 |
| 6 | `source_url` | string | 评论所在视频/笔记链接 | `comment_schema` 基础字段 |
| 7 | `video_title` | string | 平台 API 获取视频标题 | `comment_schema` 内容来源 |
| 8 | `keyword` | string | 本次采集使用的关键词组合 | `comment_schema` 内容来源 |
| 9 | `collected_time` | datetime | 采集系统时间戳 | `comment_schema` 内容来源 |
| 10 | `location` | string | 平台公开 IP 属地 | `comment_schema` 客户标签 |

#### 采集阶段可选字段（供下游分析增强）

| # | 字段 | 采集方式 | 用途 |
|:-:|------|---------|------|
| 11 | `video_url` | 平台 API | 数据追踪 |
| 12 | `competitor_id` | 内部映射 | 标注采集来源竞品，便于后续分析 |
| 13 | `competitor_grade` | 内部映射 | 竞品等级（S/A/B），辅助评论质量预判 |
| 14 | `comment_likes` | 平台 API（如有） | 评论互动量，辅助真实性判断 |

#### AI 分析字段（采集阶段不填，留空供下游填充）

| 字段 | 说明 |
|------|------|
| `sentiment` | 情绪分析，comment_analyzer 填充 |
| `customer_intent` | 购买意向(0-3)，comment_analyzer 填充 |
| `customer_type` | 客户类型，comment_analyzer 填充 |
| `score` | 价值评分(0-100)，comment_analyzer 填充 |
| `tags` | 客户标签，comment_analyzer 填充 |
| `house_type` | 房屋类型，comment_analyzer 识别填充 |

### 5.2 输出目录结构

```
02_DATA/raw/
├── douyin/
│   ├── 2026-07-13_06h_batch_001.json    # 格式：[{comment_obj}, ...]
│   ├── 2026-07-13_12h_batch_002.json
│   └── ...
├── xiaohongshu/
│   └── 2026-07-13_daily_batch_001.json
├── bilibili/
│   └── 2026-07-13_daily_batch_001.json
├── kuaishou/
│   └── 2026-07-13_daily_batch_001.json
└── wechat_video/
    └── (预留)
```

### 5.3 与 comment_analyzer 兼容性校验

| comment_analyzer 输入声明 | 采集模块是否满足 |
|--------------------------|:-------------:|
| `input.source: 02_DATA/raw/` | ✅ 输出到同一目录 |
| `input.schema: comment_schema.md` | ✅ 格式完全对齐 |
| `id` 字段 | ✅ 必填 |
| `platform` 字段 | ✅ 必填 |
| `content` 字段 | ✅ 必填 |
| `create_time` 字段 | ✅ 必填 |
| `location` 字段 | ✅ 必填（IP 属地） |

---

## 六、数据进入规则

### 6.1 进入 comment_analyzer 的规则

所有从采集模块输出的评论（`02_DATA/raw/`）经数据清洗后全量进入 `comment_analyzer`。comment_analyzer 本身不预设过滤，由 AI 判断每条评论的价值。符合 PV_OS "全量评论入库，AI 分层判断"原则。

引用自 `COMMENT_DATA_LIFECYCLE_RULE.md`：

> 所有评论进入长期资产库。最近7天：用于即时销售发现。7天以上：用于客户画像、趋势分析、二次挖掘。

### 6.2 采集阶段过滤规则

采集阶段的前置过滤仅作用于**明显无价值数据**，不替代 AI 分析判断：

| 过滤条件 | 动作 | 原因 |
|---------|:--:|------|
| 评论内容为空或仅 emoji | 丢弃 | 无分析价值 |
| 评论内容为纯 @ 提及无实质文本 | 丢弃 | 无分析价值 |
| 重复采集（同 id 已存在） | 去重（保留最新） | 数据一致性 |
| 平台不合法（非四平台） | 丢弃 | 数据规范 |
| create_time 为未来时间 | 标记异常 | 数据质量 |

### 6.3 采集阶段不做的过滤

以下条件**不在采集阶段过滤**，全部交给 `comment_analyzer` 判断：

| 条件 | 不采集过滤的原因 |
|------|----------------|
| 评论看似无关光伏 | AI 可能通过语义分析发现隐含需求 |
| 评论来自农村 IP | 遵循 CUSTOMER_SCORE_MODEL §8 原则，农村客户不因标签自动降权 |
| 评论仅有"了解一下""看看" | 可能是观望型，进入 B 级培育池 |
| 评论含政策/补贴咨询 | 可能是政策型，comment_analyzer 负向修正 |

### 6.4 城市客户信号前置标记

采集阶段不决定评论价值，但可以前置标记城市客户信号，供 pipeline 做优先级排序：

| 信号 | 标记字段 | 生效环节 |
|------|---------|---------|
| IP 属地 = 川渝黔城市 | `ip_city_match: true` | `evaluate_comment_time` 步骤优先处理 |
| 评论文本含别墅/叠拼/阳光房/大平层 | `housing_signal: high` | `analyze_comment` 步骤优先分析 |
| 评论文本含"想装""多少钱""报价" | `demand_signal: true` | `analyze_comment` 步骤优先分析 |

---

## 七、与现有系统连接

### 7.1 与 02_DATA 层连接

```
02_DATA/01_COLLECTION/（新建）
    ├── 采集配置、关键词库、竞品目标列表
    │
    ├── 读取 ──→ 02_DATA/02_COMPETITOR_DATABASE/
    │               competitor_master.csv（竞品账号主表）
    │
    ├── 读取 ──→ 02_DATA/03_REGION_LIBRARY/
    │               REGION_MASTER.md（区域主数据）
    │
    ├── 写入 ──→ 02_DATA/raw/
    │               comment_schema.md 标准格式数据
    │
    └── 写入路径被读取 ──→ 02_DATA/04_COMMENT_DATABASE/
                            COMMENT_ANALYZER_RULE.md 定义的数据入口
```

### 7.2 与 03_AI_AGENT 层连接

```
采集模块输出（02_DATA/raw/）
    │
    ▼
comment_analyzer（03_AI_AGENT/agents/comment_analyzer/agent.yml）
    ├── input.source: 02_DATA/raw/
    ├── input.schema: comment_schema.md
    ├── analysis: customer_type + intent_level + score
    └── output.path: 05_CUSTOMER_CRM/leads/
        │
        ▼
lead_scoring_agent（03_AI_AGENT/agents/lead_scoring_agent/agent.yml V2.1）
    ├── input.upstream: comment_analyzer
    ├── scoring: 五维评分（需求40+区域20+房屋20+时间10+真实性10）
    ├── grade: S(≥80) / A(60-79) / B(35-59) / C(<35)
    └── crm_target: hot(S) / qualified(A,B) / raw(C)
```

### 7.3 与 10_AI_AUTOMATION_ENGINE 连接

```
采集模块完成一批采集
    │
    ▼ 发布事件
10_AI_AUTOMATION_ENGINE/triggers/event_bus.py
    event: new_comment_received
    │
    ▼ 触发 pipeline
10_AI_AUTOMATION_ENGINE/workflows/comment_to_lead_pipeline.yml
    Step 1: collect_comment → 02_DATA/raw/（已就绪）
    Step 2: save_comment_asset → 全量保存
    Step 3: evaluate_comment_time → 7 天窗口判断
    Step 4: analyze_comment → comment_analyzer
    Step 5: score_customer → lead_scoring_agent
    Step 6: route_customer → S/A/B/C 分流
    Step 7: create_crm_lead → CRM 入库
    Step 8: generate_follow_up → 销售任务
```

### 7.4 Scheduler 集成（待实现）

`10_AI_AUTOMATION_ENGINE/scheduler/` 目录当前为空。采集调度器需实现：

```yaml
# 建议配置：10_AI_AUTOMATION_ENGINE/scheduler/collection_schedule.yml
workflow: comment_collection
schedule:
  - cron: "0 */6 * * *"           # 每 6 小时
    platforms: [douyin]
    competitor_grades: [S, A]

  - cron: "0 9 * * *"             # 每日 09:00
    platforms: [xiaohongshu, bilibili]
    competitor_grades: [S, A, B]

  - cron: "0 9 * * 1"             # 每周一 09:00
    platforms: [kuaishou]
    competitor_grades: [S, A]
```

---

## 八、下一步开发建议

### 8.1 P0（必须立即启动）

| # | 任务 | 说明 | 输入 | 输出 |
|:-:|------|------|------|------|
| 1 | 建立 `02_DATA/01_COLLECTION/` 目录与规则文件 | 创建采集模块骨架：README + COLLECTION_RULE.md + config.yml | 本文档 | 模块目录就绪 |
| 2 | 手工采集 10 个竞品账号评论 | 参照 §3.2 竞品采集优先级，手工抓取二级+三级竞品评论，输出为标准 JSON | competitor_master.csv | 200+ 条标准化评论样本 |
| 3 | 样本送入 pipeline 端到端测试 | 验证采集→清洗→analyzer→scoring→CRM 全链路 | 手工样本 | pipeline 测试报告 |

### 8.2 P1（商业验证阶段必须完成）

| # | 任务 | 说明 | 依赖 |
|:-:|------|------|------|
| 4 | 实现抖音评论采集器 | `douyin_connector.py`，对接抖音评论区数据，输出 `comment_schema` 格式 | P0 样本验证通过 |
| 5 | 实现数据清洗脚本 | 填充 `data_cleaner.py`：去重、去噪、格式标准化、字段校验 | P0 样本验证通过 |
| 6 | 实现小红书评论采集器 | `xiaohongshu_connector.py`，聚焦阳光房/露台/花园洋房场景 | 抖音采集器完成 |
| 7 | 建立采集调度器 | `scheduler/` 模块，定时触发采集 + pipeline | event_bus.py 就绪 |
| 8 | 填写竞品主表 | `competitor_master.csv` 录入首批 20+ 川渝黔本地竞品账号 | COMPETITOR_DISCOVERY_ALGORITHM |

### 8.3 P2（规模化阶段）

| # | 任务 | 说明 |
|:-:|------|------|
| 9 | 实现 B站/快手采集器 | 补充平台覆盖 |
| 10 | 竞品评论区自动发现 | `COMPETITOR_DISCOVERY_ALGORITHM.md` 自动化执行 |
| 11 | 采集效果数据看板 | 城市客户占比、需求密度、平台效果对比 |

---

## 九、约束与禁止

| # | 约束 | 来源 |
|:-:|------|------|
| 1 | 不自行创造业务规则，所有策略基于已有固化文件 | `PV_OS_MASTER_CONTEXT.md` |
| 2 | 不修改 `02_DATA/` 已有规则文件、`05_CUSTOMER_CRM/`、评分模型原文件 | `PV_OS_CODEX_RULES.md` |
| 3 | 不预设"农村=低价值"过滤，遵循 CUSTOMER_SCORE_MODEL §8 原则 | `CUSTOMER_SCORE_MODEL.md` |
| 4 | 不采集私人信息（手机号、真实姓名、私人地址） | `comment_schema.md` |
| 5 | 不丢弃历史数据，全量保存 | `COMMENT_DATA_LIFECYCLE_RULE.md` |
| 6 | 城市小区客户是采集焦点，不是唯一对象 | 本文档§四 |

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-13 | 初版：四平台策略、时间分层、关键词组合、Phase 1-3 实施计划 |
| V2.0 | 2026-07-13 | 全面重构：新增模块定位(§一)、五平台价值判断模型(§二)、四级竞品体系(§三)、六类关键词体系(§四)、数据进入规则(§六)、系统连接(§七)、P0/P1/P2 分级(§八)。聚焦城市小区客户，所有词根标出来源固化文件 |
