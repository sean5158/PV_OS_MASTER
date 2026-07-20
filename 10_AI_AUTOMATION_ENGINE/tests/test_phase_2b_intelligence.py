"""Phase 2B Content Intelligence 测试 (V3.0)。

覆盖: VideoAnalysisResult / ContentIntelligenceAgent / ScriptLibrary /
       数据流: VideoAsset → Analysis → Insight → Script。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_phase_2b_intelligence.py -v
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

from video_asset import VideoAsset  # noqa: E402
from video_analysis_model import (  # noqa: E402
    VideoAnalysisResult, VideoAnalysisStore, ReusableElements,
)
from content_intelligence_agent import (  # noqa: E402
    ContentIntelligenceAgent, ContentInsight, TopicInsight, DemandGap,
    MOCK_ANALYSIS_TEMPLATES,
)
from script_library_model import (  # noqa: E402
    ScriptEntry, ScriptLibrary, ScriptScene,
)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def agent() -> ContentIntelligenceAgent:
    return ContentIntelligenceAgent(mode="mock")


@pytest.fixture
def sample_assets() -> list[VideoAsset]:
    return [
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


# ══════════════════════════════════════════════════════════════════════
# ReusableElements
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

    def test_from_dict(self) -> None:
        d = {"hook_template": "test", "key_phrases": ["a", "b"], "angle_suggestions": []}
        re = ReusableElements.from_dict(d)
        assert re.key_phrases == ["a", "b"]


# ══════════════════════════════════════════════════════════════════════
# VideoAnalysisResult
# ══════════════════════════════════════════════════════════════════════

class TestVideoAnalysisResult:

    def test_nine_dimensions(self) -> None:
        """九维字段全部存在。"""
        r = VideoAnalysisResult(
            hook_3_seconds="钩子",
            pain_point="痛点",
            customer_type="别墅业主",
            video_structure="痛点→方案→数据→CTA",
            title_pattern="数字对比型",
            comment_trigger="代入感",
            viral_reason="强数字对比",
            turning_point="第15秒",
            closing_factor="可上门测量",
        )
        assert r.hook_3_seconds == "钩子"
        assert r.customer_type == "别墅业主"
        assert r.closing_factor == "可上门测量"

    def test_viral_score_range(self) -> None:
        r = VideoAnalysisResult(viral_score=85)
        assert 0 <= r.viral_score <= 100

    def test_reusability_score_range(self) -> None:
        r = VideoAnalysisResult(reusability_score=90)
        assert 0 <= r.reusability_score <= 100

    def test_to_dict(self) -> None:
        r = VideoAnalysisResult(
            video_id="dy_v001",
            video_title="测试",
            viral_score=75,
            reusable=ReusableElements(key_phrases=["省电"]),
        )
        d = r.to_dict()
        assert d["video_id"] == "dy_v001"
        assert d["viral_score"] == 75
        assert d["reusable"]["key_phrases"] == ["省电"]

    def test_from_dict_roundtrip(self) -> None:
        r = VideoAnalysisResult(
            video_id="dy_v001",
            video_title="测试",
            viral_score=80,
            reusable=ReusableElements(key_phrases=["a", "b"]),
        )
        d = r.to_dict()
        r2 = VideoAnalysisResult.from_dict(d)
        assert r2.viral_score == 80
        assert r2.reusable.key_phrases == ["a", "b"]

    def test_to_csv_row(self) -> None:
        r = VideoAnalysisResult(
            analysis_id="VA_001", video_id="v001", video_title="t",
            viral_score=85, reusability_score=90,
        )
        row = r.to_csv_row()
        assert row[0] == "VA_001"
        assert row[1] == "v001"

    def test_from_csv_row_type_coercion(self) -> None:
        """CSV 读取时 int 字段类型转换。"""
        row = ["VA_001", "v001", "t", "", "", "", "", "", "", "", "", "", "85", "90", "", ""]
        r = VideoAnalysisResult.from_csv_row(row)
        assert r.viral_score == 85
        assert isinstance(r.viral_score, int)
        assert r.reusability_score == 90
        assert isinstance(r.reusability_score, int)


# ══════════════════════════════════════════════════════════════════════
# VideoAnalysisStore
# ══════════════════════════════════════════════════════════════════════

class TestVideoAnalysisStore:

    @pytest.fixture
    def store(self) -> VideoAnalysisStore:
        d = Path(tempfile.mkdtemp())
        p = d / "test_analysis.csv"
        s = VideoAnalysisStore(csv_path=p)
        yield s
        p.unlink(missing_ok=True)

    def test_save_and_get(self, store: VideoAnalysisStore) -> None:
        r = VideoAnalysisResult(video_id="v001", viral_score=80)
        store.save(r)
        loaded = store.get(r.analysis_id)
        assert loaded is not None
        assert loaded.viral_score == 80

    def test_list_by_video(self, store: VideoAnalysisStore) -> None:
        store.save(VideoAnalysisResult(video_id="v001"))
        store.save(VideoAnalysisResult(video_id="v001"))
        store.save(VideoAnalysisResult(video_id="v002"))
        results = store.list_by_video("v001")
        assert len(results) == 2

    def test_list_all(self, store: VideoAnalysisStore) -> None:
        store.save(VideoAnalysisResult(video_id="v001"))
        store.save(VideoAnalysisResult(video_id="v002"))
        assert len(store.list_all()) == 2

    def test_get_top_viral(self, store: VideoAnalysisStore) -> None:
        store.save(VideoAnalysisResult(video_id="v001", viral_score=50))
        store.save(VideoAnalysisResult(video_id="v002", viral_score=90))
        store.save(VideoAnalysisResult(video_id="v003", viral_score=30))
        top = store.get_top_viral(limit=2)
        assert len(top) == 2
        assert top[0].viral_score >= top[1].viral_score

    def test_get_nonexistent(self, store: VideoAnalysisStore) -> None:
        assert store.get("no_such_id") is None


# ══════════════════════════════════════════════════════════════════════
# ContentIntelligenceAgent
# ══════════════════════════════════════════════════════════════════════

class TestContentIntelligenceAgent:

    def test_analyze_video(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        result = agent.analyze_video(sample_assets[0])
        assert result.video_title == "别墅光伏安装实拍"
        assert result.hook_3_seconds != ""
        assert result.viral_score >= 0
        assert result.reusability_score >= 0

    def test_analyze_video_has_angle_suggestions(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        result = agent.analyze_video(sample_assets[0])
        assert len(result.reusable.angle_suggestions) >= 2
        assert "成都" in str(result.reusable.angle_suggestions) or "四川" in str(result.reusable.angle_suggestions)

    def test_analyze_batch(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        results = agent.analyze_batch(sample_assets)
        assert len(results) == 3
        for r in results:
            assert r.video_id in {"dy_v001", "dy_v002", "dy_v003"}

    def test_generate_insight(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        insight = agent.generate_insight(sample_assets)
        assert isinstance(insight, ContentInsight)
        assert insight.source_video_count == 3
        assert len(insight.topics) >= 1
        assert len(insight.demand_gaps) == 3
        assert len(insight.title_patterns) >= 2
        assert len(insight.hook_formulas) >= 2
        assert len(insight.recommended_topics) == 5

    def test_insight_topics_have_trend(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        insight = agent.generate_insight(sample_assets)
        for t in insight.topics:
            assert t.trend in ("rising", "stable", "declining")

    def test_insight_demand_gaps_have_opportunity(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        insight = agent.generate_insight(sample_assets)
        for g in insight.demand_gaps:
            assert 0 <= g.opportunity_score <= 100

    def test_insight_save(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        insight = agent.generate_insight(sample_assets)
        p = insight.save()
        assert p.exists()
        # Verify JSON content
        data = json.loads(p.read_text())
        assert "topics" in data
        assert "demand_gaps" in data

    def test_mock_templates_complete(self) -> None:
        """Mock 分析模板完整。"""
        assert "别墅光伏" in MOCK_ANALYSIS_TEMPLATES
        assert "家庭光伏" in MOCK_ANALYSIS_TEMPLATES
        assert "阳光房光伏" in MOCK_ANALYSIS_TEMPLATES
        for template in MOCK_ANALYSIS_TEMPLATES.values():
            assert template["hook_3_seconds"] != ""
            assert template["video_structure"] != ""


# ══════════════════════════════════════════════════════════════════════
# ScriptEntry + ScriptLibrary
# ══════════════════════════════════════════════════════════════════════

class TestScriptEntry:

    def test_create(self) -> None:
        entry = ScriptEntry(
            topic="别墅光伏避坑",
            platform="douyin",
            target_audience="别墅业主",
            angle="成都本地化",
            title="成都别墅装光伏，这3个坑别踩",
            hook="你家别墅想装光伏？",
            closing_cta="评论区告诉我面积，免费算",
        )
        assert entry.platform == "douyin"
        assert entry.status == "draft"

    def test_scenes(self) -> None:
        entry = ScriptEntry(
            topic="测试",
            scenes=[
                ScriptScene(scene_number=1, duration_seconds=5, type="hook", text="开头"),
                ScriptScene(scene_number=2, duration_seconds=15, type="solution", text="正文"),
            ],
        )
        assert len(entry.scenes) == 2
        assert entry.scenes[0].type == "hook"

    def test_to_markdown(self) -> None:
        entry = ScriptEntry(
            title="测试脚本",
            topic="测试",
            hook="钩子文本",
            closing_cta="引导关注",
            scenes=[ScriptScene(scene_number=1, duration_seconds=3, type="hook", text="台词")],
        )
        md = entry.to_markdown()
        assert "# 测试脚本" in md
        assert "钩子文本" in md
        assert "第1镜" in md
        assert "引导关注" in md

    def test_to_dict_roundtrip(self) -> None:
        entry = ScriptEntry(
            topic="测试",
            scenes=[ScriptScene(scene_number=1, duration_seconds=5, type="hook", text="test")],
        )
        d = entry.to_dict()
        e2 = ScriptEntry.from_dict(d)
        assert e2.topic == "测试"
        assert len(e2.scenes) == 1
        assert e2.scenes[0].text == "test"


class TestScriptLibrary:

    @pytest.fixture
    def lib(self) -> ScriptLibrary:
        import script_library_model
        import tempfile as _tmp
        d = Path(_tmp.mkdtemp())
        original = script_library_model.SCRIPTS_AI_DIR
        script_library_model.SCRIPTS_AI_DIR = d
        script_library_model.SCRIPT_INDEX_CSV = d / "script_index.csv"
        yield ScriptLibrary()
        # restore
        import shutil
        shutil.rmtree(d, ignore_errors=True)
        script_library_model.SCRIPTS_AI_DIR = original
        script_library_model.SCRIPT_INDEX_CSV = original / "script_index.csv"

    def test_add_and_get(self, lib: ScriptLibrary) -> None:
        entry = ScriptEntry(topic="测试选题", platform="douyin")
        lib.add(entry)
        assert entry.script_id != ""
        loaded = lib.get(entry.script_id)
        assert loaded is not None
        assert loaded.topic == "测试选题"

    def test_list_all(self, lib: ScriptLibrary) -> None:
        lib.add(ScriptEntry(topic="选题1"))
        lib.add(ScriptEntry(topic="选题2"))
        all_scripts = lib.list_all()
        assert len(all_scripts) == 2

    def test_list_by_status(self, lib: ScriptLibrary) -> None:
        e1 = ScriptEntry(topic="脚本A", status="draft")
        e2 = ScriptEntry(topic="脚本B", status="reviewed")
        lib.add(e1)
        lib.add(e2)
        drafts = lib.list_by_status("draft")
        assert len(drafts) == 1
        assert drafts[0].topic == "脚本A"

    def test_list_by_platform(self, lib: ScriptLibrary) -> None:
        lib.add(ScriptEntry(topic="A", platform="douyin"))
        lib.add(ScriptEntry(topic="B", platform="xiaohongshu"))
        douyin = lib.list_by_platform("douyin")
        assert len(douyin) == 1

    def test_update_status(self, lib: ScriptLibrary) -> None:
        entry = lib.add(ScriptEntry(topic="测试"))
        assert lib.update_status(entry.script_id, "reviewed") is True
        loaded = lib.get(entry.script_id)
        assert loaded is not None and loaded.status == "reviewed"

    def test_update_status_published(self, lib: ScriptLibrary) -> None:
        entry = lib.add(ScriptEntry(topic="测试2"))
        lib.update_status(entry.script_id, "published")
        loaded = lib.get(entry.script_id)
        assert loaded is not None
        assert loaded.status == "published"
        assert loaded.published_at != ""


# ══════════════════════════════════════════════════════════════════════
# 数据流: VideoAsset → Analysis → Insight → Script
# ══════════════════════════════════════════════════════════════════════

class TestFullDataFlow:

    def test_video_to_analysis(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        """VideoAsset → VideoAnalysisResult。"""
        result = agent.analyze_video(sample_assets[0])
        assert result.video_id == "dy_v001"
        assert result.viral_score >= 0

    def test_analysis_to_insight(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        """VideoAnalysisResult → ContentInsight。"""
        results = agent.analyze_batch(sample_assets)
        insight = agent.generate_insight(sample_assets, results)
        assert insight.source_video_count == 3
        assert len(insight.recommended_topics) == 5

    def test_insight_to_script(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        """ContentInsight → ScriptEntry。"""
        insight = agent.generate_insight(sample_assets)
        # 从推荐选题创建脚本
        topic = insight.recommended_topics[0]
        entry = ScriptEntry(
            topic=topic,
            platform="douyin",
            target_audience="别墅业主",
            angle="成都本地化",
            title=topic,
            hook="黄金三秒钩子",
            closing_cta="评论区联系",
        )
        assert entry.topic != ""
        assert entry.platform == "douyin"

    def test_full_pipeline(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        """完整数据流: VideoAsset → Analysis → Insight → Script → Library。"""
        # Phase 1: 分析视频
        results = agent.analyze_batch(sample_assets)
        assert len(results) == 3

        # Phase 2: 生成洞察
        insight = agent.generate_insight(sample_assets, results)
        assert len(insight.recommended_topics) == 5

        # Phase 3: 从推荐选题创建脚本
        entries: list[ScriptEntry] = []
        for i, topic in enumerate(insight.recommended_topics[:3], start=1):
            entry = ScriptEntry(
                topic=topic,
                platform="douyin",
                target_audience="城市家庭",
                angle="成都本地化",
                title=topic,
                hook=f"试试这个方案，省电又省钱！",
                closing_cta="评论区留言，免费算报价",
                scenes=[
                    ScriptScene(scene_number=1, duration_seconds=3, type="hook",
                               text="试试这个方案", visuals="光伏板画面"),
                    ScriptScene(scene_number=2, duration_seconds=10, type="solution",
                               text="本地真实案例", visuals="施工画面"),
                ],
            )
            entries.append(entry)

        assert len(entries) == 3
        for e in entries:
            assert len(e.scenes) == 2
            md = e.to_markdown()
            assert e.topic in md
            assert "第1镜" in md


# ══════════════════════════════════════════════════════════════════════
# 业务边界
# ══════════════════════════════════════════════════════════════════════

class TestBusinessBoundary:

    def test_angle_suggestions_include_region(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        """差异化建议包含四川/成都/重庆/贵州。"""
        result = agent.analyze_video(sample_assets[0])
        region_keywords = ["成都", "四川", "重庆", "贵州", "川渝黔"]
        suggestions = " ".join(result.reusable.angle_suggestions)
        assert any(k in suggestions for k in region_keywords)

    def test_recommended_topics_are_localized(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        """推荐选题本地化。"""
        insight = agent.generate_insight(sample_assets)
        topics = " ".join(insight.recommended_topics)
        assert any(city in topics for city in ["成都", "重庆", "贵阳"])

    def test_no_national_content(self, agent: ContentIntelligenceAgent, sample_assets: list[VideoAsset]) -> None:
        """推荐选题不含"全国"。"""
        insight = agent.generate_insight(sample_assets)
        for topic in insight.recommended_topics:
            assert "全国" not in topic
