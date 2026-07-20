"""PV_OS Content Intelligence Agent V1.0。

实现 PV_OS_CONTENT_INTELLIGENCE_MODEL_V1.md:
    输入: VideoAsset → 分析 → VideoAnalysisResult → ContentInsight → 二创脚本

Mock 模式: 使用预置分析模板，不调用真实 AI API。

Usage::

    from content_intelligence_agent import ContentIntelligenceAgent
    agent = ContentIntelligenceAgent(mode="mock")
    insight = agent.generate_insight(video_assets)
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
CONTENT_ANALYTICS = PROJECT_ROOT / "04_CONTENT" / "analytics"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from video_asset import VideoAsset  # noqa: E402
from video_analysis_model import (  # noqa: E402
    VideoAnalysisResult, VideoAnalysisStore, ReusableElements,
)

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# ContentInsight 数据结构
# ══════════════════════════════════════════════════════════════════════

@dataclass
class TopicInsight:
    """选题洞察。"""
    topic: str = ""
    video_count: int = 0
    avg_comments: int = 0
    trend: str = "stable"           # rising / stable / declining
    demand_signals: int = 0         # 评论区需求信号数

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DemandGap:
    """需求缺口 — 客户在问但竞品没覆盖的话题。"""
    gap_topic: str = ""
    demand_signals: int = 0
    content_count: int = 0
    opportunity_score: int = 0      # 0-100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContentInsight:
    """内容洞察总览 — 对标 PV_OS_CONTENT_INTELLIGENCE_MODEL_V1.md §四.1。"""

    generated_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).isoformat())
    source_period: str = "最近30天"
    source_video_count: int = 0

    # 热点选题
    topics: list[TopicInsight] = field(default_factory=list)

    # 需求缺口
    demand_gaps: list[DemandGap] = field(default_factory=list)

    # 标题模式
    title_patterns: list[dict[str, str]] = field(default_factory=list)

    # 钩子公式
    hook_formulas: list[dict[str, str]] = field(default_factory=list)

    # 推荐选题 (PV_OS 差异化)
    recommended_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "source_period": self.source_period,
            "source_video_count": self.source_video_count,
            "topics": [t.to_dict() for t in self.topics],
            "demand_gaps": [g.to_dict() for g in self.demand_gaps],
            "title_patterns": self.title_patterns,
            "hook_formulas": self.hook_formulas,
            "recommended_topics": self.recommended_topics,
        }

    def save(self, path: Path | None = None) -> Path:
        """保存为 JSON。"""
        p = path or CONTENT_ANALYTICS / "content_insight.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("ContentInsight 保存 → %s", p)
        return p


# ══════════════════════════════════════════════════════════════════════
# Mock 分析模板
# ══════════════════════════════════════════════════════════════════════

MOCK_ANALYSIS_TEMPLATES: dict[str, dict[str, Any]] = {
    "别墅光伏": {
        "hook_3_seconds": "数字对比：电费从3000降到300",
        "pain_point": "城市别墅业主电费高但不知道光伏能省多少",
        "customer_type": "别墅业主",
        "video_structure": "痛点开场 → 方案展示 → 数据对比 → 客户见证 → 引导咨询",
        "title_pattern": "数字对比型：我家XX平米装了光伏，一年省了X万",
        "comment_trigger": "评论里很多人问'我家能装吗'——制造了代入感",
        "viral_reason": "强数字对比 + 真实案例 + 本地信任感",
        "turning_point": "第15秒展示电费账单对比",
        "closing_factor": "本地案例 + 可上门测量",
    },
    "家庭光伏": {
        "hook_3_seconds": "悬念式：光伏到底能不能省电？我用一年数据告诉你",
        "pain_point": "普通家庭担心装了没用、回本慢",
        "customer_type": "城市家庭",
        "video_structure": "悬念开场 → 安装过程 → 数据展示 → 答疑 → CTA",
        "title_pattern": "疑问解答型：普通家庭装光伏，一年后我后悔了吗？",
        "comment_trigger": "用真实数据打消疑虑，评论区变成咨询台",
        "viral_reason": "争议性话题 + 真实数据 + 情感共鸣",
        "turning_point": "第20秒展示电费对比图",
        "closing_factor": "用真实用户数据建立信任",
    },
    "阳光房光伏": {
        "hook_3_seconds": "场景痛点：阳光房太晒怎么办？一个方案解决两个问题",
        "pain_point": "阳光房夏天太热、冬天太冷",
        "customer_type": "阳光房/露台业主",
        "video_structure": "场景展示 → 问题提出 → 解决方案 → 效果展示 → 引导咨询",
        "title_pattern": "场景痛点型：阳光房太晒？装光伏一举两得",
        "comment_trigger": "很多人有阳光房但不知道能装光伏",
        "viral_reason": "差异化场景 + 一石二鸟（遮阳+发电）",
        "turning_point": "第10秒展示装光伏前后的温度对比",
        "closing_factor": "遮阳+发电双重价值",
    },
    "安装实拍": {
        "hook_3_seconds": "过程展示：光伏安装全过程，3分钟看懂",
        "pain_point": "用户担心安装麻烦、破坏屋顶",
        "customer_type": "观望中的潜在客户",
        "video_structure": "准备工作 → 施工过程 → 并网验收 → 效果展示",
        "title_pattern": "实录型：XX小区光伏安装全记录",
        "comment_trigger": "看到真实的本地案例产生信任",
        "viral_reason": "真实过程 + 本地场景 + 消除顾虑",
        "turning_point": "第30秒并网成功，电表倒转",
        "closing_factor": "本地真实案例降低决策门槛",
    },
}


# ══════════════════════════════════════════════════════════════════════
# ContentIntelligenceAgent
# ══════════════════════════════════════════════════════════════════════

class ContentIntelligenceAgent:
    """内容智能分析 Agent。

    职责:
    1. 分析竞品视频 → 生成 VideoAnalysisResult
    2. 汇总分析结果 → 生成 ContentInsight
    3. 推荐选题方向

    Mock 模式: 基于标题关键词匹配预置分析模板。
    """

    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode
        self.analysis_store = VideoAnalysisStore()

    def analyze_video(self, asset: VideoAsset) -> VideoAnalysisResult:
        """分析单个视频 → 生成拆解结果。

        Mock: 按标题关键词匹配模板。
        """
        if self.mode == "mock":
            return self._mock_analyze(asset)
        else:
            logger.warning("真实 AI 分析待实现，降级 mock")
            return self._mock_analyze(asset)

    def _mock_analyze(self, asset: VideoAsset) -> VideoAnalysisResult:
        """Mock: 按标题关键词匹配分析模板。"""
        template = None
        for keyword, tmpl in MOCK_ANALYSIS_TEMPLATES.items():
            if keyword in asset.title or keyword in asset.housing_signal:
                template = tmpl
                break

        if template is None:
            template = MOCK_ANALYSIS_TEMPLATES["家庭光伏"]

        # 计算评分
        viral_score = min(
            (asset.like_count // 100) + (asset.comment_count * 2) + (asset.share_count * 3),
            100,
        )
        reusability_score = 80 if asset.housing_signal in ("别墅", "阳光房", "叠拼") else 60

        # 生成差异化建议
        angle_suggestions = self._generate_angle_suggestions(asset)

        result = VideoAnalysisResult(
            video_id=asset.video_id,
            video_title=asset.title,
            viral_score=viral_score,
            reusability_score=reusability_score,
            reusable=ReusableElements(
                hook_template=template["hook_3_seconds"],
                structure_template=template["video_structure"],
                key_phrases=template.get("key_phrases", []),
                angle_suggestions=angle_suggestions,
            ),
            **{k: v for k, v in template.items()
               if k in VideoAnalysisResult.__dataclass_fields__},
        )

        logger.info("分析视频: %s → 爆款指数 %d", asset.video_id, viral_score)
        return result

    def _generate_angle_suggestions(self, asset: VideoAsset) -> list[str]:
        """生成 PV_OS 差异化角度建议。"""
        suggestions = ["加入四川本地元素", "展示真实施工现场"]

        if asset.housing_signal in ("别墅", "叠拼"):
            suggestions.append("成都别墅案例对标")
        if asset.housing_signal == "阳光房":
            suggestions.append("成都日照数据计算回本")
        if "安装" in asset.title:
            suggestions.append("展示川渝黔安装实拍")
        if "报价" in asset.title or "多少钱" in asset.title:
            suggestions.append("成都本地报价对比")

        return suggestions

    def analyze_batch(self, assets: list[VideoAsset]) -> list[VideoAnalysisResult]:
        """批量分析视频。"""
        results: list[VideoAnalysisResult] = []
        for asset in assets:
            result = self.analyze_video(asset)
            self.analysis_store.save(result)
            results.append(result)
        logger.info("批量分析: %d 视频 → %d 结果", len(assets), len(results))
        return results

    def generate_insight(
        self, assets: list[VideoAsset],
        results: list[VideoAnalysisResult] | None = None,
    ) -> ContentInsight:
        """生成内容洞察总览。

        Args:
            assets: 竞品视频资产列表
            results: 已生成的分析结果 (可选，如不提供则自动分析)

        Returns:
            ContentInsight 含选题/缺口/标题模式/钩子公式
        """
        if results is None:
            results = self.analyze_batch(assets)

        insight = ContentInsight(
            source_video_count=len(assets),
        )

        # 热点选题聚合
        topic_map: dict[str, list[VideoAnalysisResult]] = {}
        for r in results:
            key = r.customer_type or "通用"
            topic_map.setdefault(key, []).append(r)

        for topic, topic_results in topic_map.items():
            insight.topics.append(TopicInsight(
                topic=f"{topic}光伏内容",
                video_count=len(topic_results),
                avg_comments=sum(r.viral_score for r in topic_results) // max(len(topic_results), 1),
                trend="rising" if len(topic_results) >= 2 else "stable",
                demand_signals=len(topic_results) * 5,
            ))

        # 需求缺口 (Mock: 从 housing_signal 和 title 推断)
        gap_keywords = {
            "老旧小区光伏安装": ["小区", "公寓", "高层"],
            "阳光房光伏避坑": ["阳光房", "避坑", "后悔"],
            "光伏储能一体": ["储能", "储电", "电池"],
        }
        for gap, keywords in gap_keywords.items():
            count = sum(1 for a in assets if any(k in a.title for k in keywords))
            insight.demand_gaps.append(DemandGap(
                gap_topic=gap,
                demand_signals=count * 8,
                content_count=count,
                opportunity_score=min(count * 30, 100),
            ))

        # 标题模式
        insight.title_patterns = [
            {"pattern": "数字对比型", "example": "电费从3000降到300", "effectiveness": "high"},
            {"pattern": "场景痛点型", "example": "阳光房太晒怎么办", "effectiveness": "high"},
            {"pattern": "疑问解答型", "example": "装了光伏一年后我后悔了吗", "effectiveness": "medium"},
            {"pattern": "过程实录型", "example": "XX小区光伏安装全记录", "effectiveness": "high"},
        ]

        # 钩子公式
        insight.hook_formulas = [
            {"formula": "数字对比型", "example": "电费从3000降到300"},
            {"formula": "场景痛点型", "example": "阳光房太晒怎么办？"},
            {"formula": "悬念反问型", "example": "光伏到底能不能省电？"},
            {"formula": "过程展示型", "example": "光伏安装全过程，3分钟看懂"},
        ]

        # 推荐选题 (PV_OS 差异化)
        insight.recommended_topics = [
            "成都别墅业主：光伏一年真实电费对比",
            "重庆阳光房改造：遮阳+发电一石二鸟",
            "贵阳小商业光伏：棋牌室/茶楼月省电费实测",
            "成都老旧小区屋顶光伏安装全记录",
            "叠拼业主光伏避坑指南（川渝黔版）",
        ]

        insight.save()
        logger.info("生成内容洞察: %d 选题, %d 缺口", len(insight.topics), len(insight.demand_gaps))
        return insight


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  ContentIntelligenceAgent — 自检")
    print("=" * 60)

    # Mock 视频
    assets = [
        VideoAsset(video_id="dy_v001", platform="douyin",
                   title="别墅光伏安装实拍", author_name="成都光伏老王",
                   housing_signal="别墅", like_count=1500,
                   comment_count=85, share_count=45, relevance_score=9),
        VideoAsset(video_id="dy_v002", platform="douyin",
                   title="阳光房光伏改造案例", author_name="别墅光伏改造日记",
                   housing_signal="阳光房", like_count=2300,
                   comment_count=120, share_count=67, relevance_score=8),
        VideoAsset(video_id="dy_v003", platform="douyin",
                   title="家庭光伏安装流程", author_name="正泰安能",
                   housing_signal="普通住宅", like_count=800,
                   comment_count=45, share_count=20, relevance_score=6),
    ]

    agent = ContentIntelligenceAgent(mode="mock")

    # 分析单个
    result = agent.analyze_video(assets[0])
    assert result.video_title == "别墅光伏安装实拍"
    assert "别墅" in result.hook_3_seconds or result.video_title == "别墅光伏安装实拍"
    print(f"  分析: {result.video_title}")
    print(f"    爆款指数: {result.viral_score}")
    print(f"    钩子: {result.hook_3_seconds[:40]}...")
    print(f"    可复用元素: {result.reusable.angle_suggestions}")

    # 批量分析
    results = agent.analyze_batch(assets)
    assert len(results) == 3
    print(f"\n  批量分析: {len(results)} 视频")

    # 生成洞察
    insight = agent.generate_insight(assets, results)
    assert len(insight.topics) >= 1
    assert len(insight.demand_gaps) == 3
    assert len(insight.recommended_topics) == 5
    print(f"\n  内容洞察:")
    print(f"    选题: {len(insight.topics)}")
    for t in insight.topics:
        print(f"      - {t.topic} ({t.video_count}视频, 趋势:{t.trend})")
    print(f"    需求缺口: {len(insight.demand_gaps)}")
    for g in insight.demand_gaps:
        print(f"      - {g.gap_topic} (机会:{g.opportunity_score})")
    print(f"    推荐选题: {len(insight.recommended_topics)}")
    for t in insight.recommended_topics[:3]:
        print(f"      - {t}")

    # 保存
    insight_path = insight.save()
    assert insight_path.exists()
    print(f"\n  ✓ ContentInsight 已保存: {insight_path}")

    print("\n✓ ContentIntelligenceAgent 自检完成\n")
