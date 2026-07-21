"""PV_OS 抖音公开搜索采集器。

实现 PublicSearchCollector 接口，对抖音平台公开数据进行搜索和发现。

三模式:
    mock     → 内置候选库 MOCK_CANDIDATES 匹配
    public   → PageFetcher + PageParser 解析公开页面 (P2-3)
    official → 抖音开放平台 API (P2后期)

Usage::

    from douyin_public_collector import DouyinPublicCollector

    collector = DouyinPublicCollector(mode="public")
    results = collector.search_by_keywords("别墅光伏", depth=30)
    detail = collector.discover_account("reg_install_001")
    videos = collector.discover_videos("reg_install_001")

规则依据:
- COMPETITOR_DISCOVERY_ALGORITHM.md §二.4: 抖音搜索流程
- COMMENT_COLLECTOR_AGENT_DESIGN.md §二.1: 抖音平台特征
- PV_OS_P2_ARCHITECTURE_DESIGN.md V2.1: 公开搜索定位
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from public_search_base import (  # noqa: E402
    PublicSearchCollector,
    SearchResultItem,
    AccountDetail,
    VideoCandidate,
)
from competitor_discovery import MOCK_CANDIDATES  # noqa: E402

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))


class DouyinPublicCollector(PublicSearchCollector):
    """抖音公开搜索采集器。

    P2-2: Mock 实现。
    P2-3: public 模式接入 PageFetcher + PageParser。
    """

    def __init__(self, mode: str = "mock", page_fetcher=None) -> None:
        super().__init__(mode)
        self.platform_name = "douyin"
        self._fetcher = page_fetcher
        self._parser = None  # 延迟加载

    def _ensure_parser(self):
        """延迟加载 Parser（避免循环导入 + 启动开销）。"""
        if self._parser is None:
            from douyin_page_parser import DouyinPageParser  # noqa: PLC0415
            self._parser = DouyinPageParser(mode=self.mode)

    def _ensure_fetcher(self):
        """延迟加载 Fetcher，按模式选择。"""
        if self._fetcher is None:
            if self.mode == "public":
                from page_fetcher import PublicPageFetcher  # noqa: PLC0415
                self._fetcher = PublicPageFetcher()
                logger.info("DouyinPublicCollector: 启用 PublicPageFetcher (真实HTTP)")
            else:
                from page_fetcher import MockPageFetcher  # noqa: PLC0415
                self._fetcher = MockPageFetcher()

    # ══════════════════════════════════════════════════════════════════
    # search_by_keywords
    # ══════════════════════════════════════════════════════════════════

    def search_by_keywords(
        self, keyword: str, depth: int = 30
    ) -> list[SearchResultItem]:
        """抖音搜索框 → 搜索结果。

        mock:   从 MOCK_CANDIDATES 匹配。
        public: PageFetcher → HTML → PageParser → SearchResultItem[]。
        official: 降级到 mock (待实现)。
        """
        if self.mode == "mock":
            return self._mock_search(keyword, depth)
        elif self.mode == "public":
            return self._public_search(keyword, depth)
        else:
            logger.warning("抖音 official 模式待实现，降级 mock")
            return self._mock_search(keyword, depth)

    def _mock_search(self, keyword: str, depth: int) -> list[SearchResultItem]:
        """Mock: 关键词匹配候选库中的抖音账号。"""
        results: list[SearchResultItem] = []
        rank = 0

        for c in MOCK_CANDIDATES:
            if c["platform"] != "douyin":
                continue

            matched = keyword in c.get("discovery_keyword", "")
            if not matched:
                for sample in c.get("content_sample", []):
                    if keyword in sample:
                        matched = True
                        break

            if not matched:
                continue

            rank += 1
            results.append(SearchResultItem(
                platform="douyin",
                account_id=c["account_id"],
                account_name=c["account_name"],
                account_url=c["account_url"],
                account_type_hint=c.get("account_type", ""),
                bio_snippet=c.get("bio", ""),
                follower_count=c.get("follower_count", 0),
                ip_location=c.get("ip_location", ""),
                source_type="search",
                discovery_keyword=keyword,
                rank=rank,
            ))

        logger.info("抖音搜索: '%s' → %d 结果 (Mock)", keyword, len(results))
        return results[:depth]

    def _public_search(self, keyword: str, depth: int) -> list[SearchResultItem]:
        """Public: PageFetcher → Parser 搜索。"""
        self._ensure_fetcher()
        self._ensure_parser()

        html = self._fetcher.fetch_search_page(keyword, self.platform_name, depth)
        results = self._parser.parse_search_results(html, source_keyword=keyword)
        # 附加 source_mode / source_keyword / source_platform
        for r in results:
            r.source_type = "public_search"
        logger.info("抖音搜索: '%s' → %d 结果 (Public)", keyword, len(results))
        return results[:depth]

    # ══════════════════════════════════════════════════════════════════
    # discover_account
    # ══════════════════════════════════════════════════════════════════

    def discover_account(
        self, account_id: str
    ) -> AccountDetail | None:
        """抖音账号主页 → 账号详情。

        mock:   从 MOCK_CANDIDATES 返回。
        public: PageFetcher → HTML → PageParser → AccountDetail。
        official: 降级到 mock。
        """
        if self.mode == "mock":
            return self._mock_discover_account(account_id)
        elif self.mode == "public":
            return self._public_discover_account(account_id)
        else:
            logger.warning("抖音 official 账号发现待实现，降级 mock")
            return self._mock_discover_account(account_id)

    def _mock_discover_account(self, account_id: str) -> AccountDetail | None:
        raw = next((c for c in MOCK_CANDIDATES if c["account_id"] == account_id), None)
        if raw is None:
            logger.warning("抖音账号不存在: %s", account_id)
            return None

        return AccountDetail(
            platform="douyin",
            account_id=raw["account_id"],
            account_name=raw["account_name"],
            account_url=raw["account_url"],
            bio=raw.get("bio", ""),
            follower_count=raw.get("follower_count", 0),
            content_count=len(raw.get("content_sample", [])),
            ip_location=raw.get("ip_location", ""),
            verified=raw.get("account_type", "") != "casual",
            account_type_ai=raw.get("account_type", ""),
            recent_topics=raw.get("content_sample", []),
            premium_signals=raw.get("premium_signals", []),
            region_signals=raw.get("region_signals", []),
            comment_demand_density=raw.get("comment_signals", 0),
            last_active_days=raw.get("activity_days", 7),
        )

    def _public_discover_account(self, account_id: str) -> AccountDetail | None:
        """Public: PageFetcher → Parser 账号发现。"""
        self._ensure_fetcher()
        self._ensure_parser()

        html = self._fetcher.fetch_account_page(account_id, self.platform_name)
        if not html:
            return None
        return self._parser.parse_account_page(html)

    # ══════════════════════════════════════════════════════════════════
    # discover_videos
    # ══════════════════════════════════════════════════════════════════

    def discover_videos(
        self, account_id: str, time_range_days: int = 30, limit: int = 10
    ) -> list[VideoCandidate]:
        """抖音作品列表 → 视频候选。

        mock:   从 MOCK_CANDIDATES.content_sample 生成。
        public: PageFetcher → HTML → PageParser → VideoCandidate[]。
        official: 降级到 mock。
        """
        if self.mode == "mock":
            return self._mock_discover_videos(account_id, time_range_days, limit)
        elif self.mode == "public":
            return self._public_discover_videos(account_id, time_range_days, limit)
        else:
            logger.warning("抖音 official 视频发现待实现，降级 mock")
            return self._mock_discover_videos(account_id, time_range_days, limit)

    def _mock_discover_videos(
        self, account_id: str, time_range_days: int, limit: int
    ) -> list[VideoCandidate]:
        raw = next((c for c in MOCK_CANDIDATES if c["account_id"] == account_id), None)
        if raw is None:
            return []

        now = datetime.now(TZ_SHANGHAI)
        videos: list[VideoCandidate] = []

        for i, title in enumerate(raw.get("content_sample", []), start=1):
            housing = self._detect_housing_signal(title)

            videos.append(VideoCandidate(
                platform="douyin",
                video_id=f"{account_id}_v{i:03d}",
                video_url=f"https://douyin.com/video/{account_id}_v{i:03d}",
                title=title,
                topic=raw.get("discovery_keyword", ""),
                publish_time=(now - timedelta(days=raw.get("activity_days", 0) + i)).strftime("%Y-%m-%d"),
                comment_count=raw.get("comment_signals", 0) * 10,
                housing_signal=housing,
                relevance_score=8 if housing != "普通住宅" else 5,
            ))

        return videos[:limit]

    def _public_discover_videos(
        self, account_id: str, time_range_days: int, limit: int
    ) -> list[VideoCandidate]:
        """Public: PageFetcher → Parser 视频发现。"""
        self._ensure_fetcher()
        self._ensure_parser()

        html = self._fetcher.fetch_video_list_page(account_id, self.platform_name, limit)
        if not html:
            return []
        return self._parser.parse_video_list(html)[:limit]

    # ══════════════════════════════════════════════════════════════════
    # 工具
    # ══════════════════════════════════════════════════════════════════

    def _detect_housing_signal(self, title: str) -> str:
        """从标题中检测房屋场景信号。"""
        signals = {
            "别墅": "别墅", "叠拼": "叠拼", "阳光房": "阳光房",
            "露台": "露台", "花园洋房": "花园洋房",
            "民宿": "民宿", "酒店": "酒店", "茶楼": "茶楼",
        }
        for keyword, signal in signals.items():
            if keyword in title:
                return signal
        return "普通住宅"


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Douyin Public Collector — 自检 (P2-3)")
    print("=" * 60)

    # ── Mock 模式 ──
    print("\n── mode=mock ──")
    collector_mock = DouyinPublicCollector(mode="mock")
    results = collector_mock.search_by_keywords("别墅光伏", depth=10)
    print(f"  搜索 '别墅光伏': {len(results)} 结果")
    assert len(results) >= 1
    print("  ✓ mock 模式正常")

    # ── Public 模式 (MockPageFetcher) ──
    print("\n── mode=public (MockPageFetcher) ──")
    from page_fetcher import MockPageFetcher  # noqa: PLC0415
    fetcher = MockPageFetcher()
    collector_public = DouyinPublicCollector(mode="public", page_fetcher=fetcher)

    # search
    results = collector_public.search_by_keywords("别墅光伏", depth=10)
    print(f"  搜索 '别墅光伏': {len(results)} 结果")
    for r in results[:3]:
        print(f"    [{r.rank}] {r.account_name} ({r.account_type_hint})")
    assert len(results) >= 2

    # account
    detail = collector_public.discover_account("reg_install_001")
    assert detail is not None
    print(f"  账号: {detail.account_name}")
    print(f"    高端: {detail.premium_signals}")
    print(f"    区域: {detail.region_signals}")

    # videos
    videos = collector_public.discover_videos("reg_install_001", limit=5)
    print(f"  视频: {len(videos)} 候选")
    for v in videos:
        print(f"    [{v.housing_signal}] {v.title}")

    # batch
    batch = collector_public.search_batch(["别墅光伏", "成都光伏安装", "家庭光伏"], depth=10)
    print(f"  批量搜索: {len(batch)} 去重结果")

    print(f"\n  ✓ public 模式 (MockPageFetcher) 全链路正常")
    print("  source_mode=public, source_platform=douyin")
    print(f"  collected_time={fetcher.collected_time}")

    # ── Official 降级 ──
    print("\n── mode=official (降级 mock) ──")
    collector_official = DouyinPublicCollector(mode="official")
    results = collector_official.search_by_keywords("光伏", depth=5)
    print(f"  搜索 '光伏': {len(results)} 结果 (降级 mock)")
    assert len(results) >= 1
    print("  ✓ official 降级正常")

    print("\n✓ Douyin Public Collector 自检完成 (P2-3)\n")
