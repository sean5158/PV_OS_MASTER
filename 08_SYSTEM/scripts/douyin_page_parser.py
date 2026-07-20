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
    """抖音公开页面解析器。

    输入: 原始 HTML 字符串 (来自 PageFetcher)
    输出: 结构化数据对象

    每个 parse_* 方法都是纯函数，可独立测试。
    """

    def __init__(self) -> None:
        self.platform_name = "douyin"
        self.source_mode: str = "public"
        self.collected_time: str = ""

    # ── parse_search_results ──

    def parse_search_results(
        self, html: str, source_keyword: str = ""
    ) -> list[SearchResultItem]:
        """解析搜索综合Tab → 提取账号卡片。

        从 HTML 中提取每个 .search-card[data-type="user"]:
        - .nickname → account_name
        - .douyin-id → account_id
        - .verified-badge → 认证状态
        - .bio → bio_snippet
        - .follower-count → follower_count
        - .ip-location → ip_location
        - .account-type → account_type_hint
        """
        self.collected_time = datetime.now(TZ_SHANGHAI).isoformat()

        if not html or "search-card" not in html:
            logger.info("搜索解析: 无结果卡片")
            return []

        results: list[SearchResultItem] = []
        # 按搜索卡片分割
        cards = re.split(r'<div class="search-card"', html)[1:]

        for rank, card_html in enumerate(cards, start=1):
            account_id = _extract_text(card_html, "span", "douyin-id")
            account_name = _extract_text(card_html, "span", "nickname")

            if not account_id or not account_name:
                continue

            verified_text = _extract_text(card_html, "span", "verified-badge")
            follower_count = _extract_int(card_html, "span", "follower-count")
            ip_location = _extract_text(card_html, "span", "ip-location")
            bio = _extract_div_text(card_html, "bio")
            account_type_hint = _extract_text(card_html, "span", "account-type")

            # 业务边界检查
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
        """解析账号主页 → 提取账号详情。

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

        # 从 HTML 标签区域提取信号
        premium_from_tag = _extract_div_text(html, "premium-signals")
        region_from_tag = _extract_div_text(html, "region-signals")

        # 信号提取: 标签优先，再从 bio 补充
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

        # 评论需求密度: 基于 premium_signals 数量推算 (0-10)
        comment_demand_density = min(len(premium_signals) * 2, 10)

        # 业务边界
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
            last_active_days=3,  # 公开页面无法精确判断，默认近期活跃
        )

    # ── parse_video_list ──

    def parse_video_list(
        self, html: str, default_topic: str = ""
    ) -> list[VideoCandidate]:
        """解析作品列表 → 提取视频候选。

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
            # 相关度: 高端住宅 8-10, 普通住宅 5, 其他 3
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


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from page_fetcher import MockPageFetcher

    print("=" * 60)
    print("  DouyinPageParser — 自检")
    print("=" * 60)

    fetcher = MockPageFetcher()
    parser = DouyinPageParser()

    # ── 搜索解析 ──
    print("\n── parse_search_results ──")
    html = fetcher.fetch_search_page("别墅光伏", "douyin")
    results = parser.parse_search_results(html, source_keyword="别墅光伏")
    print(f"  '{'别墅光伏'}': {len(results)} 结果")
    for r in results:
        print(f"    [{r.rank}] {r.account_name} ({r.account_type_hint})")
    assert len(results) >= 2
    print("  ✓ 至少 2 个结果")

    # 空 HTML
    empty = parser.parse_search_results("")
    assert empty == []
    print("  ✓ 空 HTML → []")

    # ── 账号解析 ──
    print("\n── parse_account_page ──")
    html = fetcher.fetch_account_page("reg_install_001", "douyin")
    detail = parser.parse_account_page(html)
    assert detail is not None
    assert detail.account_name == "成都光伏老王"
    assert "别墅" in detail.premium_signals
    assert "成都" in detail.region_signals
    print(f"  {detail.account_name}")
    print(f"    类型: {detail.account_type_ai}")
    print(f"    高端: {detail.premium_signals}")
    print(f"    区域: {detail.region_signals}")
    print("  ✓ 字段完整")

    # 不存在
    none_result = parser.parse_account_page("")
    assert none_result is None
    print("  ✓ 无效 HTML → None")

    # ── 视频解析 ──
    print("\n── parse_video_list ──")
    html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
    videos = parser.parse_video_list(html, default_topic="成都光伏安装")
    assert len(videos) == 3
    for v in videos:
        print(f"  [{v.housing_signal}] {v.title} (相关度:{v.relevance_score})")
    print("  ✓ 3 个视频")

    # 空
    empty_vids = parser.parse_video_list("")
    assert empty_vids == []
    print("  ✓ 空 HTML → []")

    # ── 业务边界 ──
    print("\n── 业务边界 ──")
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

    print("\n✓ DouyinPageParser 自检完成\n")
