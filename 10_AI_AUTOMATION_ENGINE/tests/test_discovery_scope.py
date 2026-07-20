"""DiscoveryTask 范围校验测试。

覆盖: region_scope / customer_scope / is_keyword_allowed / FORBIDDEN_KEYWORDS /
       业务边界 / is_valid_scope / RunResult scopes。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_discovery_scope.py -v
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
    DiscoveryTaskDef,
    is_keyword_allowed,
    FORBIDDEN_KEYWORDS,
    VALID_REGION_SCOPE,
    VALID_CUSTOMER_SCOPE,
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
# FORBIDDEN_KEYWORDS
# ══════════════════════════════════════════════════════════════════════

class TestForbiddenKeywords:

    def test_contains_rural(self) -> None:
        assert "农村光伏" in FORBIDDEN_KEYWORDS
        assert "农村" in FORBIDDEN_KEYWORDS

    def test_contains_industrial(self) -> None:
        assert "工商业光伏" in FORBIDDEN_KEYWORDS
        assert "大型工商业" in FORBIDDEN_KEYWORDS
        assert "工厂光伏" in FORBIDDEN_KEYWORDS

    def test_contains_national(self) -> None:
        assert "全国光伏" in FORBIDDEN_KEYWORDS
        assert "全国安装" in FORBIDDEN_KEYWORDS

    def test_contains_ground_station(self) -> None:
        assert "地面电站" in FORBIDDEN_KEYWORDS
        assert "集中式" in FORBIDDEN_KEYWORDS


# ══════════════════════════════════════════════════════════════════════
# is_keyword_allowed
# ══════════════════════════════════════════════════════════════════════

class TestIsKeywordAllowed:

    def test_allowed_keywords(self) -> None:
        assert is_keyword_allowed("别墅光伏") is True
        assert is_keyword_allowed("成都光伏安装") is True
        assert is_keyword_allowed("家庭光伏多少钱") is True

    def test_rural_keywords_blocked(self) -> None:
        assert is_keyword_allowed("农村光伏安装") is False
        assert is_keyword_allowed("光伏扶贫项目") is False
        assert is_keyword_allowed("农村光伏扶贫") is False

    def test_industrial_keywords_blocked(self) -> None:
        assert is_keyword_allowed("工商业光伏方案") is False
        assert is_keyword_allowed("工厂光伏安装") is False
        assert is_keyword_allowed("大型工商业光伏") is False

    def test_national_keywords_blocked(self) -> None:
        assert is_keyword_allowed("全国光伏安装") is False
        assert is_keyword_allowed("全国各地光伏") is False

    def test_ground_station_blocked(self) -> None:
        assert is_keyword_allowed("地面电站建设") is False


# ══════════════════════════════════════════════════════════════════════
# VALID_SCOPE constants
# ══════════════════════════════════════════════════════════════════════

class TestValidScopes:

    def test_valid_region_scope(self) -> None:
        assert "四川" in VALID_REGION_SCOPE
        assert "重庆" in VALID_REGION_SCOPE
        assert "贵州" in VALID_REGION_SCOPE
        assert len(VALID_REGION_SCOPE) == 3

    def test_valid_customer_scope(self) -> None:
        assert "城市家庭光伏" in VALID_CUSTOMER_SCOPE
        assert "别墅/叠拼/高价值住宅" in VALID_CUSTOMER_SCOPE
        assert "小商业" in VALID_CUSTOMER_SCOPE

    def test_region_scope_no_national(self) -> None:
        """禁止全国/无区域范围。"""
        assert "全国" not in VALID_REGION_SCOPE
        assert "全部" not in VALID_REGION_SCOPE

    def test_customer_scope_no_rural(self) -> None:
        """禁止农村光伏客户范围。"""
        assert "农村" not in str(VALID_CUSTOMER_SCOPE)
        assert "扶贫" not in str(VALID_CUSTOMER_SCOPE)


# ══════════════════════════════════════════════════════════════════════
# DiscoveryTaskDef.is_valid_scope
# ══════════════════════════════════════════════════════════════════════

class TestDiscoveryTaskDefScope:

    def test_default_is_valid(self) -> None:
        task = DiscoveryTaskDef()
        assert task.is_valid_scope() is True

    def test_default_region_scope(self) -> None:
        task = DiscoveryTaskDef()
        assert task.region_scope == ["四川", "重庆", "贵州"]

    def test_default_customer_scope(self) -> None:
        task = DiscoveryTaskDef()
        assert "城市家庭光伏" in task.customer_scope
        assert "别墅/叠拼/高价值住宅" in task.customer_scope

    def test_invalid_region_scope(self) -> None:
        task = DiscoveryTaskDef(
            task_id="TEST_001",
            region_scope=["全国"],  # 不是四川/重庆/贵州
        )
        assert task.is_valid_scope() is False

    def test_invalid_customer_scope(self) -> None:
        task = DiscoveryTaskDef(
            task_id="TEST_002",
            customer_scope=["农村光伏"],  # 禁止
        )
        assert task.is_valid_scope() is False

    def test_empty_region_scope_invalid(self) -> None:
        task = DiscoveryTaskDef(region_scope=[])
        assert task.is_valid_scope() is False

    def test_mixed_valid_invalid_region(self) -> None:
        task = DiscoveryTaskDef(region_scope=["四川", "全国"])
        assert task.is_valid_scope() is False

    def test_all_valid_scopes(self) -> None:
        task = DiscoveryTaskDef(
            region_scope=["四川", "重庆", "贵州"],
            customer_scope=["城市家庭光伏", "别墅/叠拼/高价值住宅", "小商业"],
        )
        assert task.is_valid_scope() is True


# ══════════════════════════════════════════════════════════════════════
# DiscoveryTaskDef 序列化
# ══════════════════════════════════════════════════════════════════════

class TestDiscoveryTaskDefSerialization:

    def test_to_dict_includes_scopes(self) -> None:
        task = DiscoveryTaskDef(task_id="T001", keywords=["别墅光伏"])
        d = task.to_dict()
        assert "region_scope" in d
        assert "customer_scope" in d
        assert d["region_scope"] == ["四川", "重庆", "贵州"]

    def test_custom_scopes_to_dict(self) -> None:
        task = DiscoveryTaskDef(
            task_id="T002",
            region_scope=["四川"],
            customer_scope=["城市家庭光伏"],
        )
        d = task.to_dict()
        assert d["region_scope"] == ["四川"]
        assert d["customer_scope"] == ["城市家庭光伏"]


# ══════════════════════════════════════════════════════════════════════
# generate_discovery_tasks — 范围校验
# ══════════════════════════════════════════════════════════════════════

class TestGenerateTasksScope:

    def test_tasks_have_region_scope(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        for t in tasks:
            assert len(t.region_scope) >= 1
            assert all(r in VALID_REGION_SCOPE for r in t.region_scope)

    def test_tasks_have_customer_scope(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        for t in tasks:
            assert len(t.customer_scope) >= 1
            assert all(c in VALID_CUSTOMER_SCOPE for c in t.customer_scope)

    def test_tasks_all_valid(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        for t in tasks:
            assert t.is_valid_scope() is True

    def test_no_forbidden_keywords_in_tasks(self, expander: KeywordExpander) -> None:
        entries = expander.load_seed_keywords()
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        for t in tasks:
            for kw in t.keywords:
                assert is_keyword_allowed(kw) is True, f"禁止关键词: {kw}"


# ══════════════════════════════════════════════════════════════════════
# DiscoveryRunResult — 范围
# ══════════════════════════════════════════════════════════════════════

class TestDiscoveryRunResultScope:

    def test_result_has_region_scope(self, runner: DiscoveryTaskRunner) -> None:
        result = runner.run_from_seeds(["别墅光伏"])
        assert result.region_scope == ["四川", "重庆", "贵州"]

    def test_result_has_customer_scope(self, runner: DiscoveryTaskRunner) -> None:
        result = runner.run_from_seeds(["家庭光伏"])
        assert "城市家庭光伏" in result.customer_scope

    def test_result_to_dict_includes_scopes(self, runner: DiscoveryTaskRunner) -> None:
        result = runner.run_from_seeds(["别墅光伏"])
        d = result.to_dict()
        assert "region_scope" in d
        assert "customer_scope" in d


# ══════════════════════════════════════════════════════════════════════
# full chain — 范围贯穿
# ══════════════════════════════════════════════════════════════════════

class TestFullChainScope:

    def test_seed_to_result_scope_chain(self, runner: DiscoveryTaskRunner) -> None:
        """完整链路: 词根→任务→结果，范围字段贯穿。"""
        result = runner.run_from_seeds(["别墅光伏", "家庭光伏", "阳光房光伏"])

        # RunResult 有范围
        assert "四川" in result.region_scope
        assert "城市家庭光伏" in result.customer_scope

        # Tasks 有范围
        assert len(result.tasks) >= 1
        for t_dict in result.tasks:
            assert "region_scope" in t_dict
            assert "customer_scope" in t_dict

    def test_no_nationwide_tasks(self, runner: DiscoveryTaskRunner) -> None:
        """禁止全国无区域任务。"""
        result = runner.run_from_seeds(["别墅光伏"])
        for t_dict in result.tasks:
            assert "全国" not in t_dict.get("region_scope", [])

    def test_no_rural_in_result_tasks(self, runner: DiscoveryTaskRunner) -> None:
        """禁止农村光伏任务。"""
        result = runner.run_from_seeds(["别墅光伏", "家庭光伏"])
        for t_dict in result.tasks:
            customer = t_dict.get("customer_scope", [])
            assert "农村光伏" not in customer
