"""Phase 3-3 Content Intelligence 测试 (V1.0)。

覆盖: VideoAnalysisResult V2.0 / ContentInsightAgent / ScriptLibrary V2.0 /
       Phase 3-3 新增字段: conflict_pattern, cta_analysis, user_resonance, production_mode /
       数据流: VideoAnalysis → ContentInsight → Script。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_phase3_3_content.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from video_analysis_model import (  # noqa: E402
    VideoAnalysisResult, VideoAnalysisStore, ReusableElements,
)
from content_insight_agent import (  # noqa: E402
    ContentInsightAgent, ContentInsight, ContentInsightStore,
    TopicInsight, DemandGap, ContentCalendarEntry,
)
from script_library_model import (  # noqa: E402
    ScriptEntry, ScriptLibrary, ScriptScene,
)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_analysis() -> VideoAnalysisResult:
    """单条视频分析结果样本。"""
    return VideoAnalysisResult(
        video_id="dy_v001",
        video_title="别墅光伏安装实拍",
        hook_3_seconds="数字对比：电费从3000降到300",
        pain_point="城市别墅业主电费高但不知道光伏能省多少",
        customer_type="别墅业主",
        video_structure="痛点开场 → 方案展示 → 数据对比 → 客户见证 → 引导咨询",
        title_pattern="数字对比型：我家XX平米装了光伏，一年省了X万",
        comment_trigger="评论里很多人问'我家能装吗'",
        viral_reason="强数字对比 + 真实案例 + 本地信任感",
        turning_point="第15秒展示电费账单对比",
        closing_factor="本地案例 + 可上门测量",
        conflict_pattern="电费高vs光伏省钱——制造认知冲突",
        cta_analysis="评论区引导：让用户主动报面积，降低决策门槛",
        user_resonance="别墅业主身份认同+省钱预期+本地可上门",
        viral_score=85,
        reusability_score=90,
        reusable=ReusableElements(
            hook_template="【数字】从【旧状态】变成【新状态】",
            structure_template="痛点→方案→数据→见证→CTA",
            key_phrases=["我家XX平米", "一年省了X万"],
            angle_suggestions=["成都本地化", "算日照账"],
        ),
    )


@pytest.fixture
def sample_analysis_list() -> list[VideoAnalysisResult]:
    """多条视频分析结果样本 (≥5条，满足 ContentInsight 最低要求)。"""
    return [
        VideoAnalysisResult(
            analysis_id="VA_001", video_id="dy_v001",
            video_title="别墅光伏安装实拍",
            hook_3_seconds="电费从3000降到300",
            pain_point="别墅电费高", customer_type="别墅业主",
            video_structure="痛点→方案→数据→CTA",
            title_pattern="数字对比型",
            conflict_pattern="电费高vs光伏省钱",
            cta_analysis="评论区引导报价", user_resonance="别墅业主身份认同",
            viral_score=85, reusability_score=90,
        ),
        VideoAnalysisResult(
            analysis_id="VA_002", video_id="dy_v002",
            video_title="阳光房光伏改造案例",
            hook_3_seconds="阳光房太晒怎么办",
            pain_point="阳光房夏天太热", customer_type="别墅业主",
            video_structure="痛点→方案→展示→CTA",
            title_pattern="场景痛点型",
            conflict_pattern="太热vs太贵",
            cta_analysis="私信获取方案", user_resonance="家有阳光房的共鸣",
            viral_score=78, reusability_score=80,
        ),
        VideoAnalysisResult(
            analysis_id="VA_003", video_id="dy_v003",
            video_title="家庭光伏一年省了多少钱",
            hook_3_seconds="去年装了光伏，现在告诉你真实电费",
            pain_point="不知道光伏能省多少", customer_type="普通家庭",
            video_structure="回顾→数据→对比→CTA",
            title_pattern="数字对比型",
            conflict_pattern="投入vs回报",
            cta_analysis="评论区晒账单", user_resonance="家庭省钱预期",
            viral_score=92, reusability_score=88,
        ),
        VideoAnalysisResult(
            analysis_id="VA_004", video_id="dy_v004",
            video_title="工厂屋顶光伏真实案例",
            hook_3_seconds="工厂老板必看：屋顶闲着也是闲着",
            pain_point="工商业电费压力", customer_type="小商业",
            video_structure="痛点→方案→回收周期→CTA",
            title_pattern="场景痛点型",
            conflict_pattern="闲置屋顶vs电费支出",
            cta_analysis="私信获取方案", user_resonance="老板的省钱冲动",
            viral_score=70, reusability_score=65,
        ),
        VideoAnalysisResult(
            analysis_id="VA_005", video_id="dy_v005",
            video_title="光伏储能一体：再也不用交电费",
            hook_3_seconds="光伏+储能，彻底告别电网",
            pain_point="电费持续上涨", customer_type="别墅业主",
            video_structure="概念→原理→案例→CTA",
            title_pattern="好奇牵引型",
            conflict_pattern="电网依赖vs独立供电",
            cta_analysis="评论区讨论", user_resonance="能源自由渴望",
            viral_score=88, reusability_score=75,
        ),
        VideoAnalysisResult(
            analysis_id="VA_006", video_id="dy_v006",
            video_title="光伏避坑：这3种屋顶千万别装",
            hook_3_seconds="装了光伏后悔的，都是踩了这3个坑",
            pain_point="担心装错后悔", customer_type="普通家庭",
            video_structure="警告→拆解→方案→CTA",
            title_pattern="反常识警告型",
            conflict_pattern="想装vs怕踩坑",
            cta_analysis="评论区提问", user_resonance="避免损失的本能",
            viral_score=95, reusability_score=92,
        ),
    ]


@pytest.fixture
def insight_agent() -> ContentInsightAgent:
    return ContentInsightAgent(mode="mock")


@pytest.fixture
def tmp_store() -> VideoAnalysisStore:
    """使用临时目录的 VideoAnalysisStore。"""
    tmp = Path(tempfile.mkdtemp()) / "test_analysis.csv"
    return VideoAnalysisStore(csv_path=tmp)


# ══════════════════════════════════════════════════════════════════════
# 1. ReusableElements
# ══════════════════════════════════════════════════════════════════════

class TestReusableElements:

    def test_defaults(self) -> None:
        re = ReusableElements()
        assert re.hook_template == ""
        assert re.key_phrases == []
        assert re.angle_suggestions == []

    def test_serialization(self) -> None:
        re = ReusableElements(
            hook_template="【数字】从A到B",
            structure_template="痛点→方案→数据→CTA",
            key_phrases=["省电", "回本"],
            angle_suggestions=["成都本地化"],
        )
        d = re.to_dict()
        assert d["hook_template"] == "【数字】从A到B"
        assert d["key_phrases"] == ["省电", "回本"]

    def test_from_dict_empty(self) -> None:
        re = ReusableElements.from_dict({})
        assert re.hook_template == ""
        assert re.key_phrases == []


# ══════════════════════════════════════════════════════════════════════
# 2. VideoAnalysisResult V2.0
# ══════════════════════════════════════════════════════════════════════

class TestVideoAnalysisResult:

    def test_basic_fields(self, sample_analysis: VideoAnalysisResult) -> None:
        assert sample_analysis.video_id == "dy_v001"
        assert sample_analysis.video_title == "别墅光伏安装实拍"
        assert sample_analysis.viral_score == 85
        assert sample_analysis.reusability_score == 90

    def test_phase3_fields(self, sample_analysis: VideoAnalysisResult) -> None:
        """Phase 3-3 新增字段。"""
        assert sample_analysis.conflict_pattern.startswith("电费高vs光伏省钱")
        assert sample_analysis.cta_analysis.startswith("评论区引导")
        assert sample_analysis.user_resonance.startswith("别墅业主身份认同")

    def test_phase3_fields_default(self) -> None:
        """Phase 3-3 字段默认为空字符串。"""
        r = VideoAnalysisResult(video_id="test")
        assert r.conflict_pattern == ""
        assert r.cta_analysis == ""
        assert r.user_resonance == ""

    def test_to_dict_includes_phase3(self, sample_analysis: VideoAnalysisResult) -> None:
        d = sample_analysis.to_dict()
        assert "conflict_pattern" in d
        assert "cta_analysis" in d
        assert "user_resonance" in d
        assert d["conflict_pattern"].startswith("电费高vs光伏省钱")

    def test_from_dict_phase3(self) -> None:
        d = {
            "video_id": "test", "video_title": "测试",
            "conflict_pattern": "冲突测试", "cta_analysis": "CTA测试",
            "user_resonance": "共鸣测试", "viral_score": 50,
            "reusability_score": 40, "reusable": {},
        }
        r = VideoAnalysisResult.from_dict(d)
        assert r.conflict_pattern == "冲突测试"
        assert r.cta_analysis == "CTA测试"
        assert r.user_resonance == "共鸣测试"

    def test_backward_compat_no_phase3(self) -> None:
        """兼容旧版数据 (无 Phase 3-3 字段)。"""
        old_data = {
            "analysis_id": "VA_old", "video_id": "dy_old",
            "video_title": "旧版视频", "hook_3_seconds": "旧钩子",
            "pain_point": "旧痛点", "customer_type": "别墅业主",
            "video_structure": "旧结构", "title_pattern": "旧标题",
            "comment_trigger": "旧触发", "viral_reason": "旧原因",
            "turning_point": "旧转折", "closing_factor": "旧成交",
            "viral_score": 50, "reusability_score": 40,
            "analyzed_at": "2026-07-20T00:00:00", "source_video_id": "",
            "reusable": {"hook_template": "", "key_phrases": [], "angle_suggestions": []},
        }
        r = VideoAnalysisResult.from_dict(old_data)
        assert r.video_title == "旧版视频"
        assert r.conflict_pattern == ""
        assert r.cta_analysis == ""
        assert r.user_resonance == ""

    def test_to_csv_row(self, sample_analysis: VideoAnalysisResult) -> None:
        row = sample_analysis.to_csv_row()
        assert len(row) >= 19  # 原始 16 + Phase 3-3 3个字段
        # 最后3个应是 Phase 3-3 字段
        assert row[-3].startswith("电费高vs光伏省钱")
        assert row[-2].startswith("评论区引导")
        assert row[-1].startswith("别墅业主身份认同")

    def test_csv_roundtrip(self, sample_analysis: VideoAnalysisResult) -> None:
        row = sample_analysis.to_csv_row()
        r2 = VideoAnalysisResult.from_csv_row(row)
        assert r2.video_title == sample_analysis.video_title
        assert r2.viral_score == sample_analysis.viral_score
        assert r2.conflict_pattern == sample_analysis.conflict_pattern
        assert r2.cta_analysis == sample_analysis.cta_analysis
        assert r2.user_resonance == sample_analysis.user_resonance

    def test_reusable_elements(self, sample_analysis: VideoAnalysisResult) -> None:
        re = sample_analysis.reusable
        assert re.hook_template.startswith("【数字】")
        assert "我家XX平米" in re.key_phrases
        assert "成都本地化" in re.angle_suggestions


# ══════════════════════════════════════════════════════════════════════
# 3. VideoAnalysisStore
# ══════════════════════════════════════════════════════════════════════

class TestVideoAnalysisStore:

    def test_save_and_get(self, tmp_store: VideoAnalysisStore,
                          sample_analysis: VideoAnalysisResult) -> None:
        tmp_store.save(sample_analysis)
        loaded = tmp_store.get(sample_analysis.analysis_id)
        assert loaded is not None
        assert loaded.video_title == "别墅光伏安装实拍"
        assert loaded.viral_score == 85

    def test_save_preserves_phase3_fields(self, tmp_store: VideoAnalysisStore,
                                          sample_analysis: VideoAnalysisResult) -> None:
        tmp_store.save(sample_analysis)
        loaded = tmp_store.get(sample_analysis.analysis_id)
        assert loaded is not None
        assert loaded.conflict_pattern == sample_analysis.conflict_pattern
        assert loaded.cta_analysis == sample_analysis.cta_analysis
        assert loaded.user_resonance == sample_analysis.user_resonance

    def test_auto_generates_id(self, tmp_store: VideoAnalysisStore) -> None:
        r = VideoAnalysisResult(video_id="dy_auto", video_title="自动ID")
        tmp_store.save(r)
        assert r.analysis_id.startswith("VA_")

    def test_list_all(self, tmp_store: VideoAnalysisStore,
                      sample_analysis_list: list[VideoAnalysisResult]) -> None:
        for r in sample_analysis_list:
            tmp_store.save(r)
        all_results = tmp_store.list_all()
        assert len(all_results) == 6

    def test_list_by_video(self, tmp_store: VideoAnalysisStore,
                           sample_analysis_list: list[VideoAnalysisResult]) -> None:
        for r in sample_analysis_list:
            tmp_store.save(r)
        results = tmp_store.list_by_video("dy_v001")
        assert len(results) == 1
        assert results[0].video_title == "别墅光伏安装实拍"

    def test_get_top_viral(self, tmp_store: VideoAnalysisStore,
                           sample_analysis_list: list[VideoAnalysisResult]) -> None:
        for r in sample_analysis_list:
            tmp_store.save(r)
        top = tmp_store.get_top_viral(3)
        assert len(top) == 3
        assert top[0].viral_score >= top[1].viral_score >= top[2].viral_score

    def test_get_nonexistent(self, tmp_store: VideoAnalysisStore) -> None:
        assert tmp_store.get("VA_nonexistent") is None

    def test_empty_store(self, tmp_store: VideoAnalysisStore) -> None:
        assert tmp_store.list_all() == []


# ══════════════════════════════════════════════════════════════════════
# 4. TopicInsight / DemandGap / ContentCalendarEntry
# ══════════════════════════════════════════════════════════════════════

class TestTopicInsight:

    def test_defaults(self) -> None:
        t = TopicInsight()
        assert t.topic == ""
        assert t.trend == "stable"
        assert t.competitive_intensity == "medium"

    def test_serialization(self) -> None:
        t = TopicInsight(topic="别墅光伏", video_count=3, trend="rising",
                         competitive_intensity="high", demand_signals=15)
        d = t.to_dict()
        assert d["topic"] == "别墅光伏"
        assert d["trend"] == "rising"

        t2 = TopicInsight.from_dict(d)
        assert t2.topic == "别墅光伏"
        assert t2.video_count == 3


class TestDemandGap:

    def test_defaults(self) -> None:
        g = DemandGap()
        assert g.gap_topic == ""
        assert g.opportunity_score == 0

    def test_serialization(self) -> None:
        g = DemandGap(gap_topic="叠拼光伏", opportunity_score=75,
                      suggested_angle="叠拼屋顶优化方案", target_audience="叠拼业主")
        d = g.to_dict()
        assert d["opportunity_score"] == 75

        g2 = DemandGap.from_dict(d)
        assert g2.gap_topic == "叠拼光伏"
        assert g2.opportunity_score == 75


class TestContentCalendarEntry:

    def test_defaults(self) -> None:
        c = ContentCalendarEntry()
        assert c.day == ""
        assert c.content_type == "short_video"
        assert c.production_mode == "human_shoot"

    def test_fields(self) -> None:
        c = ContentCalendarEntry(
            day="周一", topic="光伏科普", content_type="short_video",
            production_mode="ai_digital", target_platform="douyin",
        )
        d = c.to_dict()
        assert d["production_mode"] == "ai_digital"

        c2 = ContentCalendarEntry.from_dict(d)
        assert c2.day == "周一"
        assert c2.production_mode == "ai_digital"


# ══════════════════════════════════════════════════════════════════════
# 5. ContentInsight
# ══════════════════════════════════════════════════════════════════════

class TestContentInsight:

    def test_defaults(self) -> None:
        ci = ContentInsight()
        assert ci.source_video_count == 0
        assert ci.topics == []
        assert ci.demand_gaps == []
        assert ci.content_calendar == []
        assert ci.strategy_summary == ""

    def test_with_data(self) -> None:
        ci = ContentInsight(
            insight_id="CI_test",
            source_video_count=5,
            topics=[TopicInsight(topic="别墅光伏", video_count=3)],
            demand_gaps=[DemandGap(gap_topic="叠拼光伏", opportunity_score=75)],
            strategy_summary="测试总结",
        )
        d = ci.to_dict()
        assert d["insight_id"] == "CI_test"
        assert d["source_video_count"] == 5

        ci2 = ContentInsight.from_dict(d)
        assert ci2.insight_id == "CI_test"
        assert ci2.topics[0].topic == "别墅光伏"
        assert ci2.strategy_summary == "测试总结"

    def test_save_load_json(self) -> None:
        ci = ContentInsight(
            insight_id="CI_json_test",
            source_video_count=3,
            strategy_summary="JSON测试",
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "insight.json"
            ci.save(p)
            assert p.exists()

            ci2 = ContentInsight.load(p)
            assert ci2.insight_id == "CI_json_test"
            assert ci2.strategy_summary == "JSON测试"

    def test_auto_generates_id(self) -> None:
        ci = ContentInsight()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "auto_id.json"
            saved = ci.save(p)
            assert ci.insight_id.startswith("CI_")


# ══════════════════════════════════════════════════════════════════════
# 6. ContentInsightAgent (Mock)
# ══════════════════════════════════════════════════════════════════════

class TestContentInsightAgent:

    def test_agent_init(self) -> None:
        agent = ContentInsightAgent(mode="mock")
        assert agent.mode == "mock"

    def test_generate_insight_basic(self, insight_agent: ContentInsightAgent,
                                    sample_analysis_list: list[VideoAnalysisResult]) -> None:
        insight = insight_agent.generate_insight(sample_analysis_list)
        assert insight.source_video_count == 6
        assert len(insight.topics) >= 2
        assert len(insight.demand_gaps) == 4
        assert len(insight.recommended_topics) >= 5
        assert len(insight.content_calendar) == 7
        assert len(insight.strategy_summary) > 20

    def test_topics_have_valid_data(self, insight_agent: ContentInsightAgent,
                                    sample_analysis_list: list[VideoAnalysisResult]) -> None:
        insight = insight_agent.generate_insight(sample_analysis_list)
        for topic in insight.topics:
            assert topic.topic != ""
            assert topic.video_count > 0
            assert topic.trend in ("rising", "stable", "declining")
            assert topic.competitive_intensity in ("high", "medium", "low")

    def test_demand_gaps_have_valid_data(self, insight_agent: ContentInsightAgent,
                                         sample_analysis_list: list[VideoAnalysisResult]) -> None:
        insight = insight_agent.generate_insight(sample_analysis_list)
        for gap in insight.demand_gaps:
            assert gap.gap_topic != ""
            assert 0 <= gap.opportunity_score <= 100
            assert gap.suggested_angle != ""
            assert gap.target_audience != ""

    def test_demand_gaps_sorted_by_opportunity(self, insight_agent: ContentInsightAgent,
                                               sample_analysis_list: list[VideoAnalysisResult]) -> None:
        insight = insight_agent.generate_insight(sample_analysis_list)
        scores = [g.opportunity_score for g in insight.demand_gaps]
        assert scores == sorted(scores, reverse=True)

    def test_title_patterns(self, insight_agent: ContentInsightAgent,
                            sample_analysis_list: list[VideoAnalysisResult]) -> None:
        insight = insight_agent.generate_insight(sample_analysis_list)
        assert len(insight.title_patterns) >= 2
        for p in insight.title_patterns:
            assert "pattern" in p
            assert p.get("effectiveness") in ("high", "medium")

    def test_hook_formulas(self, insight_agent: ContentInsightAgent,
                           sample_analysis_list: list[VideoAnalysisResult]) -> None:
        insight = insight_agent.generate_insight(sample_analysis_list)
        assert len(insight.hook_formulas) == 4
        for f in insight.hook_formulas:
            assert "formula" in f

    def test_calendar_entries_valid(self, insight_agent: ContentInsightAgent,
                                    sample_analysis_list: list[VideoAnalysisResult]) -> None:
        insight = insight_agent.generate_insight(sample_analysis_list)
        weekdays = {"周一", "周二", "周三", "周四", "周五", "周六", "周日"}
        for entry in insight.content_calendar:
            assert entry.day in weekdays
            assert entry.content_type in ("short_video", "image_text")
            assert entry.production_mode in ("human_shoot", "ai_digital")

    def test_calendar_has_mixed_modes(self, insight_agent: ContentInsightAgent,
                                      sample_analysis_list: list[VideoAnalysisResult]) -> None:
        insight = insight_agent.generate_insight(sample_analysis_list)
        modes = {e.production_mode for e in insight.content_calendar}
        assert "human_shoot" in modes
        assert "ai_digital" in modes

    def test_less_than_min_videos(self, insight_agent: ContentInsightAgent) -> None:
        """少于5条视频仍能生成基础洞察。"""
        few = [
            VideoAnalysisResult(analysis_id="VA_a", video_id="dy_a",
                              video_title="测试视频A", viral_score=70, reusability_score=60),
            VideoAnalysisResult(analysis_id="VA_b", video_id="dy_b",
                              video_title="测试视频B", viral_score=80, reusability_score=70),
        ]
        insight = insight_agent.generate_insight(few)
        assert insight.source_video_count == 2
        assert len(insight.topics) >= 1

    def test_empty_results(self, insight_agent: ContentInsightAgent) -> None:
        insight = insight_agent.generate_insight([])
        assert insight.source_video_count == 0
        assert insight.strategy_summary != ""


# ══════════════════════════════════════════════════════════════════════
# 7. ContentInsightStore
# ══════════════════════════════════════════════════════════════════════

class TestContentInsightStore:

    def test_save_and_get(self, insight_agent: ContentInsightAgent,
                          sample_analysis_list: list[VideoAnalysisResult]) -> None:
        insight = insight_agent.generate_insight(sample_analysis_list)
        with tempfile.TemporaryDirectory() as tmp:
            store = ContentInsightStore(csv_path=Path(tmp) / "index.csv")
            store.save(insight)
            loaded = store.get(insight.insight_id)
            assert loaded is not None
            assert loaded.source_video_count == 6
            assert len(loaded.topics) == len(insight.topics)

    def test_list_all(self, insight_agent: ContentInsightAgent,
                      sample_analysis_list: list[VideoAnalysisResult]) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ContentInsightStore(csv_path=Path(tmp) / "index.csv")
            insight = insight_agent.generate_insight(sample_analysis_list)
            store.save(insight)
            index_list = store.list_all()
            assert len(index_list) == 1
            assert index_list[0]["source_video_count"] == "6"

    def test_get_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ContentInsightStore(csv_path=Path(tmp) / "index.csv")
            assert store.get("CI_nonexistent") is None


# ══════════════════════════════════════════════════════════════════════
# 8. ScriptScene
# ══════════════════════════════════════════════════════════════════════

class TestScriptScene:

    def test_defaults(self) -> None:
        s = ScriptScene()
        assert s.scene_number == 0
        assert s.type == ""

    def test_fields(self) -> None:
        s = ScriptScene(
            scene_number=1, duration_seconds=5,
            type="hook", text="开场白", visuals="全景画面", notes="注意语气",
        )
        d = s.to_dict()
        assert d["type"] == "hook"
        assert d["text"] == "开场白"


# ══════════════════════════════════════════════════════════════════════
# 9. ScriptEntry V2.0
# ══════════════════════════════════════════════════════════════════════

class TestScriptEntry:

    def test_default_production_mode(self) -> None:
        e = ScriptEntry()
        assert e.production_mode == "human_shoot"

    def test_human_shoot_mode(self) -> None:
        e = ScriptEntry(
            topic="测试选题", platform="douyin",
            production_mode="human_shoot",
            title="测试标题", hook="测试钩子",
        )
        assert e.production_mode == "human_shoot"
        md = e.to_markdown()
        assert "🎬 人工拍摄" in md

    def test_ai_digital_mode(self) -> None:
        e = ScriptEntry(
            topic="AI选题", platform="douyin",
            production_mode="ai_digital",
            title="AI标题", hook="AI钩子",
        )
        assert e.production_mode == "ai_digital"
        md = e.to_markdown()
        assert "🤖 AI 数字人口播" in md
        assert "画面素材" in md

    def test_serialization_includes_production_mode(self) -> None:
        e = ScriptEntry(topic="测试", production_mode="ai_digital")
        d = e.to_dict()
        assert d["production_mode"] == "ai_digital"

        e2 = ScriptEntry.from_dict(d)
        assert e2.production_mode == "ai_digital"

    def test_backward_compat_no_production_mode(self) -> None:
        """兼容旧版数据 (无 production_mode 字段)。"""
        old_data = {
            "script_id": "SCRIPT_old", "topic": "旧版脚本",
            "platform": "douyin", "content_type": "video",
            "target_audience": "别墅业主", "angle": "旧角度",
            "title": "旧标题", "hook": "旧钩子",
            "scenes": [], "closing_cta": "旧CTA",
            "ai_model": "mock", "status": "draft",
        }
        e = ScriptEntry.from_dict(old_data)
        assert e.production_mode == "human_shoot"  # 默认值

    def test_markdown_human_shoot_no_warning(self) -> None:
        e = ScriptEntry(topic="测试", production_mode="human_shoot",
                       title="测试", hook="钩子")
        md = e.to_markdown()
        assert "画面素材" not in md  # 人工模式不应出现AI提示

    def test_with_scenes(self) -> None:
        e = ScriptEntry(
            topic="完整脚本", platform="douyin",
            production_mode="human_shoot", title="完整标题",
            hook="开场钩子",
            scenes=[
                ScriptScene(scene_number=1, duration_seconds=5, type="hook",
                           text="第一镜台词", visuals="画面1"),
                ScriptScene(scene_number=2, duration_seconds=10, type="solution",
                           text="第二镜台词", visuals="画面2"),
            ],
            closing_cta="结尾CTA",
        )
        d = e.to_dict()
        e2 = ScriptEntry.from_dict(d)
        assert len(e2.scenes) == 2
        assert e2.scenes[0].text == "第一镜台词"
        assert e2.scenes[1].type == "solution"

    def test_markdown_includes_scenes(self) -> None:
        e = ScriptEntry(
            topic="多镜脚本", title="多镜标题", hook="钩子",
            scenes=[ScriptScene(scene_number=1, duration_seconds=3, type="hook",
                               text="台词")],
        )
        md = e.to_markdown()
        assert "第1镜" in md
        assert "台词" in md


# ══════════════════════════════════════════════════════════════════════
# 10. ScriptLibrary V2.0
# ══════════════════════════════════════════════════════════════════════

class TestScriptLibrary:

    @pytest.fixture
    def lib(self) -> ScriptLibrary:
        """创建使用临时目录的 ScriptLibrary。"""
        tmp = Path(tempfile.mkdtemp())
        return ScriptLibrary(scripts_dir=tmp, csv_path=tmp / "script_index.csv")

    def test_add_and_get(self, lib: ScriptLibrary) -> None:
        e = ScriptEntry(topic="测试选题", platform="douyin",
                       title="测试标题", hook="测试钩子")
        lib.add(e)
        assert e.script_id.startswith("SCRIPT_")
        loaded = lib.get(e.script_id)
        assert loaded is not None
        assert loaded.topic == "测试选题"

    def test_production_mode_human(self, lib: ScriptLibrary) -> None:
        e = ScriptEntry(topic="人工脚本", production_mode="human_shoot")
        lib.add(e)
        loaded = lib.get(e.script_id)
        assert loaded is not None
        assert loaded.production_mode == "human_shoot"

    def test_production_mode_ai_digital(self, lib: ScriptLibrary) -> None:
        e = ScriptEntry(topic="AI脚本", production_mode="ai_digital")
        lib.add(e)
        loaded = lib.get(e.script_id)
        assert loaded is not None
        assert loaded.production_mode == "ai_digital"

    def test_list_by_production_mode(self, lib: ScriptLibrary) -> None:
        e1 = ScriptEntry(topic="人工1", production_mode="human_shoot")
        e2 = ScriptEntry(topic="数字人1", production_mode="ai_digital")
        e3 = ScriptEntry(topic="人工2", production_mode="human_shoot")
        lib.add(e1)
        lib.add(e2)
        lib.add(e3)

        human = lib.list_by_production_mode("human_shoot")
        ai = lib.list_by_production_mode("ai_digital")
        assert len(human) == 2
        assert len(ai) == 1

    def test_list_by_production_mode_empty(self, lib: ScriptLibrary) -> None:
        assert lib.list_by_production_mode("human_shoot") == []
        assert lib.list_by_production_mode("ai_digital") == []

    def test_list_all(self, lib: ScriptLibrary) -> None:
        for i in range(3):
            lib.add(ScriptEntry(topic=f"脚本{i}"))
        assert len(lib.list_all()) == 3

    def test_list_by_status(self, lib: ScriptLibrary) -> None:
        e = ScriptEntry(topic="草稿", status="draft")
        lib.add(e)
        drafts = lib.list_by_status("draft")
        assert len(drafts) == 1
        assert lib.list_by_status("published") == []

    def test_list_by_platform(self, lib: ScriptLibrary) -> None:
        lib.add(ScriptEntry(topic="抖音", platform="douyin"))
        lib.add(ScriptEntry(topic="小红书", platform="xiaohongshu"))
        assert len(lib.list_by_platform("douyin")) == 1

    def test_update_status(self, lib: ScriptLibrary) -> None:
        e = ScriptEntry(topic="待审核")
        lib.add(e)
        assert lib.update_status(e.script_id, "reviewed") is True
        updated = lib.get(e.script_id)
        assert updated is not None and updated.status == "reviewed"

    def test_update_status_published(self, lib: ScriptLibrary) -> None:
        e = ScriptEntry(topic="发布测试")
        lib.add(e)
        lib.update_status(e.script_id, "published")
        updated = lib.get(e.script_id)
        assert updated is not None
        assert updated.status == "published"
        assert updated.published_at != ""

    def test_update_nonexistent(self, lib: ScriptLibrary) -> None:
        assert lib.update_status("SCRIPT_nonexistent", "reviewed") is False

    def test_get_nonexistent(self, lib: ScriptLibrary) -> None:
        assert lib.get("SCRIPT_nonexistent") is None

    def test_markdown_file_created(self, lib: ScriptLibrary) -> None:
        e = ScriptEntry(topic="Markdown测试", title="MD标题", hook="钩子",
                       production_mode="human_shoot")
        lib.add(e)
        md_path = lib._scripts_dir / f"{e.script_id}.md"
        assert md_path.exists()
        content = md_path.read_text()
        assert "MD标题" in content
        assert "🎬 人工拍摄" in content


# ══════════════════════════════════════════════════════════════════════
# 11. 集成测试: VideoAnalysis → ContentInsight → Script
# ══════════════════════════════════════════════════════════════════════

class TestIntegration:

    def test_full_pipeline(self, insight_agent: ContentInsightAgent,
                           sample_analysis_list: list[VideoAnalysisResult]) -> None:
        """完整数据流: 分析 → 洞察 → 脚本。"""
        # Step 1: 生成洞察
        insight = insight_agent.generate_insight(sample_analysis_list)
        assert insight.source_video_count == 6
        assert len(insight.recommended_topics) >= 5

        # Step 2: 根据推荐选题生成脚本
        with tempfile.TemporaryDirectory() as tmp:
            lib = ScriptLibrary(scripts_dir=Path(tmp), csv_path=Path(tmp) / "idx.csv")
            for i, topic in enumerate(insight.recommended_topics[:3]):
                entry = ScriptEntry(
                    topic=topic,
                    platform="douyin",
                    target_audience="别墅业主",
                    angle=insight.demand_gaps[0].suggested_angle if insight.demand_gaps else "",
                    title=topic,
                    hook=insight.hook_formulas[0]["example"] if insight.hook_formulas else "钩子",
                    production_mode="ai_digital" if i % 2 == 0 else "human_shoot",
                )
                lib.add(entry)

            all_scripts = lib.list_all()
            assert len(all_scripts) == 3

            human_scripts = lib.list_by_production_mode("human_shoot")
            ai_scripts = lib.list_by_production_mode("ai_digital")
            assert len(human_scripts) + len(ai_scripts) == 3

    def test_insight_to_calendar(self, insight_agent: ContentInsightAgent,
                                 sample_analysis_list: list[VideoAnalysisResult]) -> None:
        """验证洞察中的日历可转化为脚本条目。"""
        insight = insight_agent.generate_insight(sample_analysis_list)
        assert len(insight.content_calendar) == 7

        # 周末更多 AI 数字人内容
        weekend_modes = [
            e.production_mode
            for e in insight.content_calendar
            if e.day in ("周六", "周日")
        ]
        assert len(weekend_modes) == 2

    def test_store_roundtrip_full(self, insight_agent: ContentInsightAgent,
                                  sample_analysis_list: list[VideoAnalysisResult]) -> None:
        """ContentInsight JSON 保存/加载完整性。"""
        insight = insight_agent.generate_insight(sample_analysis_list)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "roundtrip.json"
            insight.save(p)
            loaded = ContentInsight.load(p)
            assert loaded.source_video_count == insight.source_video_count
            assert loaded.strategy_summary == insight.strategy_summary
            assert len(loaded.topics) == len(insight.topics)
            assert len(loaded.demand_gaps) == len(insight.demand_gaps)
            assert len(loaded.content_calendar) == len(insight.content_calendar)
