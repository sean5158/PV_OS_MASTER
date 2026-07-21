# Phase 3-2.1 抖音公开页面解析器设计

**版本**: V1.0
**日期**: 2026-07-21
**状态**: 设计阶段 — 不执行代码
**依赖**: PV_OS_V3.2_ARCHITECTURE_LOCK.md、Phase3-2 PublicPageFetcher（已完成）

---

## 一、问题定义

### 1.1 当前状态

Phase 3-2 已实现 `PublicPageFetcher`，可向 `www.douyin.com` 发送真实 HTTP GET 请求，获取公开搜索页、账号主页、作品列表页的原始 HTML。

**当前问题**: `DouyinPageParser` 基于 P2-3 阶段设计的 Mock HTML 模板（`_SEARCH_CARD_TEMPLATE` 等 `<div class="search-card">` 结构），与抖音真实页面结构（React SSR 渲染 + `RENDER_DATA` 内嵌 JSON）不匹配，导致解析返回 0 结果。

### 1.2 抖音真实页面结构分析

抖音 Web 版公开页面不是传统 HTML 模板。其核心数据通过以下方式承载：

```
┌────────────────────────────────────────────────────────────┐
│  抖音公开页面 HTML (SSR)                                    │
│                                                            │
│  <html>                                                     │
│  <head>                                                     │
│    <!-- 页面标题等 meta -->                                  │
│  </head>                                                    │
│  <body>                                                     │
│    <!-- React SSR 渲染的 HTML 骨架（可能不完整）-->          │
│                                                            │
│    <script id="RENDER_DATA" type="application/json">        │
│      {                                                      │
│        "app": {...},                                        │
│        "serverRouter": {                                    │
│          "/search/user": {                                  │
│            "user_list": [  ← 搜索结果在这里                  │
│              {                                              │
│                "user_info": {                               │
│                  "uid": "xxx",                              │
│                  "nickname": "成都光伏老王",                 │
│                  "signature": "成都本地光伏安装...",         │
│                  "follower_count": 35000,                   │
│                  "aweme_count": 156,                        │
│                  "total_favorited": 50000                   │
│                },                                           │
│                "live_info": {...},                          │
│                "enterprise_info": {...}                     │
│              },                                             │
│              ...                                            │
│            ]                                                │
│          }                                                  │
│        }                                                    │
│      }                                                      │
│    </script>                                                │
│  </body>                                                    │
│  </html>                                                    │
└────────────────────────────────────────────────────────────┘
```

**关键发现**:
- 数据存放于 `<script id="RENDER_DATA">` 内的内嵌 JSON
- 不同页面类型 (`/search/user`、`/user/{uid}`) 有不同的 JSON 结构
- 部分字段使用数字枚举（如 `account_type` 用 1/2/3 而非字符串）
- 昵称、简介等可能被编码或截断

---

## 二、架构设计

### 2.1 核心原则

```
┌─────────────────────────────────────────────────────────────────┐
│                        Parser 核心原则                            │
│                                                                  │
│  1. 只解析公开页面 HTML，不调用 API                               │
│  2. 优雅降级：字段缺失用默认值，不抛异常                           │
│  3. 三模式兼容：Mock/Public/Official 共用同一输出格式              │
│  4. 策略模式：不同页面结构用不同策略，策略可插拔                   │
│  5. 信号检测与解析分离：解析器负责提取字段，信号检测器负责业务判断  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 解析器分层

```
                        ┌──────────────────┐
                        │   HTML 原始输入    │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Extraction Layer │  提取层
                        │  从 HTML 中提取   │
                        │  RENDER_DATA JSON │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Strategy Layer  │  策略层
                        │  按页面类型选择   │
                        │  对应的解析策略   │
                        │                  │
                        │  ├─ SearchStrategy│
                        │  ├─ AccountStrategy│
                        │  ├─ VideoStrategy │
                        │  └─ CommentStrategy│
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Mapping Layer   │  映射层
                        │  平台字段 →      │
                        │  PV_OS统一字段   │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Validation Layer│  校验层
                        │  必填字段检查    │
                        │  类型转换        │
                        │  边界值处理      │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  Signal Detection│  信号层（现有，不变）
                        │  premium_signals │
                        │  region_signals  │
                        │  housing_signal  │
                        └────────┬─────────┘
                                 │
                        ┌────────▼─────────┐
                        │  结构化输出      │
                        │  SearchResultItem│
                        │  AccountDetail   │
                        │  VideoCandidate  │
                        │  CommentRecord   │
                        └──────────────────┘
```

### 2.3 三模式兼容架构

```
DouyinPageParser
    │
    ├── mode == "mock"
    │   └── MockExtractionStrategy
    │       └── 正则匹配 class="search-card" 等 Mock 模板
    │
    ├── mode == "public"
    │   └── PublicExtractionStrategy
    │       ├── __RENDER_DATA__ 提取
    │       ├── JSON 路径解析
    │       └── 失败 → 降级 MockExtractionStrategy
    │
    └── mode == "official"
        └── OfficialExtractionStrategy（未来）
            └── 直接解析 API JSON Response
```

---

## 三、Parser 详细设计

### 3.1 Account Parser（账号解析器）

#### 输入

```
来源: PageFetcher → 抖音账号主页 HTML
URL:  https://www.douyin.com/user/{account_id}
```

#### 提取路径（公开页面）

```json
// <script id="RENDER_DATA"> 中的 JSON 路径
{
  "serverRouter": {
    "/user/profile": {
      "user": {
        "uid": "reg_install_001",        → account_id
        "nickname": "成都光伏老王",        → account_name
        "signature": "成都本地光伏安装团队", → bio
        "follower_count": 35000,          → follower_count
        "aweme_count": 156,               → content_count
        "total_favorited": 50000,         → total_likes
        "ip_location": "四川成都",         → ip_location
        "avatar_medium": {                → avatar_url
          "url_list": ["https://..."]
        },
        "enterprise_verify_info": {       → verified
          "enterprise_name": "xxx有限公司"
        },
        "custom_verify": "光伏安装专家"    → verified_tag
      }
    }
  }
}
```

#### 输出

| PV_OS 字段 | 平台字段 | 降级默认值 |
|------|------|------|
| `account_id` | `uid` | "" |
| `account_name` | `nickname` | "未知用户" |
| `account_url` | 构建: `https://douyin.com/user/{uid}` | "" |
| `platform` | 固定 "douyin" | "douyin" |
| `follower_count` | `follower_count` | 0 |
| `content_count` | `aweme_count` | 0 |
| `bio` | `signature` | "" |
| `ip_location` | `ip_location` | "" |
| `verified` | `enterprise_verify_info` 存在 | False |
| `avatar_url` | `avatar_medium.url_list[0]` | "" |
| `account_category` | 信号检测（见 §四.1） | "unknown" |

#### 解析失败处理

| 失败场景 | 处理 |
|------|------|
| HTML 无 `RENDER_DATA` | 降级到 MockExtractionStrategy |
| JSON 解析异常 | 记录日志，返回空 AccountDetail |
| `uid` 缺失 | 返回 None（无 UID 无法后续操作） |
| `nickname` 缺失 | 用 "未知用户" + uid[:8] |
| 所有数值字段缺失 | 使用 0 |

---

### 3.2 Video Parser（视频解析器）

#### 输入

```
来源: PageFetcher → 抖音账号作品列表页 HTML
URL:  https://www.douyin.com/user/{account_id}
```

#### 提取路径（公开页面）

```json
// <script id="RENDER_DATA"> 中的 JSON 路径
{
  "serverRouter": {
    "/user/profile": {
      "user": {
        "post": {
          "data": [
            {
              "aweme": {
                "aweme_id": "v_001",                    → video_id
                "desc": "别墅光伏安装实拍",              → video_title
                "create_time": 1758163200,              → publish_time (unix)
                "author": {
                  "uid": "reg_install_001",             → author_id
                  "nickname": "成都光伏老王"             → author_name
                },
                "statistics": {
                  "digg_count": 1520,                   → like_count
                  "comment_count": 85,                  → comment_count
                  "collect_count": 320,                 → collect_count
                  "share_count": 45                     → share_count
                },
                "video": {
                  "duration": 45000,                    → duration_ms
                  "cover": {
                    "url_list": ["https://..."]          → cover_url
                  }
                }
              }
            },
            // ... 更多视频
          ],
          "has_more": true,                             → has_more
          "max_cursor": 20,                             → next_cursor
          "min_cursor": 0
        }
      }
    }
  }
}
```

#### 输出

| PV_OS 字段 | 平台字段 | 降级默认值 |
|------|------|------|
| `video_id` | `aweme.aweme_id` | "" |
| `video_title` | `aweme.desc` | "无标题" |
| `video_url` | 构建: `https://douyin.com/video/{aweme_id}` | "" |
| `publish_time` | `aweme.create_time` (unix→ISO) | `collected_time` |
| `author_id` | `aweme.author.uid` | 使用 account_id |
| `author_name` | `aweme.author.nickname` | "" |
| `like_count` | `aweme.statistics.digg_count` | 0 |
| `comment_count` | `aweme.statistics.comment_count` | 0 |
| `collect_count` | `aweme.statistics.collect_count` | 0 |
| `share_count` | `aweme.statistics.share_count` | 0 |
| `duration_seconds` | `aweme.video.duration / 1000` | 0 |
| `cover_url` | `aweme.video.cover.url_list[0]` | "" |

#### 分页支持

| 字段 | 来源 | 用途 |
|------|------|------|
| `has_more` | `post.has_more` | 是否还有更多视频 |
| `next_cursor` | `post.max_cursor` | 下一页游标 |
| `min_cursor` | `post.min_cursor` | 当前页游标 |

#### 解析失败处理

| 失败场景 | 处理 |
|------|------|
| `post.data` 不存在 | 返回空列表 |
| 单个视频字段缺失 | 使用降级默认值 |
| JSON 解析失败 | 降级 MockExtractionStrategy |

---

### 3.3 Comment Parser（评论解析器）

#### 输入

```
来源: PageFetcher → 抖音视频详情页 HTML
URL:  https://www.douyin.com/video/{video_id}
```

#### 提取路径（公开页面）

```json
// <script id="RENDER_DATA"> 中的 JSON 路径
{
  "serverRouter": {
    "/video/{video_id}": {
      "aweme": {
        "detail": {
          "aweme_id": "v_001",
          "desc": "别墅光伏安装实拍",
          "author": {
            "uid": "reg_install_001",
            "nickname": "成都光伏老王"
          }
        }
      },
      "comment": {
        "data": [
          {
            "cid": "cmt_001",                            → comment_id
            "text": "我家在成都锦江区，别墅想装光伏，能报个价吗？", → comment_text
            "create_time": 1758163200,                   → comment_time (unix)
            "user": {
              "uid": "user_001",                         → user_id
              "nickname": "成都业主刘先生",                → user_name
              "signature": "热爱生活的成都人",            → user_signature
              "avatar_medium": {
                "url_list": ["https://..."]               → user_avatar
              }
            },
            "ip_label": "四川",                           → ip_location
            "digg_count": 12,                             → comment_like_count
            "reply_comment_total": 3,                     → reply_count
            "status": 1                                   → status (1=正常)
          },
          // ... 更多评论
        ],
        "has_more": true,
        "cursor": 20
      }
    }
  }
}
```

#### 输出

| PV_OS 字段 | 平台字段 | 降级默认值 |
|------|------|------|
| `comment_id` | `cid` | "" |
| `comment_text` | `text` | "" |
| `comment_time` | `create_time` (unix→ISO) | `collected_time` |
| `user_id` | `user.uid` | "" |
| `user_name` | `user.nickname` | "抖音用户" |
| `user_profile_url` | 构建: `https://douyin.com/user/{uid}` | "" |
| `ip_location` | `ip_label` | "" |
| `comment_like_count` | `digg_count` | 0 |
| `reply_count` | `reply_comment_total` | 0 |
| `source_video_id` | 采集时注入 | "" |
| `source_video_title` | `aweme.detail.desc` | "" |
| `video_author_id` | `aweme.detail.author.uid` | "" |
| `video_author_name` | `aweme.detail.author.nickname` | "" |

#### 分页支持

| 字段 | 来源 | 用途 |
|------|------|------|
| `has_more` | `comment.has_more` | 是否还有更多评论 |
| `cursor` | `comment.cursor` | 下一页游标 |

#### 解析失败处理

| 失败场景 | 处理 |
|------|------|
| `comment.data` 不存在 | 返回空列表 |
| `cid` 缺失 | 跳过该条评论 |
| `text` 缺失 | 跳过该条评论 |
| `user.uid` 缺失 | 保留评论，user_id="" |
| JSON 解析失败 | 降级 MockExtractionStrategy |

---

## 四、账号分类与信号检测

### 4.1 账号分类规则（account_category）

参考 `COMPETITOR_ACCOUNT_MODEL.md` §一：

| category | 判定条件 | 示例 |
|------|------|------|
| `personal_pv_blogger` | 个人IP + 光伏/新能源/发电玻璃内容 > 50% | "成都光伏老王" |
| `pv_company` | 企业认证 + 安装/产品/案例 | "正泰安能" |
| `renovation` | 装修/别墅改造 + 光伏相关内容 | "别墅光伏改造日记" |
| `industry_related` | 智能家居/建筑/新能源综合 | "新能源观察" |
| `unknown` | 无法判定 | — |

#### 判定信号

| 信号来源 | 信号 | 权重 |
|------|------|:--:|
| 企业认证 | `enterprise_verify_info` 存在 | +40 |
| 昵称关键词 | 光伏/新能源/太阳能/发电玻璃 | +20 |
| 简介关键词 | 安装/施工/案例/报价 | +15 |
| 视频内容比例 | 家庭光伏 > 50% | +25 |
| 认证标签 | "光伏安装专家"等 | +10 |

### 4.2 已有信号检测器（不变）

当前 `douyin_page_parser.py` 中的信号检测函数保持不动：

- `detect_premium_signals()` — 高端住宅信号（别墅/叠拼/阳光房等）
- `detect_region_signals()` — 区域信号（成都/重庆/贵阳等）
- `detect_housing_signal()` — 房屋场景信号
- `is_rural()` — 农村内容排除

---

## 五、完整数据流

### 5.1 Parser → Storage → Pipeline 数据流

```
┌──────────────────────────────────────────────────────────────────┐
│                     Stage 1: 公开页面获取                         │
│                                                                  │
│  PublicPageFetcher                                               │
│  ├── fetch_search_page("别墅光伏", "douyin")                     │
│  ├── fetch_account_page("reg_install_001", "douyin")             │
│  └── fetch_video_list_page("reg_install_001", "douyin")          │
│                                                                  │
│  输出: 原始 HTML 字符串                                           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Stage 2: Parser 解析                          │
│                                                                  │
│  DouyinPageParser (mode=public)                                  │
│  ├── PublicExtractionStrategy._extract_render_data(html)          │
│  │   └── 正则提取 <script id="RENDER_DATA"> → JSON.parse         │
│  │                                                               │
│  ├── parse_search_results(html, keyword)                         │
│  │   └── serverRouter["/search/user"]["user_list"]               │
│  │   └── 映射 → SearchResultItem[]                                │
│  │                                                               │
│  ├── parse_account_page(html)                                    │
│  │   └── serverRouter["/user/profile"]["user"]                   │
│  │   └── 映射 → AccountDetail                                     │
│  │                                                               │
│  ├── parse_video_list(html)                                      │
│  │   └── serverRouter["/user/profile"]["user"]["post"]["data"]   │
│  │   └── 映射 → VideoCandidate[]                                  │
│  │                                                               │
│  └── parse_comments(html)                          🆕            │
│      └── serverRouter["/video/{id}"]["comment"]["data"]           │
│      └── 映射 → CommentRecord[]                                   │
│                                                                  │
│  输出: 结构化数据对象                                              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Stage 3: 信号检测                             │
│                                                                  │
│  对解析结果附加业务信号:                                           │
│  ├── premium_signals (高端住宅信号)                                │
│  ├── region_signals (区域信号)                                    │
│  ├── housing_signal (房屋场景)                                    │
│  ├── is_rural (农村排除标记)                                      │
│  └── account_category (账号分类)                                  │
│                                                                  │
│  输出: 带业务标签的结构化数据                                       │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Stage 4: Asset Storage                        │
│                                                                  │
│  AccountDetail → competitor_master.csv                            │
│  VideoCandidate → video_asset_store.csv                           │
│  CommentRecord → comment_asset_library.csv                        │
│                                                                  │
│  输出: CSV/JSON 持久化资产                                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Stage 5: Pipeline                             │
│                                                                  │
│  data_cleaner → comment_analyzer → lead_scoring_agent → CRM      │
│                                                                  │
│  （Stage 5 保持不变，不修改）                                      │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 三模式数据流对比

| 阶段 | Mock | Public | Official |
|------|------|------|------|
| 页面获取 | `MockPageFetcher` (预置HTML) | `PublicPageFetcher` (HTTP GET) | `OfficialFetcher` (API) |
| HTML提取 | class 正则 | `RENDER_DATA` JSON | JSON Response |
| 策略层 | `MockExtractionStrategy` | `PublicExtractionStrategy` | `OfficialExtractionStrategy` |
| 映射层 | 相同 | 相同 | 相同 |
| 校验层 | 相同 | 相同 | 相同 |
| 信号检测 | 相同 | 相同 | 相同 |
| 输出格式 | `SearchResultItem` | `SearchResultItem` | `SearchResultItem` |

**关键**: 三种模式在映射层及之后完全共享。仅 "HTML → 字段提取" 逻辑不同。

---

## 六、实施计划

### 6.1 阶段划分

| 阶段 | 内容 | 预计工作量 |
|:--:|------|:--:|
| **3-2.1 Design** | 本文档 — 架构设计 | ✅ 完成 |
| **3-2.2 Core** | 实现 `PublicExtractionStrategy`（RENDER_DATA提取 + JSON 路径） | 1天 |
| **3-2.3 Account** | 实现真实账号页面解析 (parse_account_page real mode) | 0.5天 |
| **3-2.4 Video** | 实现真实视频列表解析 (parse_video_list real mode) | 0.5天 |
| **3-2.5 Comment** | 实现真实评论列表解析 (parse_comments 新增) | 1天 |
| **3-2.6 Integration** | 端到端连线: Fetcher→Parser→Storage→Pipeline → 人工验证 | 0.5天 |

### 6.2 文件变更计划

| 文件 | 变更类型 | 变更内容 |
|------|:--:|------|
| `douyin_page_parser.py` | 修改 | + `PublicExtractionStrategy` 类 |
| `douyin_page_parser.py` | 修改 | `DouyinPageParser` 增加 mode 参数 |
| `douyin_page_parser.py` | 新增 | `parse_comments(html)` 方法 |
| `douyin_page_parser.py` | 修改 | `parse_search_results / parse_account_page / parse_video_list` 增加 public 分支 |
| `public_search_base.py` | 不变 | CommentRecord 已有完整字段 |
| `douyin_public_collector.py` | 不变 | `_public_search / _public_discover_account` 已连线 |
| `test_public_parser.py` | 新增 | Public 模式解析专项测试 (~30 用例) |

### 6.3 测试计划

| # | 测试类别 | 用例数 | 内容 |
|:--:|------|:--:|------|
| 1 | RENDER_DATA 提取 | 5 | JSON 存在/不存在/截断/编码 |
| 2 | Account Parser | 8 | 正常/字段缺失/非用户页/空数据 |
| 3 | Video Parser | 8 | 正常/分页/空数据/格式异常 |
| 4 | Comment Parser | 8 | 正常/分页/字段缺失/无评论 |
| 5 | 三模式兼容 | 4 | Mock/Public/Official 输出一致 |
| 6 | 降级测试 | 3 | Public 失败→Mock 降级 |
| 7 | 回归 | 5 | 已有 33 个 P3-2 测试继续通过 |

---

## 七、风险与应对

### 7.1 技术风险

| 风险 | 概率 | 应对 |
|------|:--:|------|
| 抖音页面结构变化（RENDER_DATA 字段重命名） | 中 | 策略层可插拔，新增策略类适配新结构 |
| 抖音反爬增强（验证码/频率限制） | 高 | PublicPageFetcher 已有速率限制和 UA 轮换 |
| RENDER_DATA 内容为空（SPA 已接管） | 中 | 降级 MockStrategy |
| JSON 太大导致解析 OOM | 低 | 设置最大解析 size (5MB)，超出降级 |
| 某些视频/评论无公开数据 | 中 | 空值返回空列表，不抛异常 |

### 7.2 合规风险

| 约束 | 保障 |
|------|------|
| 不使用 API | Parser 只解析公开 HTML，不调用 API endpoint |
| 不携带 Cookie | `PublicPageFetcher` 不发送 Cookie |
| 速率限制 | 5s 间隔 + 100次/天（P3-2 阶段） |
| 不采集私密数据 | 只提取 `RENDER_DATA` 中公开字段，不处理 `followers_detail` 等私密数据 |

---

## 八、与现有规则的对齐

| 规则来源 | 要求 | 对齐状态 |
|------|------|:--:|
| `PV_OS_P2_ARCHITECTURE_DESIGN.md V2.1` | "公开数据采集，非API调用" | ✅ PublicExtractionStrategy |
| `COMPETITOR_DISCOVERY_ALGORITHM.md` | "关键词→搜索→发现→采集" | ✅ search → parse_search_results |
| `COMMENT_COLLECTOR_AGENT_DESIGN.md` | "采集原始评论，不做价值判断" | ✅ Parser 只提取字段 |
| `COMPETITOR_ACCOUNT_MODEL.md` | "全国发现，区域筛选" | ✅ 信号检测层附加 region_signals |
| `PV_OS_GOVERNANCE_RULES.md` | "商业价值第一" | ✅ Parser 输出直接对接 Lead 发现 |
| `PV_OS_AI_RULES.md` | "不修改已有 Agent/Pipeline" | ✅ 仅修改 Parser |

---

## 九、版本记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-07-21 | Phase 3-2.1 Douyin Public Parser 设计：五层解析架构、三模式兼容、Account/Video/Comment 三 Parser |
