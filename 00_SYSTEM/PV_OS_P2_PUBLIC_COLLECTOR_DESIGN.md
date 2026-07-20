# PV_OS P2-2 Public Search Collector 接口设计

版本：V1.0
日期：2026-07-20
状态：**接口设计 — 不包含代码实现**

> 依赖：
> - `PV_OS_P2_ARCHITECTURE_DESIGN.md` V2.1 — 三模式架构
> - `COMPETITOR_DISCOVERY_ALGORITHM.md` — 六阶段发现流程
> - `COMMENT_COLLECTOR_AGENT_DESIGN.md` V2.0 — Collector 设计
> - `keyword_expander.py` — 关键词扩展引擎 (已完成)
> - `competitor_discovery.py` — 竞品发现引擎 (已完成)
> - `collector_base.py` — BaseCollector 抽象

---

## 一、设计定位

### 1.1 三模式关系

```
mode=mock       → 内置测试数据，Pipeline验证，零依赖 (✅ 已实现)
mode=public     → 平台公开搜索+浏览+提取 (⬜ 本文档设计)
mode=official   → 平台官方API (P2后期，需企业认证)
```

**核心原则**：`public` 模式不依赖任何平台 API Key。所有数据通过公开可访问的搜索框、页面、评论区获取。`official` 仅作为 `public` 不可用时的升级路径。

### 1.2 与现有模块的关系

```
seed_keywords.yml
    │
    ▼
keyword_expander.py (✅)
    │  搜索矩阵
    ▼
┌─────────────────────────────────────┐
│  PublicSearchCollector (本文档)     │  ← P2-2 新增
│                                     │
│  search_by_keywords(keyword, plat,  │
│                     depth)          │
│      ↓                              │
│  搜索结果解析 → 账号候选列表          │
│                                     │
│  discover_account(account_id, plat) │
│      ↓                              │
│  账号主页解析 → 账号详情              │
│                                     │
│  discover_videos(account_id, plat,  │
│                  time_range)        │
│      ↓                              │
│  作品列表解析 → 视频候选列表          │
└─────────────────────────────────────┘
    │  账号候选 + 视频候选
    ▼
competitor_discovery.py (✅)
    │  prescreen → score → 入库
    ▼
competitor_master.csv
```

---

## 二、接口定义

### 2.1 search_by_keywords()

```python
def search_by_keywords(
    keyword: str,
    platform: str,          # douyin | xiaohongshu | kuaishou
    depth: int = 30,        # 搜索结果深度 (COMPETITOR_DISCOVERY_ALGORITHM.md §二)
) -> list[SearchResultItem]:
```

**输入**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `keyword` | `str` | 搜索关键词，如 "成都 别墅光伏" |
| `platform` | `str` | 目标平台 |
| `depth` | `int` | 搜索深度（默认30，对应综合Tab前50+用户Tab前30取交集） |

**输出**：`list[SearchResultItem]`

```python
@dataclass
class SearchResultItem:
    """平台搜索结果条目。"""
    platform: str = ""           # 来源平台
    account_id: str = ""         # 平台账号ID (sec_uid / user_id)
    account_name: str = ""       # 账号昵称
    account_url: str = ""        # 账号主页链接
    account_type_hint: str = ""  # 类型提示 (个人/企业/媒体，AI初步判断)
    bio_snippet: str = ""        # 简介片段
    follower_count: int = 0      # 粉丝数 (如有)
    ip_location: str = ""        # IP属地 (如有)
    source_type: str = "search"  # search | suggest | tag
    discovery_keyword: str = ""  # 触发发现的关键词
    rank: int = 0                # 搜索结果排名
```

**规则依据**：
- `COMPETITOR_DISCOVERY_ALGORITHM.md` §二.4 平台搜索流程定义
- 抖音：综合Tab前50 + 用户Tab前30
- 小红书：笔记50 + 用户20
- 快手：视频30 + 账号20

**Mock 实现**：
- 从 `MOCK_CANDIDATES` 中按 keyword 匹配返回 (✅ 已在 `competitor_discovery.py` 中实现)
- Public 实现：解析平台搜索框返回的公开页面内容

### 2.2 discover_account()

```python
def discover_account(
    account_id: str,
    platform: str,
) -> AccountDetail | None:
```

**输入**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `account_id` | `str` | 平台账号ID |
| `platform` | `str` | 目标平台 |

**输出**：`AccountDetail | None`

```python
@dataclass
class AccountDetail:
    """账号详情 — 对标 competitor_master.csv 字段。"""
    platform: str = ""
    account_id: str = ""
    account_name: str = ""
    account_url: str = ""
    bio: str = ""                    # 完整简介
    follower_count: int = 0
    content_count: int = 0           # 作品数
    ip_location: str = ""
    verified: bool = False           # 是否认证
    account_type_ai: str = ""        # AI分类: national_brand|regional_installer|city_case|renovation
    recent_topics: list[str] = None  # 最近内容主题
    premium_signals: list[str] = None  # 高端场景信号 (别墅/阳光房/民宿...)
    region_signals: list[str] = None   # 区域信号 (成都/重庆/贵阳...)
    comment_demand_density: int = 0    # 评论区需求密度 0-10
    last_active_days: int = 7          # 距上次更新天数
```

**规则依据**：
- `COMPETITOR_DISCOVERY_ALGORITHM.md` §一.1.3："不要只靠账号名称判断。真正判断依据是：账号内容(40%)、视频标题(25%)、评论区内容(25%)、账号名称/简介(10%)"
- `COMPETITOR_ACCOUNT_MODEL.md` §九："内容行为优先原则：不以账号名称作为主要判断依据"

**Public 实现方向**：
- 访问账号主页公开页面
- 提取昵称/简介/粉丝数/IP属地/作品列表
- 分析最近N条作品标题 → `recent_topics` / `premium_signals` / `region_signals`
- 提取评论区需求信号 → `comment_demand_density`

### 2.3 discover_videos()

```python
def discover_videos(
    account_id: str,
    platform: str,
    time_range_days: int = 30,
    limit: int = 10,
) -> list[VideoCandidate]:
```

**输入**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `account_id` | `str` | 平台账号ID |
| `platform` | `str` | 目标平台 |
| `time_range_days` | `int` | 时间范围（默认30天） |
| `limit` | `int` | 最多返回视频数 |

**输出**：`list[VideoCandidate]`

```python
@dataclass
class VideoCandidate:
    """视频候选 — 用于评论区采集的入口。"""
    platform: str = ""
    video_id: str = ""           # 平台视频ID (aweme_id / note_id)
    video_url: str = ""          # 视频链接
    title: str = ""              # 标题
    topic: str = ""              # 话题/标签
    publish_time: str = ""       # 发布时间
    comment_count: int = 0       # 评论数 (如有)
    housing_signal: str = ""     # 房屋场景信号: 别墅/叠拼/阳光房/普通住宅
    relevance_score: int = 0     # 相关性 0-10 (标题+话题与目标场景匹配度)
```

**规则依据**：
- `COMMENT_COLLECTOR_AGENT_DESIGN.md` §四："哪些视频进入评论采集"
- `PV_OS_COMMENT_COLLECTION_TASK_MODEL.md` §二.2: `video_filter` 字段 (time_range_days, housing_match_only, video_types)

**Public 实现方向**：
- 访问账号作品列表公开页面
- 提取视频标题/话题/发布时间
- AI分析标题中的房屋场景信号

---

## 三、三模式调度

### 3.1 mode 路由（更新 platform_adapter.py）

```python
# platform_adapter.py 新增 CollectorMode

class CollectorMode(str, Enum):
    AUTO = "auto"
    MOCK = "mock"
    PUBLIC = "public"     # 已有 (原 LIVE)
    OFFICIAL = "official" # 新增
    FILE = "file"

# 新增 PublicSearchCollector 注册
def _create_public_collector(platform: str) -> BaseCollector | None:
    if platform == "douyin":
        from douyin_public_collector import DouyinPublicCollector
        return DouyinPublicCollector()
    # xiaohongshu / kuaishou 待实现
```

### 3.2 降级链

```
auto
├─ csv_import / xiaohongshu → file (不变)
├─ 有 official API 凭证 → official
├─ enable_public_collection=True → public   ← P2-2 新增
└─ 其他 → mock
```

### 3.3 与 competitor_discovery.py 的集成点

当前 `competitor_discovery.py` 的 `search_by_keywords()` 在 Mock 模式下直接匹配 `MOCK_CANDIDATES`。P2-2 实现后：

```python
# competitor_discovery.py 修改
def search_by_keywords(self, keywords: list[str]) -> list[dict]:
    if self.mode == "mock":
        return self._mock_search(keywords)
    elif self.mode == "public":
        # 委托给 PublicSearchCollector
        from douyin_public_collector import DouyinPublicCollector
        collector = DouyinPublicCollector()
        results = []
        for kw in keywords:
            for platform in ["douyin", "xiaohongshu"]:
                items = collector.search_by_keywords(kw, platform, depth=30)
                results.extend([item.to_dict() for item in items])
        return results
    else:
        return []
```

---

## 四、Public 模式的技术约束

### 4.1 公开数据边界

| 允许 | 禁止 |
|------|------|
| 平台搜索框公开结果 | 登录态专属内容 |
| 账号主页公开信息 | 私信/粉丝群/付费内容 |
| 作品列表公开标题 | 非公开视频/笔记 |
| 评论区公开内容 | 需登录才能查看的评论 |
| 按正常用户频率访问 | 高频批量请求 |

### 4.2 速率限制（Public 模式）

| 平台 | 搜索间隔 | 页面访问间隔 | 单次最大深度 |
|------|:--:|:--:|:--:|
| 抖音 | ≥5s | ≥3s | 50条 |
| 小红书 | ≥8s | ≥5s | 30条 |
| 快手 | ≥5s | ≥3s | 30条 |
| 视频号 | 不采集 | — | — |

### 4.3 反爬对抗

| 层级 | 策略 |
|:--:|------|
| 1 | 随机 User-Agent 轮换 |
| 2 | 请求间隔随机抖动 (±20%) |
| 3 | 间歇休息（每30次请求休息 60-120s） |
| 4 | 同一平台并发≤1 |
| 5 | 固定 IP，不切换代理 |

---

## 五、需要新增/修改的文件

### 5.1 新增文件

| # | 文件 | 说明 |
|:--:|------|------|
| 1 | `08_SYSTEM/scripts/public_search_base.py` | PublicSearchCollector 抽象基类 |
| 2 | `08_SYSTEM/scripts/douyin_public_collector.py` | 抖音公开搜索实现 |
| 3 | `10_AI_AUTOMATION_ENGINE/tests/test_public_search.py` | 测试 |

### 5.2 修改文件

| # | 文件 | 修改 |
|:--:|------|:--:|
| 1 | `platform_adapter.py` | +public 模式路由，+DouyinPublicCollector 注册 |
| 2 | `competitor_discovery.py` | `search_by_keywords()` 增加 public 模式委托 |
| 3 | `douyin_live_collector.py` | 重命名 → `douyin_public_collector.py`，接口对齐 |

### 5.3 不改文件

| 文件 | 原因 |
|------|------|
| `BaseCollector` / `CommentRecord` | P0 抽象，不依赖搜索模式 |
| `LiveCollectorBase` / `RateLimiter` | 速率限制适用 public 模式 |
| `keyword_expander.py` | 已就绪，输出搜索矩阵 |
| `competitor_discovery.py` 评分/入库 | 不变，仅 search 入口增加 public 委托 |
| `Pipeline` 10步 | P0 固化 |
| `TaskManager` / `Scheduler` | P1 固化 |

---

## 六、PublicSearchCollector 抽象基类

```python
class PublicSearchCollector(ABC):
    """平台公开搜索采集器抽象基类。

    所有平台 Public Collector 必须实现此接口。
    与 BaseCollector 互补 —— BaseCollector 管评论采集，本类管账号/视频发现。
    """

    platform_name: str = ""

    @abstractmethod
    def search_by_keywords(
        self, keyword: str, depth: int = 30
    ) -> list[SearchResultItem]:
        """平台搜索框 → 搜索结果解析。"""
        ...

    @abstractmethod
    def discover_account(
        self, account_id: str
    ) -> AccountDetail | None:
        """账号主页 → 账号详情提取。"""
        ...

    @abstractmethod
    def discover_videos(
        self, account_id: str, time_range_days: int = 30, limit: int = 10
    ) -> list[VideoCandidate]:
        """作品列表 → 视频候选提取。"""
        ...

    # 通用能力
    def _rate_limit_check(self, platform: str) -> None:
        """速率限制检查。"""
        ...

    def _validate_result(self, item: SearchResultItem) -> bool:
        """搜索结果基础校验。"""
        if not item.account_id or not item.account_name:
            return False
        return True
```

---

## 七、DouyinPublicCollector 桩实现（P2-2 第一阶段）

```python
class DouyinPublicCollector(PublicSearchCollector):
    """抖音公开搜索采集器。

    P2-2 第一阶段: Mock 模拟公开搜索（从预置候选库返回）。
    P2-3: 替换为真实页面解析。
    """

    def search_by_keywords(self, keyword: str, depth: int = 30) -> list[SearchResultItem]:
        """Mock: 从 MOCK_CANDIDATES 匹配。"""
        results = []
        for c in MOCK_CANDIDATES:
            if c["platform"] != "douyin":
                continue
            if keyword in c.get("discovery_keyword", "") or any(
                keyword in t for t in c.get("content_sample", [])
            ):
                results.append(SearchResultItem(
                    platform="douyin",
                    account_id=c["account_id"],
                    account_name=c["account_name"],
                    account_url=c["account_url"],
                    bio_snippet=c.get("bio", ""),
                    follower_count=c.get("follower_count", 0),
                    ip_location=c.get("ip_location", ""),
                    discovery_keyword=keyword,
                    source_type="search",
                ))
        return results[:depth]

    def discover_account(self, account_id: str) -> AccountDetail | None:
        """Mock: 从 MOCK_CANDIDATES 返回预置详情。"""
        ...

    def discover_videos(self, account_id: str, ...) -> list[VideoCandidate]:
        """Mock: 从 MOCK_CANDIDATES.content_sample 生成视频候选。"""
        ...
```

---

## 八、实施路线

| 阶段 | 内容 | 依赖 |
|:--:|------|:--:|
| **当前** | 接口设计 (本文档) | — |
| P2-2a | `public_search_base.py` + `DouyinPublicCollector` 桩 | 本文档 |
| P2-2b | 集成到 `platform_adapter.py` (public 路由) | P2-2a |
| P2-2c | 集成到 `competitor_discovery.py` (search 委托) | P2-2b |
| P2-2d | 测试: 全链路 Mock → Public 搜索验证 | P2-2c |
| P2-3 | 替换 Mock 为真实页面解析 (浏览器/HTML) | P2-2d ✓ |

---

## 版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-20 | Public Search Collector 接口设计：三接口/三模式/降级链/文件清单 |
