"""analyze_source_account 步骤专项测试 (P1-3)。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_competitor_account.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(ENGINE_ROOT))

from engine import Engine  # noqa: E402


@pytest.fixture
def engine() -> Engine:
    wf = PROJECT_ROOT / "10_AI_AUTOMATION_ENGINE" / "workflows" / "comment_to_lead_pipeline.yml"
    return Engine(wf)


def _run(engine, source_account, video_title="", source_account_id="", platform="douyin"):
    return engine.run_single({
        "id": "asa_test",
        "platform": platform,
        "content": "想装光伏，了解一下",
        "author": "test_user",
        "create_time": "2026-07-20 10:00:00",
        "ip_location": "四川成都",
        "video_title": video_title,
        "source_account": source_account,
        "source_account_id": source_account_id,
    })


class TestAccountSource:
    """analyze_source_account 输出验证。"""

    def test_output_fields_exist(self, engine):
        """必须输出 account_category, authority_score, source_score。"""
        r = _run(engine, "光伏老王", "别墅光伏安装")
        asa = r.get("account_source", {})
        assert "account_category" in asa
        assert "account_authority_score" in asa
        assert "customer_source_score" in asa
        assert "monitor_level" in asa
        assert "match_type" in asa

    def test_csv_exact_match(self, engine):
        """CSV 中有 PV_COMP_000002 时精确匹配。"""
        r = _run(engine, "", source_account_id="PV_COMP_000002")
        asa = r["account_source"]
        assert asa["match_type"] == "exact_csv"
        assert asa["monitor_level"] == "S"
        assert asa["customer_source_score"] >= 80

    def test_csv_name_match(self, engine):
        """按账号名称模糊匹配。"""
        r = _run(engine, source_account="李哥装修日记")
        asa = r["account_source"]
        assert asa["match_type"] == "name_match"
        assert asa["customer_source_score"] >= 80

    def test_classify_personal_blogger(self, engine):
        """光伏+个人标识 → 个人光伏内容博主。"""
        r = _run(engine, "光伏老王", "别墅光伏安装实拍案例")
        assert r["account_source"]["account_category"] == "个人光伏内容博主"

    def test_classify_enterprise(self, engine):
        """官方/品牌/公司 → 光伏企业。"""
        r = _run(engine, "正泰安能官方", "家庭光伏安装流程讲解")
        assert r["account_source"]["account_category"] == "光伏企业/品牌/安装公司"

    def test_classify_media(self, engine):
        """科普/知识 → 行业媒体。"""
        r = _run(engine, "光伏知识课堂", "光伏发电原理科普")
        assert r["account_source"]["account_category"] == "行业媒体/科普账号"

    def test_heuristic_fallback(self, engine):
        """无 CSV 匹配时使用启发式分析。"""
        r = _run(engine, "未知光伏账号123", "光伏安装案例")
        assert r["account_source"]["match_type"] == "heuristic"
        assert r["account_source"]["account_category"] != "无法判断"

    def test_pipeline_no_error_with_asa(self, engine):
        """全链路运行不应有错误。"""
        r = _run(engine, "光伏老王", "别墅光伏安装")
        assert "_pipeline_error" not in r
        assert "scoring" in r
        assert "lead" in r
        assert "account_source" in r

    def test_score_range(self, engine):
        """评分应在 0-100 范围内。"""
        r = _run(engine, "光伏老王", "别墅光伏安装")
        asa = r["account_source"]
        assert 0 <= asa["account_authority_score"] <= 100
        assert 0 <= asa["customer_source_score"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
