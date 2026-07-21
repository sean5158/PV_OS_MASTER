"""PV_OS Content Insight Agent V1.0 — Phase 3-3 内容洞察聚合引擎。

实现 Phase3-3_CONTENT_INTELLIGENCE_DESIGN.md §五 ContentInsight:
    跨视频聚合分析 → 发现选题缺口 → 生成内容策略建议

Mock 模式: 使用启发式规则，不调用真实 AI API。

Usage::

    from content_insight_agent import ContentInsightAgent, ContentInsight
    agent = ContentInsightAgent(mode="mock")
    insight = agent.generate_insight(analysis_results, video_assets)
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
CONTENT_STRATEGY = PROJECT_ROOT / "04_CONTENT" / "strategy"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from video_analysis_model import (  # noqa: E402
    VideoAnalysisResult, ReusableElements,
)

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))

INSIGHT_INDEX_CSV = CONTENT_STRATEGY / "content_insight_index.csv"
INSIGHT_INDEX_FIELDS = [
    "insight_id", "generated_at", "source_period",
    "source_video_count", "topic_count", "gap_count",
    "top_recommended_topic",
]


# ══════════════════════════════════════════════════════════════════════
# 数据模型
# ══════════════════════════════════════════════════════════════════════

@dataclass
class TopicInsight:
    """选题洞察 — 某个话题的聚合分析。"""
    topic: str = ""                     # 话题名称
    video_count: int = 0                # 关联视频数
    avg_viral_score: int = 0            # 平均爆款指数
    avg_engagement: int = 0             # 平均互动量
    trend: str = "stable"               # rising / stable / declining
    demand_signals: int = 0             # 评论区需求信号数
    competitive_intensity: str = "medium"  # high / medium / low

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TopicInsight":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class DemandGap:
    """需求缺口 — 客户在问但竞品没覆盖的话题。"""
    gap_topic: str = ""                 # 缺口话题
    demand_signals: int = 0             # 需求强度
    content_count: int = 0              # 已有内容数
    opportunity_score: int = 0          # 机会指数 0-100
    suggested_angle: str = ""           # PV_OS 建议切入角度
    target_audience: str = ""           # 目标客群

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DemandGap":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class ContentCalendarEntry:
    """内容发布计划条目。"""
    day: str = ""                       # 周几
    topic: str = ""                     # 选题
    content_type: str = "short_video"   # short_video / image_text
    production_mode: str = "human_shoot"  # human_shoot / ai_digital
    target_platform: str = "douyin"     # 目标平台

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ContentCalendarEntry":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class ContentInsight:
    """内容洞察总览 — 对标 Phase3-3_CONTENT_INTELLIGENCE_DESIGN.md §五。

    聚合多个视频分析结果，输出:
    - 热点选题排行
    - 需求缺口识别
    - 标题/钩子模式提炼
    - 推荐选题列表
    - 本周发布计划
    """

    insight_id: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).isoformat())
    source_period: str = "最近30天"
    source_video_count: int = 0

    # ── 热点选题 ──
    topics: list[TopicInsight] = field(default_factory=list)

    # ── 需求缺口 ──
    demand_gaps: list[DemandGap] = field(default_factory=list)

    # ── 标题模式 ──
    title_patterns: list[dict[str, str]] = field(default_factory=list)

    # ── 钩子公式 ──
    hook_formulas: list[dict[str, str]] = field(default_factory=list)

    # ── 推荐选题 (PV_OS 差异化) ──
    recommended_topics: list[str] = field(default_factory=list)

    # ── Phase 3-3 新增: 内容日历 ──
    content_calendar: list[ContentCalendarEntry] = field(default_factory=list)

    # ── Phase 3-3 新增: 策略总结 ──
    strategy_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "generated_at": self.generated_at,
            "source_period": self.source_period,
            "source_video_count": self.source_video_count,
            "topics": [t.to_dict() for t in self.topics],
            "demand_gaps": [g.to_dict() for g in self.demand_gaps],
            "title_patterns": self.title_patterns,
            "hook_formulas": self.hook_formulas,
            "recommended_topics": self.recommended_topics,
            "content_calendar": [c.to_dict() for c in self.content_calendar],
            "strategy_summary": self.strategy_summary,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContentInsight":
        topics = [TopicInsight.from_dict(t) for t in data.get("topics", [])]
        gaps = [DemandGap.from_dict(g) for g in data.get("demand_gaps", [])]
        calendar = [ContentCalendarEntry.from_dict(c)
                    for c in data.get("content_calendar", [])]
        return cls(
            insight_id=data.get("insight_id", ""),
            generated_at=data.get("generated_at", ""),
            source_period=data.get("source_period", "最近30天"),
            source_video_count=data.get("source_video_count", 0),
            topics=topics,
            demand_gaps=gaps,
            title_patterns=data.get("title_patterns", []),
            hook_formulas=data.get("hook_formulas", []),
            recommended_topics=data.get("recommended_topics", []),
            content_calendar=calendar,
            strategy_summary=data.get("strategy_summary", ""),
        )

    def save(self, path: Path | None = None) -> Path:
        """保存 ContentInsight 为 JSON 文件。"""
        if not self.insight_id:
            ts = datetime.now(TZ_SHANGHAI).strftime("%Y%m%d%H%M%S")
            self.insight_id = f"CI_{ts}"
        p = path or CONTENT_STRATEGY / f"content_insight_{self.insight_id}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("ContentInsight 保存 → %s", p)
        return p

    @staticmethod
    def load(path: Path) -> "ContentInsight":
        """从 JSON 文件加载。"""
        data = json.loads(path.read_text(encoding="utf-8"))
        return ContentInsight.from_dict(data)


# ══════════════════════════════════════════════════════════════════════
# ContentInsightStore — CSV 索引 + JSON 详情
# ══════════════════════════════════════════════════════════════════════

class ContentInsightStore:
    """内容洞察持久化存储。

    存储: 04_CONTENT/strategy/content_insight_index.csv
          04_CONTENT/strategy/content_insight_{id}.json
    """

    def __init__(self, csv_path: Path | None = None) -> None:
        self.csv_path = csv_path or INSIGHT_INDEX_CSV
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, insight: ContentInsight) -> None:
        """保存洞察 (CSV索引 + JSON详情)。"""
        if not insight.insight_id:
            ts = datetime.now(TZ_SHANGHAI).strftime("%Y%m%d%H%M%S")
            insight.insight_id = f"CI_{ts}"

        # JSON 详情
        json_path = CONTENT_STRATEGY / f"content_insight_{insight.insight_id}.json"
        json_path.write_text(
            json.dumps(insight.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # CSV 索引
        existing = self._read_csv()
        existing_dict: dict[str, list[str]] = {
            r[0]: r for r in existing[1:] if len(r) > 0
        }
        top_topic = insight.recommended_topics[0] if insight.recommended_topics else ""
        row = [
            insight.insight_id,
            insight.generated_at,
            insight.source_period,
            str(insight.source_video_count),
            str(len(insight.topics)),
            str(len(insight.demand_gaps)),
            top_topic,
        ]
        existing_dict[insight.insight_id] = row
        self._write_csv([INSIGHT_INDEX_FIELDS] + list(existing_dict.values()))
        logger.info("ContentInsightStore: 保存 %s", insight.insight_id)

    def get(self, insight_id: str) -> ContentInsight | None:
        """按 ID 获取洞察。"""
        json_path = CONTENT_STRATEGY / f"content_insight_{insight_id}.json"
        if not json_path.exists():
            return None
        return ContentInsight.load(json_path)

    def list_all(self) -> list[dict[str, str]]:
        """列出所有洞察索引。"""
        rows = self._read_csv()
        return [dict(zip(INSIGHT_INDEX_FIELDS, r))
                for r in rows[1:] if len(r) >= len(INSIGHT_INDEX_FIELDS)]

    def _read_csv(self) -> list[list[str]]:
        if not self.csv_path.exists():
            return [INSIGHT_INDEX_FIELDS]
        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.reader(f))

    def _write_csv(self, rows: list[list[str]]) -> None:
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)


# ══════════════════════════════════════════════════════════════════════
# Mock 分析规则
# ══════════════════════════════════════════════════════════════════════

# 话题关键词映射
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "别墅光伏安装": ["别墅", "安装", "实拍"],
    "阳光房光伏改造": ["阳光房", "改造", "遮阳"],
    "家庭光伏省钱": ["省钱", "电费", "省电", "回本"],
    "工商业光伏": ["工厂", "企业", "工商业", "厂房"],
    "光伏储能一体": ["储能", "电池", "储电"],
    "光伏避坑指南": ["避坑", "踩坑", "后悔", "注意"],
    "老旧小区光伏": ["老旧", "小区", "改造", "旧房"],
}

# 话题元数据（含互动基准值）
TOPIC_META: dict[str, dict[str, Any]] = {
    "别墅光伏安装": {
        "trend": "rising", "competitive_intensity": "high",
        "avg_engagement_base": 120, "demand_base": 15,
    },
    "阳光房光伏改造": {
        "trend": "rising", "competitive_intensity": "low",
        "avg_engagement_base": 85, "demand_base": 12,
    },
    "家庭光伏省钱": {
        "trend": "stable", "competitive_intensity": "high",
        "avg_engagement_base": 200, "demand_base": 20,
    },
    "工商业光伏": {
        "trend": "stable", "competitive_intensity": "medium",
        "avg_engagement_base": 60, "demand_base": 8,
    },
    "光伏储能一体": {
        "trend": "rising", "competitive_intensity": "low",
        "avg_engagement_base": 45, "demand_base": 10,
    },
    "光伏避坑指南": {
        "trend": "stable", "competitive_intensity": "medium",
        "avg_engagement_base": 90, "demand_base": 14,
    },
    "老旧小区光伏": {
        "trend": "declining", "competitive_intensity": "low",
        "avg_engagement_base": 35, "demand_base": 5,
    },
}

# 需求缺口模板
MOCK_GAP_TEMPLATES: list[dict[str, Any]] = [
    {
        "gap_topic": "叠拼/联排别墅光伏",
        "demand_signals_multiplier": 3,
        "content_count_multiplier": 0.3,
        "suggested_angle": "叠拼屋顶复杂结构的光伏安装方案",
        "target_audience": "叠拼/联排业主",
    },
    {
        "gap_topic": "光伏+阳光房一体化",
        "demand_signals_multiplier": 4,
        "content_count_multiplier": 0.2,
        "suggested_angle": "遮阳发电二合一：阳光房改造最佳实践",
        "target_audience": "阳光房业主",
    },
    {
        "gap_topic": "老旧小区屋顶光伏审批",
        "demand_signals_multiplier": 2,
        "content_count_multiplier": 0.1,
        "suggested_angle": "老旧小区光伏安装：物业审批全流程",
        "target_audience": "老旧小区业主",
    },
    {
        "gap_topic": "光伏+储能真实回本周期",
        "demand_signals_multiplier": 3,
        "content_count_multiplier": 0.25,
        "suggested_angle": "川渝地区光伏+储能真实回本计算",
        "target_audience": "家庭用户",
    },
]

# 每周发布模板
MOCK_CALENDAR_TEMPLATE: list[dict[str, str]] = [
    {"day": "周一", "topic": "光伏知识科普", "content_type": "short_video", "production_mode": "ai_digital"},
    {"day": "周二", "topic": "本地安装案例", "content_type": "short_video", "production_mode": "human_shoot"},
    {"day": "周三", "topic": "避坑指南/答疑", "content_type": "image_text", "production_mode": "human_shoot"},
    {"day": "周四", "topic": "光伏省钱实测", "content_type": "short_video", "production_mode": "human_shoot"},
    {"day": "周五", "topic": "行业政策解读", "content_type": "short_video", "production_mode": "ai_digital"},
    {"day": "周六", "topic": "客户见证/口碑", "content_type": "short_video", "production_mode": "human_shoot"},
    {"day": "周日", "topic": "本周精选回顾", "content_type": "image_text", "production_mode": "ai_digital"},
]


# ══════════════════════════════════════════════════════════════════════
# ContentInsightAgent
# ══════════════════════════════════════════════════════════════════════

class ContentInsightAgent:
    """内容洞察聚合引擎。

    功能:
    - 从 VideoAnalysisResult 列表生成内容洞察
    - 识别热点选题和需求缺口
    - 生成每周发布计划
    - 输出策略建议

    mode="mock": 使用启发式规则 + 关键词匹配
    """

    MIN_VIDEOS_FOR_INSIGHT = 5  # 最少需要 5 条分析视频

    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode
        logger.info("ContentInsightAgent 初始化: mode=%s", mode)

    def generate_insight(
        self,
        analysis_results: list[VideoAnalysisResult],
        video_assets: list[Any] | None = None,
    ) -> ContentInsight:
        """从分析结果生成内容洞察。

        Args:
            analysis_results: VideoAnalysisResult 列表
            video_assets: 原始 VideoAsset 列表 (可选，用于补充互动数据)

        Returns:
            ContentInsight 实例
        """
        if len(analysis_results) < self.MIN_VIDEOS_FOR_INSIGHT:
            logger.warning(
                "分析视频不足: %d < %d, 返回基础洞察",
                len(analysis_results), self.MIN_VIDEOS_FOR_INSIGHT,
            )

        if self.mode == "mock":
            return self._mock_generate(analysis_results, video_assets)

        # 保留真实 AI 接口位置
        raise NotImplementedError("仅支持 mock 模式")

    def _mock_generate(
        self,
        results: list[VideoAnalysisResult],
        assets: list[Any] | None = None,
    ) -> ContentInsight:
        """Mock 模式: 使用关键词匹配 + 启发式规则生成洞察。"""
        insight = ContentInsight(
            source_video_count=len(results),
        )

        # ── 1. 热点选题分析 ──
        topic_stats: dict[str, dict[str, Any]] = {}
        for r in results:
            assigned = False
            for topic, keywords in TOPIC_KEYWORDS.items():
                if any(k in r.video_title for k in keywords):
                    if topic not in topic_stats:
                        topic_stats[topic] = {
                            "count": 0, "viral_sum": 0, "engagement_sum": 0,
                        }
                    topic_stats[topic]["count"] += 1
                    topic_stats[topic]["viral_sum"] += r.viral_score
                    topic_stats[topic]["engagement_sum"] += r.reusability_score * 2
                    assigned = True
                    break
            if not assigned:
                if "其他" not in topic_stats:
                    topic_stats["其他"] = {"count": 0, "viral_sum": 0, "engagement_sum": 0}
                topic_stats["其他"]["count"] += 1
                topic_stats["其他"]["viral_sum"] += r.viral_score
                topic_stats["其他"]["engagement_sum"] += r.reusability_score * 2

        for topic, stats in topic_stats.items():
            meta = TOPIC_META.get(topic, {})
            n = stats["count"]
            insight.topics.append(TopicInsight(
                topic=topic,
                video_count=n,
                avg_viral_score=stats["viral_sum"] // max(n, 1),
                avg_engagement=stats["engagement_sum"] // max(n, 1),
                trend=meta.get("trend", "stable"),
                demand_signals=meta.get("demand_base", 5) * n,
                competitive_intensity=meta.get("competitive_intensity", "medium"),
            ))

        # 按视频数排序
        insight.topics.sort(key=lambda t: t.video_count, reverse=True)

        # ── 2. 需求缺口识别 ──
        total_videos = max(len(results), 1)
        for template in MOCK_GAP_TEMPLATES:
            # 检查该缺口是否已被覆盖
            covered = sum(
                1 for r in results
                if any(k in r.video_title for k in [template["gap_topic"][:2]])
            )
            ds = total_videos * template["demand_signals_multiplier"]
            cc = max(int(total_videos * template["content_count_multiplier"]), 0)
            insight.demand_gaps.append(DemandGap(
                gap_topic=template["gap_topic"],
                demand_signals=int(ds),
                content_count=cc,
                opportunity_score=min(int(ds * 5 / max(cc, 1)), 100),
                suggested_angle=template["suggested_angle"],
                target_audience=template["target_audience"],
            ))

        insight.demand_gaps.sort(key=lambda g: g.opportunity_score, reverse=True)

        # ── 3. 标题模式提炼 ──
        title_counts: dict[str, int] = {}
        for r in results:
            if r.title_pattern:
                title_counts[r.title_pattern] = title_counts.get(r.title_pattern, 0) + 1

        for pattern, count in sorted(title_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            insight.title_patterns.append({
                "pattern": pattern,
                "count": str(count),
                "effectiveness": "high" if count >= 2 else "medium",
            })

        # 补充默认模式
        defaults = [
            {"pattern": "数字对比型", "example": "电费从3000降到300", "effectiveness": "high"},
            {"pattern": "场景痛点型", "example": "阳光房太晒怎么办", "effectiveness": "high"},
            {"pattern": "过程实录型", "example": "XX小区光伏安装全记录", "effectiveness": "high"},
        ]
        for d in defaults:
            if not any(p.get("pattern") == d["pattern"] for p in insight.title_patterns):
                insight.title_patterns.append(d)

        # ── 4. 钩子公式萃取 ──
        hook_keywords: dict[str, int] = {}
        for r in results:
            if r.conflict_pattern:
                hook_keywords.setdefault("冲突对比型", 0)
                hook_keywords["冲突对比型"] += 1
            if r.user_resonance:
                hook_keywords.setdefault("身份共鸣型", 0)
                hook_keywords["身份共鸣型"] += 1

        formulas = [
            {"formula": "数字对比型", "example": "电费从3000降到300",
             "usage": str(hook_keywords.get("冲突对比型", results.count))},
            {"formula": "场景痛点型", "example": "阳光房太晒怎么办？",
             "usage": str(max(len(results) // 2, 1))},
            {"formula": "身份共鸣型", "example": "别墅业主最关心的3个问题",
             "usage": str(hook_keywords.get("身份共鸣型", 0) or len(results) // 2)},
            {"formula": "过程展示型", "example": "光伏安装全过程，3分钟看懂",
             "usage": str(max(len(results) // 3, 1))},
        ]
        insight.hook_formulas = formulas

        # ── 5. 推荐选题 ──
        recommendations = [
            "成都别墅业主：光伏一年真实电费对比",
            "重庆阳光房改造：遮阳+发电一石二鸟",
            "贵阳小商业光伏：棋牌室/茶楼月省电费实测",
            "成都老旧小区屋顶光伏安装全记录",
            "叠拼业主光伏避坑指南（川渝黔版）",
        ]

        # 从缺口生成推荐
        for gap in insight.demand_gaps[:3]:
            if gap.opportunity_score >= 30:
                rec = f"{gap.gap_topic}: {gap.suggested_angle[:30]}"
                if rec not in recommendations:
                    recommendations.insert(0, rec)

        insight.recommended_topics = recommendations[:7]

        # ── 6. 内容日历 ──
        for tpl in MOCK_CALENDAR_TEMPLATE:
            insight.content_calendar.append(ContentCalendarEntry(
                day=tpl["day"],
                topic=tpl["topic"],
                content_type=tpl["content_type"],
                production_mode=tpl["production_mode"],
                target_platform="douyin",
            ))

        # ── 7. 策略总结 ──
        top_topic = insight.topics[0].topic if insight.topics else "内容创作"
        top_gap = insight.demand_gaps[0].gap_topic if insight.demand_gaps else "差异化选题"
        insight.strategy_summary = (
            f"基于 {len(results)} 条视频分析，当前 {top_topic} 话题内容供给充足但竞争激烈。"
            f"建议重点切入 {top_gap} 方向，该领域需求信号强但内容供给不足，"
            f"是 PV_OS 差异化优势所在。"
            f"本周推荐采用「本地案例 + 数据对比」的组合策略，持续建立区域信任。"
        )

        return insight


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile, shutil

    print("=" * 60)
    print("  ContentInsightAgent V1.0 — 自检 (Phase 3-3)")
    print("=" * 60)

    # 准备测试数据: 6 条分析结果
    mock_results = [
        VideoAnalysisResult(
            analysis_id="VA_001", video_id="dy_v001",
            video_title="别墅光伏安装实拍",
            hook_3_seconds="电费从3000降到300",
            pain_point="别墅电费高",
            customer_type="别墅业主",
            video_structure="痛点→方案→数据→CTA",
            title_pattern="数字对比型",
            conflict_pattern="电费高vs光伏省钱",
            cta_analysis="评论区引导报价",
            user_resonance="别墅业主身份认同",
            viral_score=85, reusability_score=90,
        ),
        VideoAnalysisResult(
            analysis_id="VA_002", video_id="dy_v002",
            video_title="阳光房光伏改造案例",
            hook_3_seconds="阳光房太晒怎么办",
            pain_point="阳光房夏天太热",
            customer_type="别墅业主",
            video_structure="痛点→方案→展示→CTA",
            title_pattern="场景痛点型",
            conflict_pattern="太热vs太贵",
            cta_analysis="私信获取方案",
            user_resonance="家有阳光房的共鸣",
            viral_score=78, reusability_score=80,
        ),
        VideoAnalysisResult(
            analysis_id="VA_003", video_id="dy_v003",
            video_title="家庭光伏一年省了多少钱",
            hook_3_seconds="去年装了光伏，现在告诉你真实电费",
            pain_point="不知道光伏能省多少",
            customer_type="普通家庭",
            video_structure="回顾→数据→对比→CTA",
            title_pattern="数字对比型",
            conflict_pattern="投入vs回报",
            cta_analysis="评论区晒账单",
            user_resonance="家庭省钱预期",
            viral_score=92, reusability_score=88,
        ),
        VideoAnalysisResult(
            analysis_id="VA_004", video_id="dy_v004",
            video_title="工厂屋顶光伏真实案例",
            hook_3_seconds="工厂老板必看：屋顶闲着也是闲着",
            pain_point="工商业电费压力",
            customer_type="小商业",
            video_structure="痛点→方案→回收周期→CTA",
            title_pattern="场景痛点型",
            conflict_pattern="闲置屋顶vs电费支出",
            cta_analysis="私信获取方案",
            user_resonance="老板的省钱冲动",
            viral_score=70, reusability_score=65,
        ),
        VideoAnalysisResult(
            analysis_id="VA_005", video_id="dy_v005",
            video_title="光伏储能一体：再也不用交电费",
            hook_3_seconds="光伏+储能，彻底告别电网",
            pain_point="电费持续上涨",
            customer_type="别墅业主",
            video_structure="概念→原理→案例→CTA",
            title_pattern="好奇牵引型",
            conflict_pattern="电网依赖vs独立供电",
            cta_analysis="评论区讨论",
            user_resonance="能源自由渴望",
            viral_score=88, reusability_score=75,
        ),
        VideoAnalysisResult(
            analysis_id="VA_006", video_id="dy_v006",
            video_title="光伏避坑：这3种屋顶千万别装",
            hook_3_seconds="装了光伏后悔的，都是踩了这3个坑",
            pain_point="担心装错后悔",
            customer_type="普通家庭",
            video_structure="警告→拆解→方案→CTA",
            title_pattern="反常识警告型",
            conflict_pattern="想装vs怕踩坑",
            cta_analysis="评论区提问",
            user_resonance="避免损失的本能",
            viral_score=95, reusability_score=92,
        ),
    ]

    # ── ContentInsight 模型测试 ──
    print("\n[1] ContentInsight 模型")
    ci = ContentInsight(
        insight_id="CI_test",
        source_video_count=6,
        topics=[TopicInsight(topic="别墅光伏", video_count=3, trend="rising")],
        demand_gaps=[DemandGap(gap_topic="叠拼光伏", opportunity_score=75)],
        strategy_summary="测试策略总结",
    )
    d = ci.to_dict()
    assert d["insight_id"] == "CI_test"
    assert d["topics"][0]["topic"] == "别墅光伏"
    assert d["demand_gaps"][0]["opportunity_score"] == 75
    print("  ✓ to_dict 正常")

    ci2 = ContentInsight.from_dict(d)
    assert ci2.insight_id == "CI_test"
    assert ci2.topics[0].topic == "别墅光伏"
    assert ci2.strategy_summary == "测试策略总结"
    print("  ✓ from_dict 正常")

    # JSON 保存/加载
    tmp_dir = Path(tempfile.mkdtemp())
    json_path = tmp_dir / "test_insight.json"
    ci.save(json_path)
    assert json_path.exists()
    ci3 = ContentInsight.load(json_path)
    assert ci3.insight_id == "CI_test"
    assert ci3.topics[0].trend == "rising"
    print("  ✓ JSON 保存/加载 正常")

    # ── ContentInsightAgent Mock 测试 ──
    print("\n[2] ContentInsightAgent (Mock)")
    agent = ContentInsightAgent(mode="mock")

    insight = agent.generate_insight(mock_results)
    assert insight.source_video_count == 6
    assert len(insight.topics) >= 2
    assert len(insight.demand_gaps) == 4
    assert len(insight.recommended_topics) >= 5
    assert len(insight.content_calendar) == 7
    assert len(insight.strategy_summary) > 20
    print(f"  来源视频: {insight.source_video_count}")
    print(f"  选题数: {len(insight.topics)}")
    print(f"  缺口数: {len(insight.demand_gaps)}")
    print(f"  推荐选题: {len(insight.recommended_topics)}")
    print(f"  日历条目: {len(insight.content_calendar)}")
    print(f"  策略总结: {insight.strategy_summary[:50]}...")

    # ── 需求缺口验证 ──
    print("\n[3] 需求缺口")
    for g in insight.demand_gaps:
        assert g.opportunity_score >= 0
        assert g.suggested_angle != ""
        assert g.target_audience != ""
        print(f"  - {g.gap_topic} (机会:{g.opportunity_score})")
        print(f"    需求信号:{g.demand_signals} 内容数:{g.content_count}")
        print(f"    角度:{g.suggested_angle[:40]}...")

    # ── 内容日历验证 ──
    print("\n[4] 内容日历")
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for e in insight.content_calendar:
        assert e.day in weekdays
        assert e.content_type in ("short_video", "image_text")
        assert e.production_mode in ("human_shoot", "ai_digital")
    print(f"  ✓ 7天日历完整")
    print(f"  生产模式: human_shoot={sum(1 for c in insight.content_calendar if c.production_mode=='human_shoot')}, "
          f"ai_digital={sum(1 for c in insight.content_calendar if c.production_mode=='ai_digital')}")

    # ── ContentInsightStore 测试 ──
    print("\n[5] ContentInsightStore")
    store_csv = tmp_dir / "insight_index.csv"
    store = ContentInsightStore(csv_path=store_csv)
    store.save(insight)
    assert store_csv.exists()
    loaded = store.get(insight.insight_id)
    assert loaded is not None
    assert loaded.source_video_count == 6
    print(f"  ✓ Store 保存/读取: {insight.insight_id}")

    # 索引列表
    index_list = store.list_all()
    assert len(index_list) >= 1
    assert index_list[0]["topic_count"] == str(len(insight.topics))
    print(f"  ✓ 索引列表: {len(index_list)} 条")

    # ── 边界条件: 少于 5 条视频 ──
    print("\n[6] 边界条件: < 5 条视频")
    small_insight = agent.generate_insight(mock_results[:3])
    assert small_insight.source_video_count == 3
    assert len(small_insight.topics) >= 1
    print(f"  ✓ 3条视频生成洞察: {len(small_insight.topics)} 选题")

    # ── 空列表 ──
    print("\n[7] 边界条件: 空列表")
    empty_insight = agent.generate_insight([])
    assert empty_insight.source_video_count == 0
    assert empty_insight.strategy_summary != ""  # 应有默认推荐
    print(f"  ✓ 空列表返回基础洞察")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print("\n✓ ContentInsightAgent V1.0 自检完成\n")
