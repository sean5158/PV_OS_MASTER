"""Keyword Expander + Discovery Task 测试 (P2-1 扩展)。

覆盖: 词根加载/AI扩展/搜索矩阵/发现任务/全链路。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_keyword_discovery.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from keyword_expander import (  # noqa: E402
    KeywordExpander,
    KeywordEntry,
    ExpandResult,
    DiscoveryTaskDef,
)
from discovery_task import DiscoveryTaskRunner, DiscoveryRunResult  # noqa: E402


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def expander() -> KeywordExpander:
    return KeywordExpander(mode="mock")


@pytest.fixture
def runner() -> DiscoveryTaskRunner:
    return DiscoveryTaskRunner(mode="mock")


# ══════════════════════════════════════════════════════════════════════
# 词根加载测试
# ══════════════════════════════════════════════════════════════════════

class TestSeedKeywords:

    def test_load_seed_keywords(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        assert len(entries) == 10

    def test_all_entries_have_required_fields(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        for e in entries:
            assert e.keyword != ""
            assert e.category != ""
            assert e.grade in ("S", "A", "B", "C")

    def test_get_active_s(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        active = expander.get_active_seeds(entries, grade_filter="S")
        assert len(active) >= 2
        assert all(e.grade == "S" for e in active)

    def test_get_active_a(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        active = expander.get_active_seeds(entries, grade_filter="A")
        assert len(active) >= 5
        for e in active:
            assert e.grade in ("S", "A")

    def test_s_grade_keywords_include_villa(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        s_kw = [e.keyword for e in entries if e.grade == "S"]
        assert "别墅光伏" in s_kw
        assert "家庭光伏" in s_kw


# ══════════════════════════════════════════════════════════════════════
# 关键词扩展测试
# ══════════════════════════════════════════════════════════════════════

class TestKeywordExpansion:

    def test_expand_single_generates_platform_hints(self, expander: KeywordExpander) -> None:
        seed = KeywordEntry(keyword="别墅光伏", category="场景词", grade="S")
        result = expander.expand_single(seed)
        assert len(result.platform_hints) >= 3
        assert "别墅光伏多少钱" in result.platform_hints

    def test_expand_single_generates_region_combos(self, expander: KeywordExpander) -> None:
        seed = KeywordEntry(keyword="家庭光伏", category="行业词", grade="S")
        result = expander.expand_single(seed)
        assert len(result.region_combos) >= 4
        assert "成都 家庭光伏" in result.region_combos

    def test_expand_single_generates_scenario_combos(self, expander: KeywordExpander) -> None:
        seed = KeywordEntry(keyword="别墅光伏", category="场景词", grade="S")
        result = expander.expand_single(seed)
        assert len(result.scenario_combos) >= 3

    def test_expand_b_grade_skips_scenarios(self, expander: KeywordExpander) -> None:
        """B级词根不生成场景组合。"""
        seed = KeywordEntry(keyword="储能", category="行业词", grade="B")
        result = expander.expand_single(seed)
        assert len(result.scenario_combos) == 0

    def test_all_keywords_deduplicated(self, expander: KeywordExpander) -> None:
        seed = KeywordEntry(keyword="别墅光伏", category="场景词", grade="S")
        result = expander.expand_single(seed)
        all_kw = result.all_keywords()
        assert len(all_kw) == len(set(all_kw))  # 无重复

    def test_all_keywords_includes_seed(self, expander: KeywordExpander) -> None:
        seed = KeywordEntry(keyword="别墅光伏", category="场景词", grade="S")
        result = expander.expand_single(seed)
        all_kw = result.all_keywords()
        assert "别墅光伏" in all_kw

    def test_expand_all(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        s_entries = expander.get_active_seeds(entries, grade_filter="S")
        results = expander.expand_all(s_entries)
        assert len(results) >= 2


# ══════════════════════════════════════════════════════════════════════
# 搜索矩阵测试
# ══════════════════════════════════════════════════════════════════════

class TestSearchMatrix:

    def test_build_matrix_has_keywords(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        matrix = expander.build_search_matrix(entries)
        assert len(matrix) >= 50

    def test_matrix_starts_with_s_grade(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        matrix = expander.build_search_matrix(entries)
        # 前几个应该是 S 级词根的产物
        assert len(matrix) > 0
        s_keywords = [k for k in matrix if "别墅光伏" in k or "家庭光伏" in k or "光伏安装" in k]
        assert len(s_keywords) > 0

    def test_matrix_no_duplicates(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        matrix = expander.build_search_matrix(entries)
        assert len(matrix) == len(set(matrix))


# ══════════════════════════════════════════════════════════════════════
# 发现任务测试
# ══════════════════════════════════════════════════════════════════════

class TestDiscoveryTasks:

    def test_generate_tasks(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        assert len(tasks) == 2

    def test_tasks_have_keywords(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        for t in tasks:
            assert len(t.keywords) >= 5

    def test_tasks_have_platforms(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        assert "douyin" in tasks[0].platforms

    def test_p0_task_first(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        assert tasks[0].priority == "P0"

    def test_task_ids_unique(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        ids = [t.task_id for t in tasks]
        assert len(ids) == len(set(ids))


# ══════════════════════════════════════════════════════════════════════
# Discovery Task Runner 测试
# ══════════════════════════════════════════════════════════════════════

class TestDiscoveryTaskRunner:

    def test_run_from_seeds(self, runner: DiscoveryTaskRunner) -> None:
        result = runner.run_from_seeds(["别墅光伏", "家庭光伏"])
        assert isinstance(result, DiscoveryRunResult)
        assert result.seed_keywords == ["别墅光伏", "家庭光伏"]
        assert result.total_candidates >= 1

    def test_run_result_has_counts(self, runner: DiscoveryTaskRunner) -> None:
        result = runner.run_from_seeds(["别墅光伏"])
        assert result.total_discovered >= 0
        assert result.duration_seconds >= 0

    def test_run_with_unknown_seed(self, runner: DiscoveryTaskRunner) -> None:
        """不在库中的词根也创建临时词根继续执行。"""
        result = runner.run_from_seeds(["成都光伏报价"])
        assert result.total_candidates >= 0

    def test_get_master_summary(self, runner: DiscoveryTaskRunner) -> None:
        summary = runner.get_master_summary()
        assert "total" in summary
        assert "by_grade" in summary
        assert "by_platform" in summary

    def test_run_result_to_dict(self, runner: DiscoveryTaskRunner) -> None:
        result = runner.run_from_seeds(["别墅光伏"])
        d = result.to_dict()
        assert d["seed_keywords"] == ["别墅光伏"]
        assert "duration_seconds" in d


# ══════════════════════════════════════════════════════════════════════
# 全链路测试
# ══════════════════════════════════════════════════════════════════════

class TestFullChain:

    def test_seed_to_discovery_chain(self, runner: DiscoveryTaskRunner) -> None:
        """完整链路: 词根→扩展→任务→发现→入库。"""
        result = runner.run_from_seeds(["别墅光伏", "家庭光伏", "阳光房光伏"])

        assert result.seed_keywords == ["别墅光伏", "家庭光伏", "阳光房光伏"]
        assert len(result.tasks) >= 1
        assert result.mode == "mock"

    def test_chain_idempotent(self, runner: DiscoveryTaskRunner) -> None:
        """重复运行不报错。"""
        result1 = runner.run_from_seeds(["别墅光伏"])
        result2 = runner.run_from_seeds(["别墅光伏"])
        assert result1.mode == result2.mode
