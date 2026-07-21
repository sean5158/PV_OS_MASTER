# Phase 3-2.2 Coding Report — Public Parser Core

**版本**: V1.0
**日期**: 2026-07-21
**状态**: ✅ 完成
**项目**: PV_OS V3.2

---

## 一、概述

Phase 3-2.2 实现了 Public Parser Core，基于 Phase 3-2.1 的设计文档，在 `douyin_page_parser.py` 中新增了 Public 模式解析能力。

### 核心交付

| 组件 | 文件 | 变更类型 |
|------|------|:--:|
| `PublicExtractionStrategy` | `douyin_page_parser.py` | 新增 |
| `AccountParser` | `douyin_page_parser.py` | 新增 |
| `VideoParser` | `douyin_page_parser.py` | 新增 |
| `CommentParser` | `douyin_page_parser.py` | 新增 |
| `DouyinPageParser` 模式路由 | `douyin_page_parser.py` | 修改 |
| Collector `_ensure_parser` | `douyin_public_collector.py` | 修改 |

---

## 二、实现细节

### 2.1 PublicExtractionStrategy

**职责**: 从公开 HTML 提取 `RENDER_DATA` JSON，标准化字段。

**关键方法**:
- `extract_render_data(html)` → `dict` — 从 `<script id="RENDER_DATA">` 提取 JSON
- `extract_account_fields(render_data)` → `dict` — 多路径适配账号字段
- `extract_video_fields(render_data)` → `list[dict]` — 视频列表提取
- `extract_comment_fields(render_data)` → `list[dict]` — 评论列表提取

**多路径适配**:
- 账号: `serverRouter.UserModule.user_info` → `serverRouter.UserPageData.user` → `userInfo.user` → `user`
- 视频: `serverRouter.UserPageData.aweme_list` → `aweme_list`
- 评论: `serverRouter.CommentData.comments` → `comments`

**字段标准化**:
- `_normalize_count()`: 支持纯数字、逗号分隔、"3.5w" 万单位
- `_normalize_timestamp()`: 支持秒/毫秒时间戳 → ISO 格式
- `_safe_get()`: 安全嵌套字典取值

### 2.2 AccountParser

输出: `account_id`, `account_name`, `account_url`, `platform`, `follower_count`, `account_category`

### 2.3 VideoParser

输出: `video_id`, `video_title`, `video_url`, `author_id`, `publish_time`, `like_count`, `comment_count`, `collect_count`

### 2.4 CommentParser

输出: `comment_id`, `comment_text`, `comment_time`, `user_id`, `user_name`, `user_profile_url`

### 2.5 模式路由

`DouyinPageParser` 现在支持 `mode` 参数:
- `mode="mock"` — 原始 HTML 模板解析
- `mode="public"` — 检测 `RENDER_DATA` 存在则用 Public 策略，否则降级 Mock

每个 `parse_*` 方法内部路由:
```
parse_search_results → _parse_search_public / _parse_search_mock
parse_account_page   → _parse_account_public / _parse_account_mock
parse_video_list     → _parse_videos_public / _parse_videos_mock
parse_comments       → _parse_comments_public / _parse_comments_mock
```

### 2.6 降级机制

Public 解析失败时自动降级 Mock:
- `RENDER_DATA` 标签不存在 → Mock
- JSON 解析失败 → Mock
- 字段提取异常 → Mock
- 降级仅为空 HTML → 返回 `[]` 或 `None`

---

## 三、三模式兼容

| 模式 | Fetcher | Parser 策略 | 降级 |
|------|---------|------------|:--:|
| Mock | `MockPageFetcher` | class 属性解析 | N/A |
| Public | `PublicPageFetcher` | `PublicExtractionStrategy` | → Mock |
| Official | API (未来) | 降级 Mock | → Mock |

**Mock/Public/Official 在映射层及之后完全共享**，仅 "HTML → 字段提取" 逻辑不同。

---

## 四、测试结果

### 新增测试

| 测试文件 | 用例数 | 状态 |
|------|:--:|:--:|
| `test_public_extraction_strategy.py` | 36 | ✅ 通过 |
| `test_account_parser.py` | 16 | ✅ 通过 |
| `test_video_parser.py` | 17 | ✅ 通过 |
| `test_comment_parser.py` | 19 | ✅ 通过 |

### 全量回归

```
761 passed in 17.16s (0 failures)
```

### 覆盖率

| 区域 | 覆盖内容 |
|------|------|
| RENDER_DATA 提取 | 正常/不存在/空/截断/非法 JSON |
| 字段标准化 | count整数/浮点/万单位/空/none, timestamp秒/毫秒/零/字符串 |
| AccountParser | 正常/字段缺失/非账号页/多路径/认证 |
| VideoParser | 正常/多视频/空列表/字段缺失/非列表 |
| CommentParser | 正常/多条/空/缺少user/缺少avatar/备选路径 |
| 降级 | Public→Mock 降级/空HTML/异常处理 |
| 三模式 | 输出字段一致性验证 |

---

## 五、禁止修改确认

| 模块 | 状态 |
|------|:--:|
| Agent (`03_AI_AGENT/`) | ✅ 未修改 |
| Pipeline (`10_AI_AUTOMATION_ENGINE/workflows/`) | ✅ 未修改 |
| CRM (`05_CUSTOMER_CRM/`) | ✅ 未修改 |
| Business Rules | ✅ 未修改 |

---

## 六、文件变更清单

```
修改:
  08_SYSTEM/scripts/douyin_page_parser.py      (+456 lines, V3.2 mode routing)
  08_SYSTEM/scripts/douyin_public_collector.py  (1 line: mode 透传到 parser)

新增:
  10_AI_AUTOMATION_ENGINE/tests/test_public_extraction_strategy.py
  10_AI_AUTOMATION_ENGINE/tests/test_account_parser.py
  10_AI_AUTOMATION_ENGINE/tests/test_video_parser.py
  10_AI_AUTOMATION_ENGINE/tests/test_comment_parser.py
```

---

## 七、下一步

Phase 3-2.3: Account — 真实账号页面解析验证
Phase 3-2.4: Video — 真实视频列表解析验证
Phase 3-2.5: Comment — 真实评论列表解析验证
Phase 3-2.6: Integration — 端到端连线 Fetcher→Parser→Storage→Pipeline
