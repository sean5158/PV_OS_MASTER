"""Competitor Discovery Engine 测试 (P2-1)。

覆盖: 搜索/初筛/评分/入库/日报/全流程/关键词匹配/排除规则。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_competitor_discovery.py -v
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from competitor_discovery import (  # noqa: E402
    CompetitorDiscovery,
    CompetitorCandidate,
    ScoreDetail,
    DiscoveryReport,
    MOCK_CANDIDATES,
    EXCLUDE_TYPES,
    SCORE_MAX,
    COMPETITOR_MASTER,
    DISCOVERY_LOGS_DIR,
)


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def engine() -> CompetitorDiscovery:
    return CompetitorDiscovery(mode="mock")


@pytest.fixture
def clean_master() -> None:
    """确保测试不污染真实 master 文件。"""
    # 备份
    backup = None
    if COMPETITOR_MASTER.exists():
        backup = COMPETITOR_MASTER.read_text(encoding="utf-8-sig")
    yield
    # 恢复
    if backup is not None:
        COMPETITOR_MASTER.write_text(backup, encoding="utf-8-sig")
    elif COMPETITOR_MASTER.exists():
        COMPETITOR_MASTER.unlink()


# ══════════════════════════════════════════════════════════════════════
# ScoreDetail 测试
# ══════════════════════════════════════════════════════════════════════

class TestScoreDetail:

    def test_total_sums_dimensions(self) -> None:
        s = ScoreDetail(business_match=30, home_pv_match=20, premium_scene=15,
                        region_match=15, comment_value=10, activity_7d=10)
        assert s.total == 100

    def test_grade_s(self) -> None:
        s = ScoreDetail(business_match=28, home_pv_match=18, premium_scene=12,
                        region_match=12, comment_value=9, activity_7d=10)
        assert s.total == 89
        assert s.grade == "S"

    def test_grade_a(self) -> None:
        s = ScoreDetail(business_match=20, home_pv_match=15, premium_scene=9,
                        region_match=10, comment_value=6, activity_7d=6)
        assert 65 <= s.total < 80
        assert s.grade == "A"

    def test_grade_b(self) -> None:
        s = ScoreDetail(business_match=15, home_pv_match=10, premium_scene=5,
                        region_match=8, comment_value=3, activity_7d=5)
        assert 45 <= s.total < 65
        assert s.grade == "B"

    def test_grade_c(self) -> None:
        s = ScoreDetail(business_match=8, home_pv_match=5, premium_scene=2,
                        region_match=3, comment_value=1, activity_7d=1)
        assert s.total < 45
        assert s.grade == "C"

    def test_grade_s_boundary(self) -> None:
        s = ScoreDetail(business_match=25, home_pv_match=18, premium_scene=12,
                        region_match=10, comment_value=8, activity_7d=7)
        assert s.total == 80
        assert s.grade == "S"


# ══════════════════════════════════════════════════════════════════════
# 搜索测试
# ══════════════════════════════════════════════════════════════════════

class TestSearch:

    def test_single_keyword_finds_candidates(self, engine: CompetitorDiscovery) -> None:
        results = engine.search_by_keywords(["别墅光伏"])
        assert len(results) >= 1
        names = [r["account_name"] for r in results]
        assert "别墅光伏改造日记" in names

    def test_multiple_keywords(self, engine: CompetitorDiscovery) -> None:
        results = engine.search_by_keywords(["成都光伏安装", "重庆光伏"])
        assert len(results) >= 2

    def test_no_match_keyword(self, engine: CompetitorDiscovery) -> None:
        results = engine.search_by_keywords(["不存在的关键词xyz"])
        assert results == []

    def test_all_candidates_have_required_fields(self, engine: CompetitorDiscovery) -> None:
        results = engine.search_by_keywords(["光伏安装"])
        for r in results:
            assert "platform" in r
            assert "account_id" in r
            assert "account_name" in r
            assert "account_type" in r


# ══════════════════════════════════════════════════════════════════════
# 初筛测试 (7排除规则)
# ══════════════════════════════════════════════════════════════════════

class TestPrescreen:

    def test_info_account_excluded(self, engine: CompetitorDiscovery) -> None:
        candidates = [c for c in MOCK_CANDIDATES if c["account_type"] == "info_account"]
        assert len(candidates) >= 1
        passed = engine.prescreen(candidates)
        assert len(passed) == 0

    def test_supplier_excluded(self, engine: CompetitorDiscovery) -> None:
        candidates = [c for c in MOCK_CANDIDATES if c["account_type"] == "supplier"]
        assert len(candidates) >= 1
        passed = engine.prescreen(candidates)
        assert len(passed) == 0

    def test_casual_excluded(self, engine: CompetitorDiscovery) -> None:
        candidates = [c for c in MOCK_CANDIDATES if c["account_type"] == "casual"]
        assert len(candidates) >= 1
        passed = engine.prescreen(candidates)
        assert len(passed) == 0

    def test_regional_installer_passes(self, engine: CompetitorDiscovery) -> None:
        candidates = [c for c in MOCK_CANDIDATES if c["account_type"] == "regional_installer"]
        passed = engine.prescreen(candidates)
        assert len(passed) >= 2

    def test_all_exclude_types_defined(self) -> None:
        """7种排除类型已定义。"""
        assert len(EXCLUDE_TYPES) == 7
        assert "info_account" in EXCLUDE_TYPES
        assert "supplier" in EXCLUDE_TYPES
        assert "casual" in EXCLUDE_TYPES

    def test_prescreen_output_is_competitor_candidate(self, engine: CompetitorDiscovery) -> None:
        candidates = [c for c in MOCK_CANDIDATES if c["account_type"] == "regional_installer"]
        passed = engine.prescreen(candidates)
        for p in passed:
            assert isinstance(p, CompetitorCandidate)
            assert p.prescreen_result == "passed"


# ══════════════════════════════════════════════════════════════════════
# 评分测试
# ══════════════════════════════════════════════════════════════════════

class TestScoring:

    def test_score_regional_installer_is_high(self, engine: CompetitorDiscovery) -> None:
        candidates = [c for c in MOCK_CANDIDATES if c["account_id"] == "reg_install_001"]
        passed = engine.prescreen(candidates)
        scored = engine.score_candidates(passed)
        assert len(scored) == 1
        assert scored[0].score.grade in ("S", "A")

    def test_score_national_brand(self, engine: CompetitorDiscovery) -> None:
        candidates = [c for c in MOCK_CANDIDATES if c["account_type"] == "national_brand"]
        passed = engine.prescreen(candidates)
        scored = engine.score_candidates(passed)
        assert len(scored) >= 1
        for s in scored:
            assert s.score.grade in ("S", "A", "B")

    def test_veto_business_match_low(self, engine: CompetitorDiscovery) -> None:
        """业务匹配<10 → 一票否决。"""
        # 创建一个业务匹配极低的候选
        from competitor_discovery import CompetitorCandidate
        cc = CompetitorCandidate(
            platform="douyin", account_id="low_biz_001",
            account_name="低业务账号", account_type="casual",
            discovery_keyword="无关",
        )
        scored = engine.score_candidates([cc])
        assert len(scored) == 0  # 被否决

    def test_score_dimensions_within_range(self, engine: CompetitorDiscovery) -> None:
        candidates = [c for c in MOCK_CANDIDATES if c["account_type"] == "regional_installer"]
        passed = engine.prescreen(candidates)
        scored = engine.score_candidates(passed)
        for s in scored:
            assert 0 <= s.score.business_match <= SCORE_MAX["business_match"]
            assert 0 <= s.score.home_pv_match <= SCORE_MAX["home_pv_match"]
            assert 0 <= s.score.premium_scene <= SCORE_MAX["premium_scene"]
            assert 0 <= s.score.region_match <= SCORE_MAX["region_match"]
            assert 0 <= s.score.comment_value <= SCORE_MAX["comment_value"]
            assert 0 <= s.score.activity_7d <= SCORE_MAX["activity_7d"]

    def test_monitor_frequency_assigned(self, engine: CompetitorDiscovery) -> None:
        candidates = [c for c in MOCK_CANDIDATES if c["account_type"] == "regional_installer"]
        passed = engine.prescreen(candidates)
        scored = engine.score_candidates(passed)
        for s in scored:
            assert s.monitor_frequency in ("6h", "daily", "weekly", "")

    def test_score_total_equals_sum(self, engine: CompetitorDiscovery) -> None:
        candidates = MOCK_CANDIDATES[:3]
        passed = engine.prescreen(candidates)
        scored = engine.score_candidates(passed)
        for s in scored:
            dims = [s.score.business_match, s.score.home_pv_match, s.score.premium_scene,
                    s.score.region_match, s.score.comment_value, s.score.activity_7d]
            assert s.score.total == sum(dims)


# ══════════════════════════════════════════════════════════════════════
# 入库测试
# ══════════════════════════════════════════════════════════════════════

class TestSaveToMaster:

    def test_save_creates_file(self, engine: CompetitorDiscovery) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            import competitor_discovery as cd
            old_path = cd.COMPETITOR_MASTER
            cd.COMPETITOR_MASTER = Path(tmp) / "test_master.csv"

            candidates = [c for c in MOCK_CANDIDATES if c["account_type"] == "regional_installer"]
            passed = engine.prescreen(candidates)
            scored = engine.score_candidates(passed)
            count = engine.save_to_master(scored)
            assert count >= 1
            assert cd.COMPETITOR_MASTER.exists()

            cd.COMPETITOR_MASTER = old_path

    def test_master_csv_has_all_fields(self, engine: CompetitorDiscovery) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            import competitor_discovery as cd
            old_path = cd.COMPETITOR_MASTER
            cd.COMPETITOR_MASTER = Path(tmp) / "test_master.csv"

            candidates = [c for c in MOCK_CANDIDATES if c["account_id"] == "reg_install_001"]
            passed = engine.prescreen(candidates)
            scored = engine.score_candidates(passed)
            engine.save_to_master(scored)

            with open(cd.COMPETITOR_MASTER, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) >= 1
                assert "competitor_id" in rows[0]
                assert "grade" in rows[0]
                assert "total_score" in rows[0]

            cd.COMPETITOR_MASTER = old_path

    def test_duplicate_not_saved(self, engine: CompetitorDiscovery) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            import competitor_discovery as cd
            old_path = cd.COMPETITOR_MASTER
            cd.COMPETITOR_MASTER = Path(tmp) / "test_master.csv"

            candidates = [c for c in MOCK_CANDIDATES if c["account_id"] == "reg_install_001"]
            passed = engine.prescreen(candidates)
            scored = engine.score_candidates(passed)
            engine.save_to_master(scored)
            # 第二次保存同一账号
            count2 = engine.save_to_master(scored)
            assert count2 == 0  # 去重

            cd.COMPETITOR_MASTER = old_path


# ══════════════════════════════════════════════════════════════════════
# 日报测试
# ══════════════════════════════════════════════════════════════════════

class TestReport:

    def test_report_counts_match(self, engine: CompetitorDiscovery) -> None:
        keywords = ["别墅光伏", "成都光伏安装"]
        report = engine.run(keywords)

        total_graded = report.grade_s + report.grade_a + report.grade_b + report.grade_c
        assert total_graded == report.scored
        assert report.scored <= report.prescreen_passed

    def test_report_saved_to_logs(self, engine: CompetitorDiscovery) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            import competitor_discovery as cd
            old_dir = cd.DISCOVERY_LOGS_DIR
            cd.DISCOVERY_LOGS_DIR = Path(tmp)

            report = engine.run(["别墅光伏"])
            log_file = cd.DISCOVERY_LOGS_DIR / f"{report.date}.json"
            assert log_file.exists()

            cd.DISCOVERY_LOGS_DIR = old_dir

    def test_report_has_keywords(self, engine: CompetitorDiscovery) -> None:
        report = engine.run(["别墅光伏", "阳光房光伏"])
        assert "别墅光伏" in report.keywords_used
        assert "阳光房光伏" in report.keywords_used

    def test_report_new_accounts_format(self, engine: CompetitorDiscovery) -> None:
        report = engine.run(["成都光伏安装"])
        for a in report.new_accounts:
            assert "account_name" in a
            assert "platform" in a
            assert "grade" in a
            assert "total_score" in a


# ══════════════════════════════════════════════════════════════════════
# 全流程测试
# ══════════════════════════════════════════════════════════════════════

class TestFullPipeline:

    def test_full_discovery_flow(self, engine: CompetitorDiscovery) -> None:
        """完整流程: 关键词→搜索→初筛→评分→入库→日报。"""
        report = engine.run(["别墅光伏", "成都光伏安装", "家庭光伏", "阳光房光伏"])

        assert report.candidates_total >= 1
        assert report.prescreen_passed >= 1
        assert report.scored >= 1
        assert report.grade_s + report.grade_a + report.grade_b >= 1

    def test_noise_accounts_excluded_from_results(self, engine: CompetitorDiscovery) -> None:
        """排除类账号不出现在最终入库结果中。"""
        report = engine.run(["光伏新闻", "光伏组件"])
        names = [a["account_name"] for a in report.new_accounts]
        assert "光伏资讯日报" not in names
        assert "隆基绿能官方" not in names

    def test_s_grade_accounts_have_high_scores(self, engine: CompetitorDiscovery) -> None:
        report = engine.run(["成都光伏安装", "别墅光伏"])
        s_accounts = [a for a in report.new_accounts if a["grade"] == "S"]
        for a in s_accounts:
            assert a["total_score"] >= 80

    def test_mock_candidates_count(self) -> None:
        """确认 Mock 候选库有 12 个。"""
        assert len(MOCK_CANDIDATES) == 12


# ══════════════════════════════════════════════════════════════════════
# 回归测试
# ══════════════════════════════════════════════════════════════════════

class TestRegression:

    def test_existing_pipeline_unaffected(self) -> None:
        """确认 Pipeline 测试文件无变化。"""
        sys.path.insert(0, str(PROJECT_ROOT / "10_AI_AUTOMATION_ENGINE"))
        from engine import Engine
        wf = PROJECT_ROOT / "10_AI_AUTOMATION_ENGINE" / "workflows" / "comment_to_lead_pipeline.yml"
        engine = Engine(wf)
        comment = {
            "id": "reg_001", "platform": "douyin",
            "content": "成都别墅想装光伏，报个价",
            "author": "test", "create_time": "2026-07-20 10:00:00",
            "ip_location": "四川成都",
        }
        result = engine.run_single(comment)
        assert "_pipeline_error" not in result
        assert result["scoring"]["lead_grade"] == "S"
