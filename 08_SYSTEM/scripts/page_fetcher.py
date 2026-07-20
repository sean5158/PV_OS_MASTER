"""PV_OS 页面获取层。

定义平台公开页面获取的抽象接口。
P2-3: 只提供 MockPageFetcher（返回预置 HTML），真实网络获取在 P3 实现。

设计原则:
- PageFetcher 与 Parser 分离：获取原始 HTML/JSON，不解析内容
- MockPageFetcher 输出模拟真实页面的 HTML 片段，供 Parser 测试

三模式:
    mock   → MockPageFetcher (预置 HTML)
    public → 真实 HTTP/Browser 获取 (P3)
    official → API Client (P3)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# 预置 HTML 模板 — 模拟抖音公开页面结构
# ══════════════════════════════════════════════════════════════════════

# 搜索结果页 — 模拟抖音搜索综合Tab+用户Tab的账号卡片
_SEARCH_RESULT_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><title>抖音搜索: {keyword}</title></head><body>
<div id="search-result-list">
{cards}
</div>
</body></html>"""

_SEARCH_CARD_TEMPLATE = """
<div class="search-card" data-type="user">
  <div class="user-info">
    <span class="nickname">{account_name}</span>
    <span class="douyin-id">{account_id}</span>
    <span class="verified-badge">{verified}</span>
  </div>
  <div class="bio">{bio}</div>
  <div class="stats">
    <span class="follower-count">{follower_count}</span>
    <span class="content-count">{content_count}</span>
  </div>
  <div class="meta">
    <span class="ip-location">{ip_location}</span>
    <span class="account-type">{account_type_hint}</span>
  </div>
</div>"""

# 账号主页 — 模拟抖音账号详情页
_ACCOUNT_PAGE_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><title>{account_name} 的主页</title></head><body>
<div class="profile-page">
  <div class="profile-header">
    <h1 class="nickname">{account_name}</h1>
    <span class="douyin-id">{account_id}</span>
    <span class="verified-badge">{verified}</span>
  </div>
  <div class="bio">{bio}</div>
  <div class="profile-stats">
    <span class="follower-count">{follower_count}</span>
    <span class="following-count">120</span>
    <span class="content-count">{content_count}</span>
    <span class="total-likes">50000</span>
  </div>
  <div class="ip-location">{ip_location}</div>
  <div class="account-tags">
    <span class="account-type">{account_type_ai}</span>
  </div>
  <div class="premium-signals">{premium_signals}</div>
  <div class="region-signals">{region_signals}</div>
</div>
</body></html>"""

# 作品列表 — 模拟抖音账号作品列表
_VIDEO_LIST_HTML_TEMPLATE = """<!DOCTYPE html>
<html><head><title>{account_name} 的作品</title></head><body>
<div class="video-list">
{videos}
</div>
</body></html>"""

_VIDEO_CARD_TEMPLATE = """
<div class="video-card">
  <div class="video-title">{title}</div>
  <div class="video-meta">
    <span class="comment-count">{comment_count}</span>
    <span class="like-count">230</span>
    <span class="publish-time">{publish_time}</span>
  </div>
  <div class="video-topic">{topic}</div>
</div>"""


# ══════════════════════════════════════════════════════════════════════
# 预置测试数据 — 模拟 MOCK_CANDIDATES 对应的 HTML
# ══════════════════════════════════════════════════════════════════════

MOCK_ACCOUNT_HTML_DATA: dict[str, dict[str, Any]] = {
    "reg_install_001": {
        "account_name": "成都光伏老王",
        "account_id": "reg_install_001",
        "verified": "true",
        "bio": "成都本地光伏安装团队，专注家庭光伏10年",
        "follower_count": "35000",
        "content_count": "156",
        "ip_location": "四川成都",
        "account_type_ai": "regional_installer",
        "premium_signals": "别墅,叠拼,阳光房",
        "region_signals": "成都,绵阳,德阳",
    },
    "city_case_001": {
        "account_name": "别墅光伏改造日记",
        "account_id": "city_case_001",
        "verified": "true",
        "bio": "专注高端别墅光伏改造，实拍案例分享",
        "follower_count": "50000",
        "content_count": "89",
        "ip_location": "四川成都",
        "account_type_ai": "city_case",
        "premium_signals": "别墅,花园洋房,阳光房",
        "region_signals": "成都,重庆",
    },
    "nat_brand_001": {
        "account_name": "正泰安能",
        "account_id": "nat_brand_001",
        "verified": "true",
        "bio": "正泰集团旗下户用光伏品牌，全国安装服务",
        "follower_count": "250000",
        "content_count": "420",
        "ip_location": "浙江杭州",
        "account_type_ai": "national_brand",
        "premium_signals": "别墅,阳光房",
        "region_signals": "成都,重庆",
    },
}

MOCK_VIDEO_HTML_DATA: dict[str, list[dict[str, Any]]] = {
    "reg_install_001": [
        {"title": "别墅光伏安装实拍", "comment_count": "50", "publish_time": "2026-07-18", "topic": "成都光伏安装"},
        {"title": "成都家庭光伏案例", "comment_count": "32", "publish_time": "2026-07-15", "topic": "成都光伏安装"},
        {"title": "光伏报价", "comment_count": "80", "publish_time": "2026-07-12", "topic": "成都光伏安装"},
    ],
    "city_case_001": [
        {"title": "独栋别墅光伏改造", "comment_count": "65", "publish_time": "2026-07-19", "topic": "别墅光伏"},
        {"title": "花园洋房光伏", "comment_count": "28", "publish_time": "2026-07-16", "topic": "别墅光伏"},
        {"title": "阳光房光伏顶", "comment_count": "41", "publish_time": "2026-07-14", "topic": "别墅光伏"},
    ],
}


# ══════════════════════════════════════════════════════════════════════
# PageFetcherBase
# ══════════════════════════════════════════════════════════════════════

class PageFetcherBase(ABC):
    """平台公开页面获取器抽象基类。

    职责: 获取原始页面内容 (HTML/JSON)，不解析。
    解析交给 PageParser。

    子类:
    - MockPageFetcher: 返回预置 HTML (P2-3)
    - HttpPageFetcher: requests/httpx 获取 (P3)
    - BrowserPageFetcher: Playwright/Selenium (P3)
    """

    def __init__(self) -> None:
        self.collected_time: str = ""

    def _now(self) -> str:
        return datetime.now(TZ_SHANGHAI).isoformat()

    @abstractmethod
    def fetch_search_page(
        self, keyword: str, platform: str, depth: int = 30
    ) -> str:
        """获取平台搜索结果页原始内容。

        Args:
            keyword: 搜索关键词
            platform: 平台标识 (douyin/xiaohongshu/...)
            depth: 搜索深度

        Returns:
            原始 HTML 字符串
        """
        ...

    @abstractmethod
    def fetch_account_page(
        self, account_id: str, platform: str
    ) -> str:
        """获取账号主页原始内容。

        Args:
            account_id: 平台账号 ID
            platform: 平台标识

        Returns:
            原始 HTML 字符串，账号不存在时返回空字符串
        """
        ...

    @abstractmethod
    def fetch_video_list_page(
        self, account_id: str, platform: str, limit: int = 30
    ) -> str:
        """获取作品列表页原始内容。

        Args:
            account_id: 平台账号 ID
            platform: 平台标识
            limit: 最大作品数

        Returns:
            原始 HTML 字符串
        """
        ...


# ══════════════════════════════════════════════════════════════════════
# MockPageFetcher
# ══════════════════════════════════════════════════════════════════════

class MockPageFetcher(PageFetcherBase):
    """Mock 页面获取器 — 返回预置 HTML 模板。

    用于测试 Parser 的解析能力，不依赖网络。
    HTML 结构与抖音公开页面类似，Parser 应能正确解析。

    用法::

        fetcher = MockPageFetcher()
        html = fetcher.fetch_search_page("别墅光伏", "douyin", depth=30)
        # → 包含 city_case_001 等匹配账号卡片的 HTML
    """

    def __init__(self) -> None:
        super().__init__()
        # 默认搜索匹配规则: discovery_keyword 对应的 account_ids
        self._search_index: dict[str, list[str]] = {
            "别墅光伏": ["city_case_001", "reg_install_001"],
            "成都光伏安装": ["reg_install_001"],
            "家庭光伏": ["nat_brand_001", "nat_brand_002"],
            "光伏安装": ["nat_brand_001", "reg_install_001"],
            "光伏": ["nat_brand_001", "reg_install_001", "city_case_001"],
        }

    # ── search ──

    def fetch_search_page(
        self, keyword: str, platform: str, depth: int = 30
    ) -> str:
        """Mock: 根据关键词匹配预置账号，生成搜索结果 HTML。"""
        self.collected_time = self._now()

        if platform != "douyin":
            return ""

        # 查找匹配的 account_ids
        matched_ids: list[str] = []
        for index_kw, ids in self._search_index.items():
            if index_kw in keyword or keyword in index_kw:
                matched_ids.extend(ids)

        if not matched_ids:
            # 对于不匹配的关键词，返回空结果 HTML
            return _SEARCH_RESULT_HTML_TEMPLATE.format(
                keyword=keyword, cards=""
            )

        # 生成搜索卡片 HTML
        cards: list[str] = []
        for account_id in matched_ids[:depth]:
            data = MOCK_ACCOUNT_HTML_DATA.get(account_id)
            if data is None:
                continue
            cards.append(_SEARCH_CARD_TEMPLATE.format(
                account_name=data["account_name"],
                account_id=data["account_id"],
                verified=data["verified"],
                bio=data["bio"],
                follower_count=data["follower_count"],
                content_count=data["content_count"],
                ip_location=data["ip_location"],
                account_type_hint=data["account_type_ai"],
            ))

        html = _SEARCH_RESULT_HTML_TEMPLATE.format(
            keyword=keyword, cards="\n".join(cards)
        )
        logger.info("MockPageFetcher: 搜索 '%s' → %d 卡片", keyword, len(cards))
        return html

    # ── account ──

    def fetch_account_page(
        self, account_id: str, platform: str
    ) -> str:
        """Mock: 返回预置账号主页 HTML。"""
        self.collected_time = self._now()

        if platform != "douyin":
            return ""

        data = MOCK_ACCOUNT_HTML_DATA.get(account_id)
        if data is None:
            logger.warning("MockPageFetcher: 账号不存在: %s", account_id)
            return ""

        html = _ACCOUNT_PAGE_HTML_TEMPLATE.format(**data)
        logger.info("MockPageFetcher: 获取账号 %s 主页", account_id)
        return html

    # ── video list ──

    def fetch_video_list_page(
        self, account_id: str, platform: str, limit: int = 30
    ) -> str:
        """Mock: 返回预置作品列表 HTML。"""
        self.collected_time = self._now()

        if platform != "douyin":
            return ""

        videos = MOCK_VIDEO_HTML_DATA.get(account_id, [])
        if not videos:
            logger.warning("MockPageFetcher: 无视频数据: %s", account_id)
            account_name = MOCK_ACCOUNT_HTML_DATA.get(
                account_id, {}
            ).get("account_name", account_id)
            return _VIDEO_LIST_HTML_TEMPLATE.format(
                account_name=account_name, videos=""
            )

        video_cards: list[str] = []
        for v in videos[:limit]:
            video_cards.append(_VIDEO_CARD_TEMPLATE.format(**v))

        account_name = MOCK_ACCOUNT_HTML_DATA.get(
            account_id, {}
        ).get("account_name", account_id)

        html = _VIDEO_LIST_HTML_TEMPLATE.format(
            account_name=account_name, videos="\n".join(video_cards)
        )
        logger.info("MockPageFetcher: 获取账号 %s 作品列表 → %d 视频", account_id, len(video_cards))
        return html


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  MockPageFetcher — 自检")
    print("=" * 60)

    fetcher = MockPageFetcher()

    # search
    print("\n── fetch_search_page ──")
    html = fetcher.fetch_search_page("别墅光伏", "douyin", depth=10)
    print(f"  搜索结果 HTML 长度: {len(html)} 字符")
    assert "city_case_001" in html
    assert "reg_install_001" in html
    print("  ✓ 包含 city_case_001, reg_install_001")

    # 空结果
    html_empty = fetcher.fetch_search_page("XYZ不存在", "douyin")
    assert "search-card" not in html_empty
    print("  ✓ 无匹配 → 空结果")

    # 非 douyin 平台
    html_other = fetcher.fetch_search_page("光伏", "xiaohongshu")
    assert html_other == ""
    print("  ✓ 非 douyin → 空")

    # account
    print("\n── fetch_account_page ──")
    html = fetcher.fetch_account_page("reg_install_001", "douyin")
    assert "成都光伏老王" in html
    assert "别墅" in html
    print(f"  账号主页 HTML 长度: {len(html)} 字符")
    print("  ✓ 包含 成都光伏老王, 别墅信号")

    # 不存在
    html_none = fetcher.fetch_account_page("no_such_id", "douyin")
    assert html_none == ""
    print("  ✓ 不存在账号 → 空")

    # videos
    print("\n── fetch_video_list_page ──")
    html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
    assert "别墅光伏安装实拍" in html
    assert "光伏报价" in html
    print(f"  作品列表 HTML 长度: {len(html)} 字符")
    print("  ✓ 包含 3 个视频")

    # 无视频
    html_none_vid = fetcher.fetch_video_list_page("nat_brand_001", "douyin")
    assert "video-card" not in html_none_vid
    print("  ✓ 无视频数据 → 空列表")

    print("\n✓ MockPageFetcher 自检完成\n")
