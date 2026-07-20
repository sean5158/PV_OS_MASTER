"""Integration tests for PV_OS automation engine.

Run::

    cd PV_OS_MASTER
    python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_pipeline.py -v
"""

from __future__ import annotations

import json
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


@pytest.fixture
def sample_comment() -> dict:
    path = Path(__file__).parent / "fixtures" / "sample_comment.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# test cases
# ---------------------------------------------------------------------------

def test_workflow_loads(engine: Engine) -> None:
    """Verify the YAML workflow parses successfully."""
    assert engine.name == "comment_to_lead_pipeline"
    assert len(engine.steps) == 10


def test_s_grade_villa(engine: Engine) -> None:
    """Villa + quote request + install intent → S grade."""
    comment = {
        "id": "test_S_001",
        "platform": "douyin",
        "content": "我家在成都郊区别墅，想装一套光伏系统，能报个价吗？电话联系138xxxx",
        "author": "高意向用户",
        "create_time": "2026-07-12 10:00:00",
        "ip_location": "四川成都",
    }
    result = engine.run_single(comment)

    assert result["scoring"]["lead_grade"] == "S"
    assert result["scoring"]["total_score"] >= 80
    assert result["scoring"]["contact_intent"] is True
    assert result["scoring"]["urgency"] == "high"
    assert result["lead"]["status"] == "new"
    assert "lead_id" in result["lead"]
    assert result["lead"]["lead_grade"] == "S"
    # S-grade should generate follow-up
    assert "follow_up" in result
    assert result["follow_up"]["action"] == "电话联系"


def test_a_grade_rural(engine: Engine) -> None:
    """Rural self-built + price inquiry → S grade (intent model L3)."""
    comment = {
        "id": "test_A_001",
        "platform": "douyin",
        "content": "农村自建房想装光伏发电，大概多少钱？有补贴吗",
        "author": "农村用户",
        "create_time": "2026-07-10 14:00:00",
        "ip_location": "重庆",
    }
    result = engine.run_single(comment)

    assert result["scoring"]["lead_grade"] == "S"
    assert result["scoring"]["total_score"] >= 80
    assert result["scoring"]["urgency"] == "high"
    assert result["analysis"]["housing_type"] == "普通住宅"  # intent model: 农村→普通住宅, scoring handles diff
    # A-grade should also generate follow-up
    assert "follow_up" in result


def test_b_grade_curious(engine: Engine) -> None:
    """Curious but has inquiry signals → A grade (intent model L2)."""
    comment = {
        "id": "test_B_001",
        "platform": "xiaohongshu",
        "content": "光伏发电靠谱吗？想了解一下",
        "author": "观望用户",
        "create_time": "2026-07-01 09:00:00",
        "ip_location": "贵州贵阳",
    }
    result = engine.run_single(comment)

    assert result["scoring"]["lead_grade"] == "A"
    assert 60 <= result["scoring"]["total_score"] < 80
    assert result["scoring"]["contact_intent"] is True
    # A grade → follow-up generated
    assert "follow_up" in result


def test_pipeline_no_error(engine: Engine) -> None:
    """All 8 steps should complete without _pipeline_error marker."""
    comment = {
        "id": "test_noerr",
        "platform": "douyin",
        "content": "别墅想装光伏，报价多少？",
        "author": "test",
        "create_time": "2026-07-13 10:00:00",
        "ip_location": "四川成都",
    }
    result = engine.run_single(comment)
    assert "_pipeline_error" not in result
    assert "scoring" in result
    assert "lead" in result


def test_crm_output_files_exist(engine: Engine) -> None:
    """After running S + A + B comments, the CRM CSV files should exist."""
    comments = [
        {"id": "cat_S", "platform": "douyin", "content": "别墅光伏安装报价联系电话",
         "author": "x", "create_time": "2026-07-13 10:00:00", "ip_location": "四川成都"},
        {"id": "cat_B", "platform": "douyin", "content": "光伏了解一下",
         "author": "y", "create_time": "2026-07-01 10:00:00", "ip_location": "北京"},
    ]
    for c in comments:
        engine.run_single(c)

    crm_root = PROJECT_ROOT / "05_CUSTOMER_CRM"
    assert (crm_root / "leads" / "hot" / "hot_leads.csv").exists()
    assert (crm_root / "leads" / "nurture_pool.csv").exists()
    assert (crm_root / "leads" / "comment_asset_library.csv").exists()
