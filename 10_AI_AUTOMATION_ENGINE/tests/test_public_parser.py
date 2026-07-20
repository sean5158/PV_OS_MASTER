"""Public Page Parser 测试 (P2-3)。

覆盖: PageFetcherBase / MockPageFetcher / DouyinPageParser /
       Collector public模式 / 三模式 / 业务边界 / 回归。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_public_parser.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from page_fetcher import (  # noqa: E402
    PageFetcherBase,
    MockPageFetcher,
    MOCK_ACCOUNT_HTML_DATA,
    MOCK_VIDEO_HTML_DATA,
)
from douyin_page_parser import (  # noqa: E402
    DouyinPageParser,
    detect_premium_signals,
    detect_region_signals,
    detect_housing_signal,
    is_rural,
)
from douyin_public_collector import DouyinPublicCollector  # noqa: E402
from public_search_base import (  # noqa: E402
    SearchResultItem,
    AccountDetail,
    VideoCandidate,
    PublicSearchCollector,
)


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def fetcher() -> MockPageFetcher:
    return MockPageFetcher()


@pytest.fixture
def parser() -> DouyinPageParser:
    return DouyinPageParser()


@pytest.fixture
def collector_mock() -> DouyinPublicCollector:
    return DouyinPublicCollector(mode="mock")


@pytest.fixture
def collector_public() -> DouyinPublicCollector:
    return DouyinPublicCollector(mode="public", page_fetcher=MockPageFetcher())


# ══════════════════════════════════════════════════════════════════════
# PageFetcherBase
# ══════════════════════════════════════════════════════════════════════

class TestPageFetcherBase:
    """抽象基类验证。"""

    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            PageFetcherBase()  # type: ignore[abstract]

    def test_mock_is_instance(self, fetcher: MockPageFetcher) -> None:
        assert isinstance(fetcher, PageFetcherBase)


# ══════════════════════════════════════════════════════════════════════
# MockPageFetcher — 搜索
# ══════════════════════════════════════════════════════════════════════

class TestMockPageFetcherSearch:
    """搜索页面获取。"""

    def test_search_returns_html(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_search_page("别墅光伏", "douyin")
        assert len(html) > 100
        assert "search-card" in html
        assert "别墅光伏改造日记" in html

    def test_search_no_match(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_search_page("不存在的关键词XYZ", "douyin")
        assert "search-card" not in html

    def test_search_non_douyin(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_search_page("光伏", "xiaohongshu")
        assert html == ""

    def test_search_collected_time_set(self, fetcher: MockPageFetcher) -> None:
        fetcher.fetch_search_page("光伏", "douyin")
        assert fetcher.collected_time
        assert "2026" in fetcher.collected_time


# ══════════════════════════════════════════════════════════════════════
# MockPageFetcher — 账号
# ══════════════════════════════════════════════════════════════════════

class TestMockPageFetcherAccount:
    """账号页面获取。"""

    def test_account_returns_html(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_account_page("reg_install_001", "douyin")
        assert "profile-page" in html
        assert "成都光伏老王" in html
        assert "别墅" in html

    def test_account_not_found(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_account_page("no_such_id", "douyin")
        assert html == ""

    def test_account_non_douyin(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_account_page("reg_install_001", "xiaohongshu")
        assert html == ""


# ══════════════════════════════════════════════════════════════════════
# MockPageFetcher — 视频
# ══════════════════════════════════════════════════════════════════════

class TestMockPageFetcherVideos:
    """视频列表获取。"""

    def test_videos_returns_html(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        assert "video-card" in html
        assert "别墅光伏安装实拍" in html

    def test_videos_no_data(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_video_list_page("nat_brand_001", "douyin")
        assert "video-card" not in html

    def test_videos_limit(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin", limit=1)
        # 限制在 MockPageFetcher 的 list slicing 中生效
        assert len(html) > 0


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser — 搜索解析
# ══════════════════════════════════════════════════════════════════════

class TestParserSearch:
    """搜索页面解析。"""

    def test_parse_search_results(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_search_page("别墅光伏", "douyin")
        results = parser.parse_search_results(html, source_keyword="别墅光伏")
        assert len(results) >= 2

    def test_parse_search_no_match(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_search_page("不存在XYZ", "douyin")
        results = parser.parse_search_results(html)
        assert results == []

    def test_parse_search_empty_html(self, parser: DouyinPageParser) -> None:
        results = parser.parse_search_results("")
        assert results == []

    def test_parse_search_fields(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_search_page("别墅光伏", "douyin")
        results = parser.parse_search_results(html, source_keyword="别墅光伏")
        for r in results:
            assert r.platform == "douyin"
            assert r.account_id
            assert r.account_name
            assert r.rank >= 1
            assert r.source_type == "search"

    def test_parse_search_ip_location(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_search_page("别墅光伏", "douyin")
        results = parser.parse_search_results(html)
        locations = {r.ip_location for r in results}
        assert "四川成都" in locations

    def test_parse_search_discovery_keyword(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_search_page("别墅光伏", "douyin")
        results = parser.parse_search_results(html, source_keyword="别墅光伏")
        for r in results:
            assert r.discovery_keyword == "别墅光伏"


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser — 账号解析
# ══════════════════════════════════════════════════════════════════════

class TestParserAccount:
    """账号页面解析。"""

    def test_parse_account_basic(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_account_page("reg_install_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert detail.account_name == "成都光伏老王"
        assert detail.account_id == "reg_install_001"
        assert detail.platform == "douyin"

    def test_parse_account_bio(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_account_page("reg_install_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert "家庭光伏" in detail.bio

    def test_parse_account_follower(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_account_page("reg_install_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert detail.follower_count == 35000

    def test_parse_account_premium_signals(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_account_page("reg_install_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert "别墅" in detail.premium_signals
        assert "叠拼" in detail.premium_signals

    def test_parse_account_region_signals(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_account_page("reg_install_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert "成都" in detail.region_signals

    def test_parse_account_not_found(self, parser: DouyinPageParser) -> None:
        detail = parser.parse_account_page("")
        assert detail is None

    def test_parse_account_no_html(self, parser: DouyinPageParser) -> None:
        detail = parser.parse_account_page("<html>no profile here</html>")
        assert detail is None


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser — 视频解析
# ══════════════════════════════════════════════════════════════════════

class TestParserVideos:
    """视频列表解析。"""

    def test_parse_videos_basic(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        videos = parser.parse_video_list(html, default_topic="成都光伏安装")
        assert len(videos) == 3

    def test_parse_videos_housing_signal(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        videos = parser.parse_video_list(html)
        housing = {v.housing_signal for v in videos}
        assert "别墅" in housing

    def test_parse_videos_relevance(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        videos = parser.parse_video_list(html)
        for v in videos:
            assert 0 <= v.relevance_score <= 10

    def test_parse_videos_comment_count(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        videos = parser.parse_video_list(html)
        for v in videos:
            assert v.comment_count >= 0

    def test_parse_videos_empty(self, parser: DouyinPageParser) -> None:
        videos = parser.parse_video_list("")
        assert videos == []

    def test_parse_videos_no_cards(self, parser: DouyinPageParser) -> None:
        html = fetcher = MockPageFetcher()
        html = fetcher.fetch_video_list_page("nat_brand_001", "douyin")
        videos = parser.parse_video_list(html)
        assert videos == []


# ══════════════════════════════════════════════════════════════════════
# Collector — Public 模式
# ══════════════════════════════════════════════════════════════════════

class TestCollectorPublicMode:
    """Collector mode=public 测试 (MockPageFetcher 提供 HTML)。"""

    def test_search_public(self, collector_public: DouyinPublicCollector) -> None:
        results = collector_public.search_by_keywords("别墅光伏", depth=30)
        assert len(results) >= 2
        account_ids = {r.account_id for r in results}
        assert "city_case_001" in account_ids

    def test_discover_account_public(self, collector_public: DouyinPublicCollector) -> None:
        detail = collector_public.discover_account("reg_install_001")
        assert detail is not None
        assert detail.account_name == "成都光伏老王"
        assert "别墅" in detail.premium_signals

    def test_discover_videos_public(self, collector_public: DouyinPublicCollector) -> None:
        videos = collector_public.discover_videos("reg_install_001", limit=5)
        assert len(videos) >= 1
        assert all(v.platform == "douyin" for v in videos)

    def test_search_batch_public(self, collector_public: DouyinPublicCollector) -> None:
        results = collector_public.search_batch(["别墅光伏", "成都光伏安装"], depth=10)
        assert len(results) >= 2


# ══════════════════════════════════════════════════════════════════════
# Collector — Mock 模式 (回归)
# ══════════════════════════════════════════════════════════════════════

class TestCollectorMockMode:
    """Collector mode=mock 路径不变。"""

    def test_search_mock(self, collector_mock: DouyinPublicCollector) -> None:
        results = collector_mock.search_by_keywords("别墅光伏", depth=30)
        assert len(results) >= 1

    def test_discover_account_mock(self, collector_mock: DouyinPublicCollector) -> None:
        detail = collector_mock.discover_account("reg_install_001")
        assert detail is not None
        assert detail.account_name == "成都光伏老王"

    def test_discover_videos_mock(self, collector_mock: DouyinPublicCollector) -> None:
        videos = collector_mock.discover_videos("reg_install_001", limit=5)
        assert len(videos) >= 1


# ══════════════════════════════════════════════════════════════════════
# 信号检测函数
# ══════════════════════════════════════════════════════════════════════

class TestSignalDetectors:
    """premium/region/housing 信号检测。"""

    def test_detect_premium_signals(self) -> None:
        sigs = detect_premium_signals("别墅光伏安装，阳光房改造")
        assert "别墅" in sigs
        assert "阳光房" in sigs

    def test_detect_premium_empty(self) -> None:
        sigs = detect_premium_signals("普通光伏安装")
        assert sigs == []

    def test_detect_region_signals(self) -> None:
        sigs = detect_region_signals("成都光伏安装，重庆服务")
        assert "成都" in sigs
        assert "重庆" in sigs

    def test_detect_housing_villa(self) -> None:
        assert detect_housing_signal("别墅光伏改造") == "别墅"

    def test_detect_housing_sunroom(self) -> None:
        assert detect_housing_signal("阳光房光伏顶设计") == "阳光房"

    def test_detect_housing_normal(self) -> None:
        assert detect_housing_signal("光伏安装案例") == "普通住宅"

    def test_is_rural_true(self) -> None:
        assert is_rural("农村光伏扶贫项目") is True

    def test_is_rural_false(self) -> None:
        assert is_rural("城市别墅光伏安装") is False


# ══════════════════════════════════════════════════════════════════════
# 业务边界
# ══════════════════════════════════════════════════════════════════════

class TestBusinessBoundary:
    """城市家庭光伏 / 别墅叠拼 / 小商业，禁止农村。"""

    def test_rural_excluded_from_search(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        """农村内容在搜索解析阶段被排除。"""
        from page_fetcher import _SEARCH_CARD_TEMPLATE
        rural_card = _SEARCH_CARD_TEMPLATE.format(
            account_name="农村光伏扶贫号",
            account_id="rural_001",
            verified="false",
            bio="农村光伏扶贫项目",
            follower_count="1000",
            content_count="10",
            ip_location="某县",
            account_type_hint="info_account",
        )
        html = f'<div id="search-result-list">\n<div class="search-card"{rural_card}\n</div>'
        results = parser.parse_search_results(html)
        assert len(results) == 0

    def test_premium_signals_in_parser(self, fetcher: MockPageFetcher, parser: DouyinPageParser) -> None:
        html = fetcher.fetch_account_page("city_case_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        high_value = {"别墅", "花园洋房", "阳光房"}
        assert bool(set(detail.premium_signals) & high_value)

    def test_no_rural_in_mock_data(self, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_search_page("光伏", "douyin")
        assert "农村" not in html
        assert "扶贫" not in html


# ══════════════════════════════════════════════════════════════════════
# 回归
# ══════════════════════════════════════════════════════════════════════

class TestRegression:
    """确保不破坏已有模块。"""

    def test_public_search_base_still_works(self) -> None:
        from public_search_base import SearchResultItem as SRI
        item = SRI(platform="douyin", account_id="001", account_name="test")
        assert item.to_dict()["platform"] == "douyin"

    def test_competitor_discovery_still_works(self) -> None:
        from competitor_discovery import CompetitorDiscovery, MOCK_CANDIDATES
        engine = CompetitorDiscovery(mode="mock")
        assert engine.mode == "mock"
        assert len(MOCK_CANDIDATES) >= 9

    def test_mock_candidates_intact(self) -> None:
        from competitor_discovery import MOCK_CANDIDATES
        for c in MOCK_CANDIDATES:
            assert "platform" in c
            assert "account_id" in c
            assert "discovery_keyword" in c

    def test_douyin_public_collector_importable(self) -> None:
        c = DouyinPublicCollector(mode="mock")
        assert c.platform_name == "douyin"
        assert c.mode == "mock"
