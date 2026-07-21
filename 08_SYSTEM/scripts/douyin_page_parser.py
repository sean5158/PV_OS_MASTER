"""PV_OS 抖音公开页面解析器。

将 MockPageFetcher（或未来真实 PageFetcher）返回的 HTML 解析为结构化数据。
输出: SearchResultItem / AccountDetail / VideoCandidate。

规则依据:
- COMPETITOR_DISCOVERY_ALGORITHM.md §二.4: 抖音搜索流程
- COMMENT_COLLECTOR_AGENT_DESIGN.md §二.1: 抖音平台特征
- PV_OS_P2_ARCHITECTURE_DESIGN.md V2.1: 公开搜索定位

解析策略:
- 基于 class/data 属性提取 (模拟抖音公开页面 DOM 结构)
- 优雅降级: 字段缺失 → 使用默认值，不抛异常
- 业务信号检测: 从文本中提取 premium_signals / region_signals / housing_signal
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from public_search_base import (  # noqa: E402
    SearchResultItem,
    AccountDetail,
    VideoCandidate,
)

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# 业务信号检测器
# ══════════════════════════════════════════════════════════════════════

PREMIUM_KEYWORDS = [
    "别墅", "叠拼", "阳光房", "露台", "花园洋房",
    "民宿", "酒店", "茶楼", "独栋", "联排", "大平层",
]

REGION_KEYWORDS = [
    "成都", "重庆", "贵阳", "绵阳", "德阳", "遵义",
    "渝北", "渝中", "南岸", "江北", "锦江", "武侯",
    "高新", "天府", "双流", "龙泉", "温江",
]

HOUSING_SIGNAL_MAP = {
    "别墅": "别墅", "叠拼": "叠拼", "阳光房": "阳光房",
    "露台": "露台", "花园洋房": "花园洋房",
    "民宿": "民宿", "酒店": "酒店", "茶楼": "茶楼",
    "独栋": "别墅", "联排": "别墅", "大平层": "大平层",
}

RURAL_EXCLUDE_KEYWORDS = ["农村", "扶贫", "村村通", "惠农"]


def detect_premium_signals(text: str) -> list[str]:
    """从文本中检测高端住宅信号。"""
    found: list[str] = []
    for kw in PREMIUM_KEYWORDS:
        if kw in text:
            found.append(kw)
    return found


def detect_region_signals(text: str) -> list[str]:
    """从文本中检测区域信号。"""
    found: list[str] = []
    for kw in REGION_KEYWORDS:
        if kw in text:
            found.append(kw)
    return found


def detect_housing_signal(title: str) -> str:
    """从标题中检测房屋场景信号。"""
    for keyword, signal in sorted(
        HOUSING_SIGNAL_MAP.items(), key=lambda x: -len(x[0])
    ):
        if keyword in title:
            return signal
    return "普通住宅"


def is_rural(text: str) -> bool:
    """检测是否为农村内容。"""
    for kw in RURAL_EXCLUDE_KEYWORDS:
        if kw in text:
            return True
    return False


# ══════════════════════════════════════════════════════════════════════
# Phase 3-2.2: RENDER_DATA 提取与 JSON 解析
# ══════════════════════════════════════════════════════════════════════

_RENDER_DATA_PATTERN = re.compile(
    r'<script\s+id="RENDER_DATA"[^>]*type="application/json"[^>]*>'
    r'(.*?)'
    r'</script>',
    re.DOTALL,
)

MAX_RENDER_DATA_SIZE = 5 * 1024 * 1024  # 5MB


def _extract_render_data_json(html: str) -> dict[str, Any]:
    """从公开 HTML 中提取 RENDER_DATA 内嵌 JSON。

    Args:
        html: 原始 HTML 字符串

    Returns:
        解析后的 JSON 字典；提取或解析失败返回空字典
    """
    if not html:
        return {}

    if len(html) > MAX_RENDER_DATA_SIZE:
        logger.warning("HTML 过大 (%d bytes)，跳过 RENDER_DATA 提取", len(html))
        return {}

    match = _RENDER_DATA_PATTERN.search(html)
    if not match:
        logger.info("未找到 RENDER_DATA 标签")
        return {}

    raw_json = match.group(1).strip()
    if not raw_json:
        logger.info("RENDER_DATA 内容为空")
        return {}

    try:
        data = json.loads(raw_json)
        logger.info("RENDER_DATA 解析成功，顶层键: %s", list(data.keys())[:10])
        return data
    except json.JSONDecodeError as e:
        logger.warning("RENDER_DATA JSON 解析失败: %s", e)
        return {}


# ══════════════════════════════════════════════════════════════════════
# Phase 3-2.2: 字段标准化工具
# ══════════════════════════════════════════════════════════════════════

def _safe_get(d: dict, *keys: str, default: Any = "") -> Any:
    """安全获取嵌套字典值。"""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, {})
        else:
            return default
    return d if d != {} else default


def _normalize_count(value: Any) -> int:
    """标准化计数字段为整数。

    支持:
    - 纯数字: 12345 → 12345
    - 带逗号: "12,345" → 12345
    - 万单位: "3.5w" → 35000, "5W" → 50000
    """
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        # 处理 "万/w/W" 单位
        if s.lower().endswith("w"):
            try:
                return int(float(s[:-1]) * 10000)
            except (ValueError, TypeError):
                return 0
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return 0
    return 0


def _normalize_timestamp(value: Any) -> str:
    """标准化时间戳为 ISO 格式字符串。"""
    if isinstance(value, (int, float)):
        if value <= 0:
            return ""
        try:
            # 抖音使用毫秒时间戳
            if value > 1e12:
                value = value / 1000
            dt = datetime.fromtimestamp(value, tz=TZ_SHANGHAI)
            return dt.isoformat()
        except (ValueError, OSError):
            pass
    if isinstance(value, str):
        return value
    return ""


# ══════════════════════════════════════════════════════════════════════
# Phase 3-2.2: PublicExtractionStrategy
# ══════════════════════════════════════════════════════════════════════

class PublicExtractionStrategy:
    """公开 HTML 提取策略 — 从 RENDER_DATA JSON 中提取结构化字段。

    三模式之一（Mock/Public/Official），负责 "HTML → 字段提取"。
    映射层、校验层、信号检测层由 DouyinPageParser 复用。

    核心职责:
    - 从公开 HTML 提取 RENDER_DATA
    - JSON 解析
    - 字段标准化 (count → int, timestamp → ISO)
    """

    def extract_render_data(self, html: str) -> dict[str, Any]:
        """从 HTML 提取并解析 RENDER_DATA。"""
        return _extract_render_data_json(html)

    def extract_account_fields(
        self, render_data: dict[str, Any]
    ) -> dict[str, Any]:
        """从 RENDER_DATA 提取账号字段。

        适配抖音 /user/ 页面 JSON 结构:
        serverRouter.UserModule.user_info / serverRouter.UserPageData.user
        """
        user_info = (
            _safe_get(render_data, "serverRouter", "UserModule", "user_info")
            or _safe_get(render_data, "serverRouter", "UserPageData", "user")
            or _safe_get(render_data, "userInfo", "user")
            or _safe_get(render_data, "user")
        )

        return {
            "account_id": str(_safe_get(user_info, "uid", default="") or _safe_get(user_info, "sec_uid", default="")),
            "account_name": str(_safe_get(user_info, "nickname", default="") or _safe_get(user_info, "nick_name", default="")),
            "account_url": f"https://www.douyin.com/user/{_safe_get(user_info, 'sec_uid', default='')}" if _safe_get(user_info, "sec_uid") else "",
            "platform": "douyin",
            "follower_count": _normalize_count(_safe_get(user_info, "follower_count", default=0)),
            "account_category": str(_safe_get(user_info, "account_type_hint", default="") or _safe_get(user_info, "enterprise_info", "type", default="")),
            "bio": str(_safe_get(user_info, "signature", default="") or _safe_get(user_info, "bio", default="")),
            "content_count": _normalize_count(_safe_get(user_info, "aweme_count", default=0)),
            "verified": bool(_safe_get(user_info, "custom_verify", default="") or _safe_get(user_info, "enterprise_verify_reason", default="")),
            "ip_location": str(_safe_get(user_info, "ip_location", default="") or _safe_get(user_info, "city", default="")),
        }

    def extract_video_fields(
        self, render_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """从 RENDER_DATA 提取视频列表字段。

        适配抖音作品列表 JSON 结构:
        serverRouter.UserPageData.aweme_list[] (主路径)
        aweme_list[] (备选路径)
        """
        # 主路径
        aweme_list = _safe_get(render_data, "serverRouter", "UserPageData", "aweme_list", default=[])
        # 备选路径: 主路径为空或非列表时尝试
        if not isinstance(aweme_list, list) or not aweme_list:
            aweme_list = _safe_get(render_data, "aweme_list", default=[])
        if not isinstance(aweme_list, list):
            return []

        videos: list[dict[str, Any]] = []
        for aweme in aweme_list:
            if not isinstance(aweme, dict):
                continue
            videos.append({
                "video_id": str(_safe_get(aweme, "aweme_id", default="")),
                "video_title": str(_safe_get(aweme, "desc", default="")),
                "video_url": f"https://www.douyin.com/video/{_safe_get(aweme, 'aweme_id', default='')}" if _safe_get(aweme, "aweme_id") else "",
                "author_id": str(_safe_get(aweme, "author", "uid", default="") or _safe_get(aweme, "author_user_id", default="")),
                "publish_time": _normalize_timestamp(_safe_get(aweme, "create_time", default=0)),
                "like_count": _normalize_count(_safe_get(aweme, "statistics", "digg_count", default=0)),
                "comment_count": _normalize_count(_safe_get(aweme, "statistics", "comment_count", default=0)),
                "collect_count": _normalize_count(_safe_get(aweme, "statistics", "collect_count", default=0)),
            })

        return videos

    def extract_comment_fields(
        self, render_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """从 RENDER_DATA 提取评论列表字段。

        适配抖音评论 JSON 结构:
        serverRouter.CommentData.comments[]
        """
        comments_data = (
            _safe_get(render_data, "serverRouter", "CommentData", "comments", default=[])
            or _safe_get(render_data, "comments", default=[])
        )
        if not isinstance(comments_data, list):
            return []

        result: list[dict[str, Any]] = []
        for c in comments_data:
            if not isinstance(c, dict):
                continue
            user = c.get("user", {})
            avatar_url = ""
            if isinstance(user, dict):
                avatar_list = _safe_get(user, "avatar_thumb", "url_list", default=[])
                if isinstance(avatar_list, list) and avatar_list:
                    avatar_url = str(avatar_list[0])

            result.append({
                "comment_id": str(c.get("cid", "")),
                "comment_text": str(c.get("text", "")),
                "comment_time": _normalize_timestamp(c.get("create_time", 0)),
                "user_id": str(user.get("uid", "")) if isinstance(user, dict) else "",
                "user_name": str(user.get("nickname", "")) if isinstance(user, dict) else "",
                "user_profile_url": avatar_url,
            })

        return result


# ══════════════════════════════════════════════════════════════════════
# Phase 3-2.2: AccountParser
# ══════════════════════════════════════════════════════════════════════

class AccountParser:
    """账号解析器 — 从 RENDER_DATA 提取标准账号字段。

    输出:
    - account_id
    - account_name
    - account_url
    - platform
    - follower_count
    - account_category
    """

    def __init__(self, strategy: PublicExtractionStrategy | None = None) -> None:
        self._strategy = strategy or PublicExtractionStrategy()

    def parse(self, html: str) -> dict[str, Any] | None:
        """从 HTML 解析账号信息。

        Args:
            html: 平台公开页面 HTML

        Returns:
            标准化账号字段字典；解析失败返回 None
        """
        render_data = self._strategy.extract_render_data(html)
        if not render_data:
            return None

        fields = self._strategy.extract_account_fields(render_data)
        if not fields.get("account_id"):
            logger.info("AccountParser: 未找到 account_id，可能非账号页面")
            return None

        return fields


# ══════════════════════════════════════════════════════════════════════
# Phase 3-2.2: VideoParser
# ══════════════════════════════════════════════════════════════════════

class VideoParser:
    """视频解析器 — 从 RENDER_DATA 提取标准视频字段。

    输出:
    - video_id
    - video_title
    - video_url
    - author_id
    - publish_time
    - like_count
    - comment_count
    - collect_count
    """

    def __init__(self, strategy: PublicExtractionStrategy | None = None) -> None:
        self._strategy = strategy or PublicExtractionStrategy()

    def parse(self, html: str) -> list[dict[str, Any]]:
        """从 HTML 解析视频列表。

        Args:
            html: 平台公开页面 HTML

        Returns:
            标准化视频字段字典列表；解析失败返回空列表
        """
        render_data = self._strategy.extract_render_data(html)
        if not render_data:
            return []

        return self._strategy.extract_video_fields(render_data)


# ══════════════════════════════════════════════════════════════════════
# Phase 3-2.2: CommentParser
# ══════════════════════════════════════════════════════════════════════

class CommentParser:
    """评论解析器 — 从 RENDER_DATA 提取标准评论字段。

    输出:
    - comment_id
    - comment_text
    - comment_time
    - user_id
    - user_name
    - user_profile_url
    """

    def __init__(self, strategy: PublicExtractionStrategy | None = None) -> None:
        self._strategy = strategy or PublicExtractionStrategy()

    def parse(self, html: str) -> list[dict[str, Any]]:
        """从 HTML 解析评论列表。

        Args:
            html: 平台公开页面 HTML

        Returns:
            标准化评论字段字典列表；解析失败返回空列表
        """
        render_data = self._strategy.extract_render_data(html)
        if not render_data:
            return []

        return self._strategy.extract_comment_fields(render_data)



# ══════════════════════════════════════════════════════════════════════
# HTML 解析工具
# ══════════════════════════════════════════════════════════════════════

def _extract_text(html: str, tag: str, cls: str) -> str:
    """从 HTML 中提取指定 class 的标签文本内容。"""
    pattern = rf'<{tag}[^>]*class="{cls}"[^>]*>(.*?)</{tag}>'
    match = re.search(pattern, html)
    return match.group(1).strip() if match else ""


def _extract_int(html: str, tag: str, cls: str) -> int:
    """从 HTML 中提取整数。"""
    text = _extract_text(html, tag, cls)
    try:
        return int(text.replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return 0


def _extract_div_text(html: str, cls: str) -> str:
    """从 div 中提取文本。"""
    pattern = rf'<div class="{cls}">(.*?)</div>'
    match = re.search(pattern, html, re.DOTALL)
    return match.group(1).strip() if match else ""


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser
# ══════════════════════════════════════════════════════════════════════

class DouyinPageParser:
    """抖音公开页面解析器 (V3.2)。

    支持三模式:
    - mock:   基于 class/data 属性的 HTML 模板解析（MockPageFetcher）
    - public: 基于 RENDER_DATA JSON 提取（PublicPageFetcher）
    - official: 基于官方 API JSON 提取（未来）

    Public 失败自动降级到 Mock。
    输出: SearchResultItem / AccountDetail / VideoCandidate / Comment dicts。
    """

    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode
        self.platform_name = "douyin"
        self.source_mode: str = mode if mode != "mock" else "public"
        self.collected_time: str = ""
        if mode == "public":
            self._strategy = PublicExtractionStrategy()
            self._account_parser = AccountParser(self._strategy)
            self._video_parser = VideoParser(self._strategy)
            self._comment_parser = CommentParser(self._strategy)
        else:
            self._strategy = None
            self._account_parser = None
            self._video_parser = None
            self._comment_parser = None

    # ── parse_search_results ──

    def parse_search_results(
        self, html: str, source_keyword: str = ""
    ) -> list[SearchResultItem]:
        """解析搜索结果页 (mock/public 两模式)。

        Public 模式下从 RENDER_DATA 提取 user_list，
        失败自动降级到 Mock 策略。
        """
        if self.mode == "public" and html and "RENDER_DATA" in html:
            try:
                result = self._parse_search_public(html, source_keyword)
                if result:
                    return result
            except Exception as e:
                logger.warning("Public 搜索解析失败: %s，降级 mock", e)

        return self._parse_search_mock(html, source_keyword)

    def _parse_search_public(
        self, html: str, source_keyword: str
    ) -> list[SearchResultItem]:
        """Public 模式: RENDER_DATA → user_list → SearchResultItem。"""
        render_data = _extract_render_data_json(html)
        if not render_data:
            return []

        user_list = (
            _safe_get(render_data, "serverRouter", "/search/user", "user_list", default=[])
            or _safe_get(render_data, "serverRouter", "SearchUser", "user_list", default=[])
            or _safe_get(render_data, "user_list", default=[])
        )
        if not isinstance(user_list, list):
            return []

        self.collected_time = datetime.now(TZ_SHANGHAI).isoformat()
        results: list[SearchResultItem] = []
        for i, user_item in enumerate(user_list, start=1):
            if not isinstance(user_item, dict):
                continue
            user_info = user_item.get("user_info", user_item)
            if not isinstance(user_info, dict):
                continue

            account_name = str(user_info.get("nickname", ""))
            bio = str(user_info.get("signature", ""))

            if is_rural(account_name + bio):
                continue

            results.append(SearchResultItem(
                platform=self.platform_name,
                account_id=str(user_info.get("uid", "") or user_info.get("sec_uid", "")),
                account_name=account_name,
                account_url=f"https://www.douyin.com/user/{user_info.get('sec_uid', '')}",
                account_type_hint=str(user_info.get("account_type_hint", "")),
                bio_snippet=bio,
                follower_count=_normalize_count(user_info.get("follower_count", 0)),
                ip_location=str(user_info.get("ip_location", "")),
                source_type="search",
                discovery_keyword=source_keyword,
                rank=i,
            ))

        logger.info("Public 搜索解析: '%s' → %d 结果", source_keyword, len(results))
        return results

    def _parse_search_mock(
        self, html: str, source_keyword: str
    ) -> list[SearchResultItem]:
        """Mock 模式: class/data 属性 HTML 解析（原实现）。"""
        self.collected_time = datetime.now(TZ_SHANGHAI).isoformat()

        if not html or "search-card" not in html:
            logger.info("搜索解析: 无结果卡片")
            return []

        results: list[SearchResultItem] = []
        cards = re.split(r'<div class="search-card"', html)[1:]

        for rank, card_html in enumerate(cards, start=1):
            account_id = _extract_text(card_html, "span", "douyin-id")
            account_name = _extract_text(card_html, "span", "nickname")

            if not account_id or not account_name:
                continue

            follower_count = _extract_int(card_html, "span", "follower-count")
            ip_location = _extract_text(card_html, "span", "ip-location")
            bio = _extract_div_text(card_html, "bio")
            account_type_hint = _extract_text(card_html, "span", "account-type")

            if is_rural(bio):
                logger.info("搜索解析: 排除农村内容 '%s'", account_name)
                continue

            results.append(SearchResultItem(
                platform=self.platform_name,
                account_id=account_id,
                account_name=account_name,
                account_url=f"https://douyin.com/user/{account_id}",
                account_type_hint=account_type_hint,
                bio_snippet=bio,
                follower_count=follower_count,
                ip_location=ip_location,
                source_type="search",
                discovery_keyword=source_keyword,
                rank=rank,
            ))

        logger.info("搜索解析: '%s' → %d 结果", source_keyword, len(results))
        return results

    # ── parse_account_page ──

    def parse_account_page(self, html: str) -> AccountDetail | None:
        """解析账号主页 (mock/public 两模式)。

        Public 模式下从 RENDER_DATA 提取账号字段，
        失败自动降级到 Mock 策略。
        """
        if self.mode == "public" and html and "RENDER_DATA" in html:
            try:
                result = self._parse_account_public(html)
                if result is not None:
                    return result
            except Exception as e:
                logger.warning("Public 账号解析失败: %s，降级 mock", e)

        return self._parse_account_mock(html)

    def _parse_account_public(self, html: str) -> AccountDetail | None:
        """Public 模式: RENDER_DATA → 账号字段 → AccountDetail。"""
        if self._account_parser is None:
            return None

        fields = self._account_parser.parse(html)
        if fields is None:
            return None

        self.collected_time = datetime.now(TZ_SHANGHAI).isoformat()
        bio = fields.get("bio", "")
        account_name = fields.get("account_name", "")
        ip_location = fields.get("ip_location", "")
        premium_signals = detect_premium_signals(bio + " " + account_name)
        region_signals = detect_region_signals(bio + " " + account_name + " " + ip_location)
        comment_demand_density = min(len(premium_signals) * 2, 10)

        if is_rural(bio):
            logger.info("账号解析: 排除农村内容 '%s'", account_name)
            return None

        return AccountDetail(
            platform=fields.get("platform", "douyin"),
            account_id=fields.get("account_id", ""),
            account_name=account_name,
            account_url=fields.get("account_url", ""),
            bio=bio,
            follower_count=fields.get("follower_count", 0),
            content_count=fields.get("content_count", 0),
            ip_location=fields.get("ip_location", ""),
            verified=fields.get("verified", False),
            account_type_ai=fields.get("account_category", ""),
            premium_signals=premium_signals,
            region_signals=region_signals,
            comment_demand_density=comment_demand_density,
            last_active_days=3,
        )

    def _parse_account_mock(self, html: str) -> AccountDetail | None:
        """Mock 模式: class 属性 HTML 解析（原实现）。

        提取字段:
        - 基础: account_id / account_name / bio / follower_count / content_count
        - 认证: verified
        - 分类: account_type_ai
        - 信号: premium_signals / region_signals (从 bio + 标签提取)
        - 需求密度: comment_demand_density (从 premium_signals 推算)
        """
        self.collected_time = datetime.now(TZ_SHANGHAI).isoformat()

        if not html or "profile-page" not in html:
            logger.warning("账号解析: 无效页面 HTML")
            return None

        account_id = _extract_text(html, "span", "douyin-id")
        account_name = _extract_text(html, "h1", "nickname") or _extract_text(html, "span", "nickname")

        if not account_id or not account_name:
            logger.warning("账号解析: 缺少 account_id 或 account_name")
            return None

        verified_text = _extract_text(html, "span", "verified-badge")
        bio = _extract_div_text(html, "bio")
        follower_count = _extract_int(html, "span", "follower-count")
        content_count = _extract_int(html, "span", "content-count")
        ip_location = _extract_text(html, "div", "ip-location")
        account_type_ai = _extract_text(html, "span", "account-type")

        premium_from_tag = _extract_div_text(html, "premium-signals")
        region_from_tag = _extract_div_text(html, "region-signals")

        premium_signals = [
            s.strip() for s in premium_from_tag.split(",") if s.strip()
        ] if premium_from_tag else []
        premium_from_bio = detect_premium_signals(bio)
        for s in premium_from_bio:
            if s not in premium_signals:
                premium_signals.append(s)

        region_signals = [
            s.strip() for s in region_from_tag.split(",") if s.strip()
        ] if region_from_tag else []
        region_from_bio = detect_region_signals(bio + ip_location)
        for s in region_from_bio:
            if s not in region_signals:
                region_signals.append(s)

        comment_demand_density = min(len(premium_signals) * 2, 10)

        if is_rural(bio):
            logger.info("账号解析: 排除农村内容 '%s'", account_name)
            return None

        return AccountDetail(
            platform=self.platform_name,
            account_id=account_id,
            account_name=account_name,
            account_url=f"https://douyin.com/user/{account_id}",
            bio=bio,
            follower_count=follower_count,
            content_count=content_count,
            ip_location=ip_location,
            verified=verified_text.lower() == "true",
            account_type_ai=account_type_ai,
            premium_signals=premium_signals,
            region_signals=region_signals,
            comment_demand_density=comment_demand_density,
            last_active_days=3,
        )

    # ── parse_video_list ──

    def parse_video_list(
        self, html: str, default_topic: str = ""
    ) -> list[VideoCandidate]:
        """解析账号作品列表页 (mock/public 两模式)。

        Public 模式下从 RENDER_DATA 提取 aweme_list，
        失败自动降级到 Mock 策略。
        """
        if self.mode == "public" and html and "RENDER_DATA" in html:
            try:
                result = self._parse_videos_public(html, default_topic)
                if result:
                    return result
            except Exception as e:
                logger.warning("Public 视频解析失败: %s，降级 mock", e)

        return self._parse_videos_mock(html, default_topic)

    def _parse_videos_public(
        self, html: str, default_topic: str
    ) -> list[VideoCandidate]:
        """Public 模式: RENDER_DATA → aweme_list → VideoCandidate。"""
        if self._video_parser is None:
            return []

        video_fields_list = self._video_parser.parse(html)
        if not video_fields_list:
            return []

        self.collected_time = datetime.now(TZ_SHANGHAI).isoformat()
        videos: list[VideoCandidate] = []
        for vf in video_fields_list:
            title = vf.get("video_title", "")
            if not title:
                continue

            housing_signal = detect_housing_signal(title)
            if housing_signal in ("别墅", "叠拼", "阳光房"):
                relevance_score = 9
            elif housing_signal != "普通住宅":
                relevance_score = 7
            else:
                relevance_score = 5

            videos.append(VideoCandidate(
                platform=self.platform_name,
                video_id=vf.get("video_id", ""),
                video_url=vf.get("video_url", ""),
                title=title,
                topic=default_topic,
                publish_time=vf.get("publish_time", ""),
                comment_count=vf.get("comment_count", 0),
                housing_signal=housing_signal,
                relevance_score=relevance_score,
            ))

        logger.info("Public 视频解析: %d 候选", len(videos))
        return videos

    def _parse_videos_mock(
        self, html: str, default_topic: str
    ) -> list[VideoCandidate]:
        """Mock 模式: class 属性 HTML 解析（原实现）。

        提取字段:
        - .video-title → title
        - .comment-count → comment_count
        - .publish-time → publish_time
        - .video-topic → topic

        额外计算:
        - housing_signal: 从 title 检测
        - relevance_score: 从 housing_signal 推算
        """
        self.collected_time = datetime.now(TZ_SHANGHAI).isoformat()

        if not html or "video-card" not in html:
            return []

        videos: list[VideoCandidate] = []
        cards = re.split(r'<div class="video-card"', html)[1:]

        for card_html in cards:
            title = _extract_div_text(card_html, "video-title")
            if not title:
                continue

            comment_count = _extract_int(card_html, "span", "comment-count")
            publish_time = _extract_text(card_html, "span", "publish-time")
            topic = _extract_div_text(card_html, "video-topic") or default_topic

            housing_signal = detect_housing_signal(title)
            if housing_signal in ("别墅", "叠拼", "阳光房"):
                relevance_score = 9
            elif housing_signal != "普通住宅":
                relevance_score = 7
            else:
                relevance_score = 5

            videos.append(VideoCandidate(
                platform=self.platform_name,
                video_id=f"dy_{hash(title) % 100000:05d}",
                video_url=f"https://douyin.com/video/dy_{hash(title) % 100000:05d}",
                title=title,
                topic=topic,
                publish_time=publish_time,
                comment_count=comment_count,
                housing_signal=housing_signal,
                relevance_score=relevance_score,
            ))

        logger.info("视频解析: %d 候选", len(videos))
        return videos


    # ── 评论解析 (Phase 3-2.2 新增) ──

    def parse_comments(self, html: str) -> list[dict[str, Any]]:
        """解析评论列表页 (mock/public 两模式)。

        Args:
            html: 评论页面 HTML

        Returns:
            标准化评论字段字典列表，每个包含:
            comment_id, comment_text, comment_time,
            user_id, user_name, user_profile_url

        Public 失败自动降级到 Mock（返回空列表）。
        """
        if self.mode == "public" and html and "RENDER_DATA" in html:
            try:
                result = self._parse_comments_public(html)
                if result:
                    return result
            except Exception as e:
                logger.warning("Public 评论解析失败: %s，降级 mock", e)

        return self._parse_comments_mock(html)

    def _parse_comments_public(self, html: str) -> list[dict[str, Any]]:
        """Public 模式: RENDER_DATA → comments。"""
        if self._comment_parser is None:
            return []
        return self._comment_parser.parse(html)

    def _parse_comments_mock(self, html: str) -> list[dict[str, Any]]:
        """Mock 模式: 从视频列表 Mock 数据中提取评论。

        Mock 模式下评论数据有限，返回基于视频标题的模拟评论。
        """
        if not html:
            return []

        comments: list[dict[str, Any]] = []
        cards = re.split(r'<div class="video-card"', html)
        for i, card_html in enumerate(cards):
            title = _extract_div_text(card_html, "video-title")
            if not title:
                continue
            comments.append({
                "comment_id": f"mock_c{i:04d}",
                "comment_text": f"看了{title}，想了解一下光伏安装",
                "comment_time": datetime.now(TZ_SHANGHAI).isoformat(),
                "user_id": f"mock_user_{i:04d}",
                "user_name": f"光伏关注者{i:02d}",
                "user_profile_url": "",
            })

        return comments



# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json as _json
    from page_fetcher import MockPageFetcher

    def _test_mock_mode():
        print("── Mock 模式 ──")
        fetcher = MockPageFetcher()
        parser = DouyinPageParser(mode="mock")

        # 搜索解析
        html = fetcher.fetch_search_page("别墅光伏", "douyin")
        results = parser.parse_search_results(html, source_keyword="别墅光伏")
        print(f"  搜索 '别墅光伏': {len(results)} 结果")
        for r in results[:3]:
            print(f"    [{r.rank}] {r.account_name} ({r.account_type_hint})")
        assert len(results) >= 2
        print("  ✓ 至少 2 个结果")

        # 空 HTML
        empty = parser.parse_search_results("")
        assert empty == []
        print("  ✓ 空 HTML → []")

        # 账号解析
        html = fetcher.fetch_account_page("reg_install_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert detail.account_name == "成都光伏老王"
        assert "别墅" in detail.premium_signals
        assert "成都" in detail.region_signals
        print(f"  账号: {detail.account_name} (粉丝:{detail.follower_count})")
        print("  ✓ 字段完整")

        # 不存在
        none_result = parser.parse_account_page("")
        assert none_result is None
        print("  ✓ 无效 HTML → None")

        # 视频解析
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        videos = parser.parse_video_list(html, default_topic="成都光伏安装")
        assert len(videos) == 3
        for v in videos:
            print(f"  [{v.housing_signal}] {v.title} (相关度:{v.relevance_score})")
        print("  ✓ 3 个视频")

        # 空视频
        empty_vids = parser.parse_video_list("")
        assert empty_vids == []
        print("  ✓ 空 HTML → []")

        # 评论解析 (Mock)
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        comments = parser.parse_comments(html)
        print(f"  评论 (mock): {len(comments)} 条")
        assert len(comments) >= 1
        for c in comments[:2]:
            print(f"    [{c['user_name']}] {c['comment_text'][:40]}...")
        print("  ✓ 评论解析正常")

        # 业务边界
        from page_fetcher import _SEARCH_CARD_TEMPLATE
        rural_html = _SEARCH_CARD_TEMPLATE.format(
            account_name="农村光伏扶贫号",
            account_id="rural_001",
            verified="false",
            bio="农村光伏扶贫项目，惠农政策推广",
            follower_count="1000",
            content_count="10",
            ip_location="某县",
            account_type_hint="info_account",
        )
        rural_results = parser.parse_search_results(
            f'<div class="search-card"{rural_html}', source_keyword="光伏"
        )
        assert len(rural_results) == 0
        print("  ✓ 农村内容被排除")

    def _test_public_mode():
        print("── Public 模式 (降级测试) ──")
        parser = DouyinPageParser(mode="public")
        fetcher = MockPageFetcher()
        mock_html = fetcher.fetch_search_page("光伏", "douyin")

        # RENDER_DATA 不存在时应降级到 mock
        results = parser.parse_search_results(mock_html, source_keyword="光伏")
        print(f"  搜索 (降级mock): {len(results)} 结果")
        assert len(results) >= 1

        # 空 HTML 测试
        empty = parser.parse_search_results("")
        assert empty == []
        print("  ✓ Public 降级正常")

    def _test_public_with_render_data():
        print("── Public 模式 (含 RENDER_DATA) ──")
        parser = DouyinPageParser(mode="public")

        render_data = {
            "serverRouter": {
                "/search/user": {
                    "user_list": [{
                        "user_info": {
                            "uid": "12345",
                            "sec_uid": "sec_12345",
                            "nickname": "成都光伏专家",
                            "signature": "专注别墅光伏安装10年",
                            "follower_count": 50000,
                            "aweme_count": 200,
                            "ip_location": "四川成都",
                        }
                    }]
                },
                "UserPageData": {
                    "aweme_list": [{
                        "aweme_id": "v001",
                        "desc": "别墅光伏改造实拍",
                        "create_time": 1700000000,
                        "author_user_id": "12345",
                        "statistics": {
                            "digg_count": 1500,
                            "comment_count": 85,
                            "collect_count": 320,
                        },
                    }],
                },
            },
        }

        html_with_render = f'<html><script id="RENDER_DATA" type="application/json">{_json.dumps(render_data)}</script></html>'

        # 搜索解析
        results = parser.parse_search_results(html_with_render, source_keyword="光伏")
        print(f"  RENDER_DATA 搜索: {len(results)} 结果")
        if results:
            r = results[0]
            print(f"    [{r.rank}] {r.account_name} (粉丝:{r.follower_count})")
            assert r.account_name == "成都光伏专家"
            assert r.follower_count == 50000

        # 空 RENDER_DATA → 降级
        results_empty = parser.parse_search_results("<html></html>", "光伏")
        assert results_empty == []
        print("  ✓ RENDER_DATA 解析正常")

    print("=" * 60)
    print("  DouyinPageParser — 自检 (V3.2)")
    print("=" * 60)

    _test_mock_mode()
    _test_public_mode()
    _test_public_with_render_data()

    print("\n✓ DouyinPageParser 自检完成 (V3.2)\n")
