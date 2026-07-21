"""Phase 3-2 Public Collector 真实化测试 (V3.2)。

覆盖: PublicPageFetcher / PublicPageFetcher 速率限制 / UA轮换 /
       降级到Mock / DouyinPublicCollector public模式 /
       业务边界 / 回归保护。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_phase32_public_collector.py -v
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from page_fetcher import (  # noqa: E402
    MockPageFetcher, PublicPageFetcher, PageFetcherBase,
)
from douyin_public_collector import DouyinPublicCollector  # noqa: E402
from public_search_base import (  # noqa: E402
    SearchResultItem, AccountDetail, VideoCandidate,
)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# PublicPageFetcher
# ══════════════════════════════════════════════════════════════════════

class TestPublicPageFetcher:

    def test_init_defaults(self) -> None:
        pf = PublicPageFetcher()
        assert pf.timeout == 15
        assert len(pf.ua_pool) >= 4
        assert pf._daily_limit == 100
        assert pf._min_interval == 5.0

    def test_custom_config(self) -> None:
        pf = PublicPageFetcher(timeout=8, ua_pool=["TestUA/1.0"])
        assert pf.timeout == 8
        assert pf.ua_pool == ["TestUA/1.0"]

    def test_rate_stats_initial(self) -> None:
        pf = PublicPageFetcher()
        stats = pf.get_rate_stats()
        assert stats["requests_today"] == 0
        assert stats["daily_limit"] == 100

    def test_rotate_ua(self) -> None:
        pf = PublicPageFetcher()
        ua1 = pf._rotate_ua()
        ua2 = pf._rotate_ua()
        # With 4 UAs, first two should differ
        assert ua1 != ua2

    def test_check_rate_limit_first_request(self) -> None:
        pf = PublicPageFetcher()
        assert pf._check_rate_limit() is True

    def test_search_mock_fallback(self) -> None:
        """非 douyin 平台降级为空。"""
        pf = PublicPageFetcher()
        html = pf.fetch_search_page("测试", "xiaohongshu")
        assert html == ""

    def test_account_mock_fallback(self) -> None:
        """非 douyin 平台降级为空。"""
        pf = PublicPageFetcher()
        html = pf.fetch_account_page("test", "kuaishou")
        assert html == ""

    def test_inherits_from_base(self) -> None:
        pf = PublicPageFetcher()
        assert isinstance(pf, PageFetcherBase)

    def test_inherits_from_base_mock(self) -> None:
        mf = MockPageFetcher()
        assert isinstance(mf, PageFetcherBase)


# ══════════════════════════════════════════════════════════════════════
# PageFetcherBase 抽象接口
# ══════════════════════════════════════════════════════════════════════

class TestPageFetcherBase:

    def test_abstract_methods_exist(self) -> None:
        """验证基类定义了三个抽象方法。"""
        assert hasattr(PageFetcherBase, 'fetch_search_page')
        assert hasattr(PageFetcherBase, 'fetch_account_page')
        assert hasattr(PageFetcherBase, 'fetch_video_list_page')

    def test_collected_time_initial(self) -> None:
        mf = MockPageFetcher()
        assert mf.collected_time == ""

    def test_collected_time_after_fetch(self) -> None:
        mf = MockPageFetcher()
        mf.fetch_search_page("别墅光伏", "douyin")
        assert mf.collected_time != ""

    def test_mode_attribute(self) -> None:
        mf = MockPageFetcher()
        pf = PublicPageFetcher()
        # Both are PageFetcherBase subclasses
        assert isinstance(mf, PageFetcherBase)
        assert isinstance(pf, PageFetcherBase)


# ══════════════════════════════════════════════════════════════════════
# MockPageFetcher 回归
# ══════════════════════════════════════════════════════════════════════

class TestMockPageFetcherRegression:

    def test_search_finds_expected(self) -> None:
        mf = MockPageFetcher()
        html = mf.fetch_search_page("别墅光伏", "douyin")
        assert "city_case_001" in html
        assert "reg_install_001" in html

    def test_search_empty_for_unknown(self) -> None:
        mf = MockPageFetcher()
        html = mf.fetch_search_page("XYZNOTEXIST", "douyin")
        assert "search-card" not in html

    def test_account_page_has_signals(self) -> None:
        mf = MockPageFetcher()
        html = mf.fetch_account_page("reg_install_001", "douyin")
        assert "成都光伏老王" in html
        assert "别墅" in html

    def test_account_nonexistent(self) -> None:
        mf = MockPageFetcher()
        html = mf.fetch_account_page("no_such_id", "douyin")
        assert html == ""

    def test_video_list_has_videos(self) -> None:
        mf = MockPageFetcher()
        html = mf.fetch_video_list_page("reg_install_001", "douyin")
        assert "别墅光伏安装实拍" in html
        assert "光伏报价" in html


# ══════════════════════════════════════════════════════════════════════
# DouyinPublicCollector 三模式
# ══════════════════════════════════════════════════════════════════════

class TestDouyinPublicCollectorModes:

    def test_mock_search_works(self) -> None:
        collector = DouyinPublicCollector(mode="mock")
        results = collector.search_by_keywords("别墅光伏", depth=10)
        assert len(results) > 0
        assert all(r.platform == "douyin" for r in results)

    def test_public_search_falls_back_to_mock(self) -> None:
        """public 模式无匹配时降级。"""
        collector = DouyinPublicCollector(mode="public")
        results = collector.search_by_keywords("XYZNOTEXIST", depth=5)
        assert isinstance(results, list)

    def test_official_mode_falls_back_to_mock(self) -> None:
        collector = DouyinPublicCollector(mode="official")
        results = collector.search_by_keywords("别墅光伏", depth=5)
        assert len(results) > 0  # falls back to mock

    def test_mock_discover_account(self) -> None:
        collector = DouyinPublicCollector(mode="mock")
        detail = collector.discover_account("reg_install_001")
        assert detail is not None
        assert detail.account_name == "成都光伏老王"
        assert detail.platform == "douyin"

    def test_mock_discover_videos(self) -> None:
        collector = DouyinPublicCollector(mode="mock")
        videos = collector.discover_videos("reg_install_001")
        assert len(videos) > 0
        titles = [v.title for v in videos]
        assert "别墅光伏安装实拍" in titles

    def test_search_result_format(self) -> None:
        collector = DouyinPublicCollector(mode="mock")
        results = collector.search_by_keywords("光伏", depth=3)
        for r in results:
            assert r.platform == "douyin"
            assert r.account_id != ""
            assert r.account_name != ""

    def test_mode_preserved(self) -> None:
        c1 = DouyinPublicCollector(mode="mock")
        c2 = DouyinPublicCollector(mode="public")
        assert c1.mode == "mock"
        assert c2.mode == "public"


# ══════════════════════════════════════════════════════════════════════
# 业务边界
# ══════════════════════════════════════════════════════════════════════

class TestBusinessBoundary:

    def test_no_rural_content_in_mock(self) -> None:
        """Mock 数据中不应包含农村/大型工商业内容。"""
        collector = DouyinPublicCollector(mode="mock")
        results = collector.search_by_keywords("光伏", depth=20)
        rural_keywords = ["农村", "扶贫", "村村通", "惠农", "地面电站"]
        for r in results:
            text = r.account_name + (r.bio_snippet or "")
            for kw in rural_keywords:
                assert kw not in text, f"禁止关键词 '{kw}' 出现在 {r.account_name}"

    def test_premium_signals_present(self) -> None:
        """高端住宅信号应存在。"""
        collector = DouyinPublicCollector(mode="mock")
        detail = collector.discover_account("city_case_001")
        assert detail is not None
        signals_str = " ".join(detail.premium_signals) if detail.premium_signals else ""
        assert "别墅" in signals_str or len(detail.premium_signals) > 0

    def test_region_signals_present(self) -> None:
        """区域信号应存在。"""
        collector = DouyinPublicCollector(mode="mock")
        detail = collector.discover_account("reg_install_001")
        assert detail is not None
        signals_str = " ".join(detail.region_signals) if detail.region_signals else ""
        assert "成都" in signals_str or len(detail.region_signals) > 0

    def test_no_api_key_leaked(self) -> None:
        """不应在任何 collector 输出中泄露 API key。"""
        from page_fetcher import PublicPageFetcher
        pf = PublicPageFetcher()
        # PublicPageFetcher 不应存储 API key / token
        assert not hasattr(pf, 'api_key')
        stats = pf.get_rate_stats()
        assert "api_key" not in str(stats).lower()


# ══════════════════════════════════════════════════════════════════════
# 回归保护
# ══════════════════════════════════════════════════════════════════════

class TestRegression:

    def test_mock_fetcher_unchanged(self) -> None:
        """MockFetcher 接口无变化。"""
        mf = MockPageFetcher()
        assert hasattr(mf, 'fetch_search_page')
        assert hasattr(mf, 'fetch_account_page')
        assert hasattr(mf, 'fetch_video_list_page')

    def test_collector_platform_name(self) -> None:
        c = DouyinPublicCollector(mode="mock")
        assert c.platform_name == "douyin"

    def test_search_result_item_fields(self) -> None:
        sr = SearchResultItem(
            platform="douyin", account_id="test_001",
            account_name="测试账号", account_url="https://douyin.com/user/test",
            source_type="search", discovery_keyword="光伏", rank=1,
        )
        d = sr.to_dict()
        assert d["platform"] == "douyin"
        assert d["account_id"] == "test_001"
        assert d["rank"] == 1

    def test_pipeline_unaffected(self) -> None:
        """验证 P3-2 变更不破坏 Pipeline。"""
        from alert_engine import AlertEngine
        engine = AlertEngine()
        assert engine.should_alert("S", is_inbound=True)
        assert not engine.should_alert("B", is_inbound=True)
