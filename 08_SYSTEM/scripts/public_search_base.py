"""PV_OS Public Search Collector 抽象基类。

定义平台公开搜索的标准接口: search_by_keywords / discover_account / discover_videos。
与 BaseCollector 互补 —— BaseCollector 管评论采集，本类管账号/视频发现。

三模式定位:
    mock     → 内置测试数据 (本文档实现)
    public   → 平台公开搜索框+页面解析 (P2-3)
    official → 平台官方API (P2后期)

Usage::

    from douyin_public_collector import DouyinPublicCollector

    collector = DouyinPublicCollector(mode="mock")
    results = collector.search_by_keywords("别墅光伏", depth=30)
    detail = collector.discover_account("reg_install_001")
    videos = collector.discover_videos("reg_install_001", time_range_days=30)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════════

@dataclass
class SearchResultItem:
    """平台搜索结果条目 — search_by_keywords() 输出。"""
    platform: str = ""
    account_id: str = ""
    account_name: str = ""
    account_url: str = ""
    account_type_hint: str = ""   # 类型提示 (个人/企业/媒体)
    bio_snippet: str = ""
    follower_count: int = 0
    ip_location: str = ""
    source_type: str = "search"   # search | suggest | tag
    discovery_keyword: str = ""
    rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AccountDetail:
    """账号详情 — discover_account() 输出。

    对标 competitor_master.csv 字段 + COMPETITOR_SCORE_RULE.md 六维评分输入。
    """
    platform: str = ""
    account_id: str = ""
    account_name: str = ""
    account_url: str = ""
    bio: str = ""
    follower_count: int = 0
    content_count: int = 0
    ip_location: str = ""
    verified: bool = False
    account_type_ai: str = ""           # AI分类
    recent_topics: list[str] = field(default_factory=list)
    premium_signals: list[str] = field(default_factory=list)    # 别墅/阳光房/民宿...
    region_signals: list[str] = field(default_factory=list)     # 成都/重庆/贵阳...
    comment_demand_density: int = 0     # 0-10
    last_active_days: int = 7

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["recent_topics"] = list(self.recent_topics)
        d["premium_signals"] = list(self.premium_signals)
        d["region_signals"] = list(self.region_signals)
        return d


@dataclass
class VideoCandidate:
    """视频候选 — discover_videos() 输出。"""
    platform: str = ""
    video_id: str = ""
    video_url: str = ""
    title: str = ""
    topic: str = ""
    publish_time: str = ""
    comment_count: int = 0
    housing_signal: str = ""      # 别墅/叠拼/阳光房/普通住宅
    relevance_score: int = 0      # 0-10

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════
# 抽象基类
# ══════════════════════════════════════════════════════════════════════

class PublicSearchCollector(ABC):
    """平台公开搜索采集器抽象基类。

    子类必须实现三个抽象方法。
    速率限制由子类自行管理（可使用 live_collector_base.RateLimiter）。
    """

    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode          # mock | public | official
        self.platform_name: str = ""

    @abstractmethod
    def search_by_keywords(
        self, keyword: str, depth: int = 30
    ) -> list[SearchResultItem]:
        """平台搜索框 → 搜索结果解析。

        Args:
            keyword: 搜索关键词
            depth: 搜索深度 (默认30)

        Returns:
            搜索结果条目列表

        Mock: 从预置候选库匹配。
        Public: 解析平台搜索框返回的公开页面内容。
        """
        ...

    @abstractmethod
    def discover_account(
        self, account_id: str
    ) -> AccountDetail | None:
        """账号主页 → 账号详情。

        Args:
            account_id: 平台账号ID

        Returns:
            账号详情，账号不可访问时返回 None

        Mock: 从预置候选库返回详情。
        Public: 解析账号主页公开内容。
        """
        ...

    @abstractmethod
    def discover_videos(
        self, account_id: str, time_range_days: int = 30, limit: int = 10
    ) -> list[VideoCandidate]:
        """作品列表 → 视频候选。

        Args:
            account_id: 平台账号ID
            time_range_days: 时间范围
            limit: 最大返回数

        Returns:
            视频候选列表

        Mock: 从预置 content_sample 生成。
        Public: 解析作品列表公开内容。
        """
        ...

    def validate_result(self, item: SearchResultItem) -> bool:
        """搜索结果基础校验。"""
        if not item.account_id or not item.account_name:
            return False
        return True

    def search_batch(
        self, keywords: list[str], depth: int = 30
    ) -> list[SearchResultItem]:
        """批量搜索 — 对多个关键词依次搜索并去重。

        Args:
            keywords: 搜索关键词列表
            depth: 搜索深度

        Returns:
            去重后的搜索结果
        """
        seen: set[str] = set()
        results: list[SearchResultItem] = []
        for kw in keywords:
            for item in self.search_by_keywords(kw, depth):
                if item.account_id not in seen:
                    seen.add(item.account_id)
                    results.append(item)
        logger.info("批量搜索: %d关键词 → %d去重结果", len(keywords), len(results))
        return results
