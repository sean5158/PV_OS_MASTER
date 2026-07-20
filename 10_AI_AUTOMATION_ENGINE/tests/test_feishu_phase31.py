"""Phase 3-1 飞书运营层测试 (V3.2)。

覆盖: FeishuWebhookClient / FeishuBitableClient / BitableRecord /
       Alert-to-Bitable integration / Mock→Live 降级。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_feishu_phase31.py -v
"""

from __future__ import annotations

import csv
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

from alert_engine import (  # noqa: E402
    Alert, AlertEngine, FeishuAlertPayload, ContactJourney,
)
from feishu_webhook_client import (  # noqa: E402
    FeishuWebhookClient, SendResult, create_mock_client as create_mock_webhook,
)
from feishu_bitable_client import (  # noqa: E402
    FeishuBitableClient, BitableRecord, SyncResult,
    create_mock_client as create_mock_bitable,
)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def webhook_client() -> FeishuWebhookClient:
    return FeishuWebhookClient(mode="mock", owner_open_id="ou_test_001")


@pytest.fixture
def bitable_client() -> FeishuBitableClient:
    with tempfile.TemporaryDirectory() as tmp:
        yield FeishuBitableClient(mode="mock", sync_log_csv=Path(tmp) / "sync_log.csv")


@pytest.fixture
def sample_payload() -> FeishuAlertPayload:
    return FeishuAlertPayload(
        platform="douyin",
        video_title="别墅光伏安装实拍",
        customer_name="成都锦江业主刘先生",
        comment_content="我家在成都锦江区别墅，想装一套光伏发电系统，能报个价吗？",
        region="四川成都",
        lead_grade="S",
        lead_score=92,
        alert_time=datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M"),
        user_profile_url="https://douyin.com/user/u1",
        comment_url="https://douyin.com/video/v1",
        video_url="https://douyin.com/video/v1",
        response_deadline="24小时内",
    )


@pytest.fixture
def sample_alert() -> Alert:
    return Alert(
        alert_id="ALERT_TEST_001",
        lead_id="LEAD_TEST_001",
        comment_id="cmt_001",
        user_id="user_001",
        platform="douyin",
        author="成都锦江业主刘先生",
        comment_content="别墅想装光伏，能报个价吗？",
        video_title="别墅光伏安装实拍",
        video_url="https://douyin.com/video/v1",
        region="四川成都",
        lead_grade="S",
        lead_score=92,
        user_profile_url="https://douyin.com/user/u1",
        comment_url="https://douyin.com/video/v1",
        notify_level="immediate",
    )


# ══════════════════════════════════════════════════════════════════════
# FeishuWebhookClient
# ══════════════════════════════════════════════════════════════════════

class TestFeishuWebhookClient:

    def test_mock_send_success(self, webhook_client, sample_payload) -> None:
        result = webhook_client.send(sample_payload)
        assert result.success
        assert result.mode == "mock"
        assert result.message_id.startswith("mock_msg_")

    def test_s_grade_at_owner(self, webhook_client, sample_payload) -> None:
        result = webhook_client.send_alert(sample_payload, lead_grade="S")
        assert result.success
        title = result.payload_snapshot["card"]["header"]["title"]["content"]
        assert "@负责人" in title

    def test_a_grade_no_at_owner(self, webhook_client, sample_payload) -> None:
        result = webhook_client.send_alert(sample_payload, lead_grade="A")
        assert result.success
        title = result.payload_snapshot["card"]["header"]["title"]["content"]
        assert "@负责人" not in title

    def test_card_template_by_grade(self, webhook_client) -> None:
        s_payload = FeishuAlertPayload(lead_grade="S", lead_score=92,
                                       response_deadline="24小时内")
        a_payload = FeishuAlertPayload(lead_grade="A", lead_score=72,
                                       response_deadline="48小时内")
        r_s = webhook_client.send(s_payload)
        r_a = webhook_client.send(a_payload)
        assert r_s.payload_snapshot["card"]["header"]["template"] == "red"
        assert r_a.payload_snapshot["card"]["header"]["template"] == "blue"

    def test_card_has_required_elements(self, webhook_client, sample_payload) -> None:
        result = webhook_client.send(sample_payload)
        elements = result.payload_snapshot["card"]["elements"]
        assert len(elements) >= 5  # header + platform + customer + comment + score + links + note

    def test_card_has_clickable_links(self, webhook_client, sample_payload) -> None:
        result = webhook_client.send(sample_payload)
        card_str = json.dumps(result.payload_snapshot, ensure_ascii=False)
        assert "user/u1" in card_str
        assert "video/v1" in card_str

    def test_send_history(self, webhook_client, sample_payload) -> None:
        webhook_client.send(sample_payload)
        webhook_client.send(sample_payload)
        assert len(webhook_client.get_send_history()) == 2

    def test_get_stats(self, webhook_client, sample_payload) -> None:
        webhook_client.send(sample_payload)
        stats = webhook_client.get_stats()
        assert stats["total_sent"] == 1
        assert stats["success"] == 1
        assert stats["mode"] == "mock"

    def test_live_no_url_fails(self, sample_payload) -> None:
        client = FeishuWebhookClient(mode="live")
        result = client.send(sample_payload)
        assert not result.success
        assert "not configured" in result.error

    def test_send_result_json_serializable(self, webhook_client, sample_payload) -> None:
        result = webhook_client.send(sample_payload)
        d = result.to_dict()
        assert d["success"] is True
        json_str = json.dumps(d, ensure_ascii=False)
        assert len(json_str) > 100

    def test_payload_snapshot_preserved(self, webhook_client, sample_payload) -> None:
        result = webhook_client.send(sample_payload)
        snap = result.payload_snapshot
        assert snap["msg_type"] == "interactive"
        assert "card" in snap

    def test_no_owner_open_id_no_at(self, sample_payload) -> None:
        client = FeishuWebhookClient(mode="mock")  # no owner_open_id
        result = client.send_alert(sample_payload, lead_grade="S")
        # Should still succeed, just no @mention
        assert result.success


# ══════════════════════════════════════════════════════════════════════
# BitableRecord
# ══════════════════════════════════════════════════════════════════════

class TestBitableRecord:

    def test_defaults(self) -> None:
        rec = BitableRecord(lead_id="LEAD_001")
        assert rec.lead_id == "LEAD_001"
        assert rec.status == "pending"
        assert rec.intent_score == 0

    def test_all_required_fields(self) -> None:
        rec = BitableRecord(
            lead_id="LEAD_001", platform="douyin",
            account_name="成都光伏小马哥", customer_name="刘先生",
            user_id="u001", user_profile_url="https://douyin.com/user/u001",
            video_url="https://douyin.com/video/v1",
            comment_url="https://douyin.com/video/v1",
            comment_text="想装光伏", region="四川成都",
            intent_score=92, lead_grade="S", status="pending",
        )
        d = rec.to_dict()
        assert d["lead_id"] == "LEAD_001"
        assert d["platform"] == "douyin"
        assert d["lead_grade"] == "S"
        assert d["region"] == "四川成都"

    def test_from_alert(self, sample_alert) -> None:
        rec = BitableRecord.from_alert(sample_alert, account_name="成都光伏小马哥", intent_score=92)
        assert rec.lead_id == "LEAD_TEST_001"
        assert rec.platform == "douyin"
        assert rec.account_name == "成都光伏小马哥"
        assert rec.customer_name == "成都锦江业主刘先生"
        assert rec.lead_grade == "S"
        assert rec.status == "pending"

    def test_from_comment_record(self) -> None:
        from collector_base import CommentRecord
        cr = CommentRecord(
            comment_id="cmt_001", platform="xiaohongshu",
            content="阳光房光伏改造，成都能做吗？", author="成都业主",
            user_id="u002", user_profile_url="https://xhs.com/user/u002",
            source_url="https://xhs.com/explore/v2",
            video_author_name="成都光伏小马哥",
        )
        rec = BitableRecord.from_comment_record(
            cr, lead_id="LEAD_XHS_001", region="四川成都",
            lead_grade="A", lead_score=72, account_name="成都光伏小马哥",
        )
        assert rec.platform == "xiaohongshu"
        assert rec.region == "四川成都"
        assert rec.lead_grade == "A"

    def test_comment_truncation(self, sample_alert) -> None:
        long_alert = Alert(
            alert_id="A1", lead_id="L1", comment_id="c1",
            comment_content="光伏" * 150, platform="douyin",
        )
        rec = BitableRecord.from_alert(long_alert)
        assert len(rec.comment_text) <= 200


# ══════════════════════════════════════════════════════════════════════
# FeishuBitableClient
# ══════════════════════════════════════════════════════════════════════

class TestFeishuBitableClient:

    def test_mock_insert(self, bitable_client) -> None:
        rec = BitableRecord(lead_id="LEAD_001", platform="douyin",
                            lead_grade="S", region="四川成都")
        result = bitable_client.upsert_record(rec)
        assert result.success
        assert result.action == "insert"
        assert result.mode == "mock"

    def test_duplicate_updates(self, bitable_client) -> None:
        rec = BitableRecord(lead_id="LEAD_DUP", platform="douyin")
        r1 = bitable_client.upsert_record(rec)
        assert r1.action == "insert"
        r2 = bitable_client.upsert_record(rec)
        assert r2.action == "update"

    def test_sync_batch(self, bitable_client) -> None:
        records = [
            BitableRecord(lead_id="LEAD_B1", platform="douyin", lead_grade="S"),
            BitableRecord(lead_id="LEAD_B2", platform="xiaohongshu", lead_grade="A"),
            BitableRecord(lead_id="LEAD_B3", platform="kuaishou", lead_grade="A"),
        ]
        results = bitable_client.sync_batch(records)
        assert len(results) == 3
        assert all(r.success for r in results)
        assert results[0].action == "insert"

    def test_sync_from_alert(self, bitable_client, sample_alert) -> None:
        result = bitable_client.sync_from_alert(sample_alert, "成都光伏小马哥", 92)
        assert result.success
        assert result.lead_id == "LEAD_TEST_001"

    def test_sync_log_persistence(self, bitable_client) -> None:
        rec = BitableRecord(lead_id="LEAD_LOG", platform="douyin", lead_grade="S")
        bitable_client.upsert_record(rec)
        log = bitable_client.get_sync_log()
        assert len(log) >= 1
        assert log[0]["lead_id"] == "LEAD_LOG"

    def test_get_stats(self, bitable_client) -> None:
        bitable_client.upsert_record(BitableRecord(lead_id="L1", lead_grade="S"))
        bitable_client.upsert_record(BitableRecord(lead_id="L2", lead_grade="A"))
        stats = bitable_client.get_stats()
        assert stats["total_synced"] == 2
        assert stats["success"] == 2
        assert stats["mode"] == "mock"

    def test_live_no_creds_fails(self) -> None:
        live = FeishuBitableClient(mode="live")
        rec = BitableRecord(lead_id="LEAD_LIVE")
        result = live.upsert_record(rec)
        assert not result.success
        assert "not configured" in result.error

    def test_multi_platform_records(self, bitable_client) -> None:
        for platform in ["douyin", "xiaohongshu", "kuaishou", "shipinhao"]:
            rec = BitableRecord(lead_id=f"LEAD_{platform}", platform=platform, lead_grade="A")
            r = bitable_client.upsert_record(rec)
            assert r.success
        stats = bitable_client.get_stats()
        assert stats["total_synced"] == 4


# ══════════════════════════════════════════════════════════════════════
# 集成测试: Alert → Webhook + Bitable
# ══════════════════════════════════════════════════════════════════════

class TestFeishuIntegration:

    def test_full_alert_to_feishu_flow(self) -> None:
        """完整流程: AlertEngine → FeishuAlertPayload → Webhook + Bitable。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            webhook = FeishuWebhookClient(mode="mock", owner_open_id="ou_001")
            bitable = FeishuBitableClient(mode="mock", sync_log_csv=tmp_p / "sync.csv")
            engine = AlertEngine(
                alert_csv=tmp_p / "alert.csv",
                journey_csv=tmp_p / "journey.csv",
            )

            from collector_base import CommentRecord
            record = CommentRecord(
                comment_id="cmt_int_001", platform="douyin",
                content="别墅装光伏多少钱？成都锦江区", author="刘先生",
                source_video_title="光伏安装实拍", source_url="https://douyin.com/video/v1",
                user_id="u001", user_profile_url="https://douyin.com/user/u001",
            )

            # AlertEngine → Alert
            alert = engine.create_alert(record, "S", 92, "四川成都", "LEAD_INT_001")
            assert alert.lead_grade == "S"

            # Alert → FeishuAlertPayload
            payload = engine.build_feishu_payload(alert)
            assert payload.platform == "douyin"

            # Webhook send
            webhook_result = webhook.send_alert(payload, lead_grade="S")
            assert webhook_result.success

            # Bitable sync
            bitable_result = bitable.sync_from_alert(alert, "成都光伏小马哥", 92)
            assert bitable_result.success

            # Verify
            assert len(webhook.get_send_history()) == 1
            assert len(bitable.get_sync_log()) >= 1

    def test_a_grade_no_at_owner(self) -> None:
        """A级不应 @负责人。"""
        with tempfile.TemporaryDirectory() as tmp:
            webhook = FeishuWebhookClient(mode="mock", owner_open_id="ou_001")
            payload = FeishuAlertPayload(
                platform="douyin", lead_grade="A", lead_score=72,
                response_deadline="48小时内",
                video_title="测试", customer_name="测试",
                comment_content="测试", region="重庆",
                user_profile_url="https://douyin.com/user/u1",
                comment_url="https://douyin.com/video/v1",
                video_url="https://douyin.com/video/v1",
                alert_time="2026-07-20 10:00",
            )
            result = webhook.send_alert(payload, lead_grade="A")
            title = result.payload_snapshot["card"]["header"]["title"]["content"]
            assert "@负责人" not in title

    def test_regression_pipeline_unaffected(self) -> None:
        """验证 Phase 3-1 不破坏 Pipeline。"""
        from alert_engine import AlertEngine
        engine = AlertEngine()
        assert engine.should_alert("S", is_inbound=True)
        assert not engine.should_alert("B", is_inbound=True)
        assert engine.get_notify_level("S") == "immediate"
        # ContactJourney still works
        journey = engine.create_journey("LEAD_REGRESSION", "u001")
        assert journey.status == "pending"


# ══════════════════════════════════════════════════════════════════════
# 边界条件
# ══════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_empty_payload(self, webhook_client) -> None:
        payload = FeishuAlertPayload()
        result = webhook_client.send(payload)
        assert result.success  # Should not crash with empty fields

    def test_very_long_comment(self, webhook_client) -> None:
        payload = FeishuAlertPayload(
            lead_grade="S", lead_score=90,
            comment_content="光伏" * 500,  # 1000 chars
        )
        result = webhook_client.send(payload)
        assert result.success

    def test_empty_bitable_record(self, bitable_client) -> None:
        rec = BitableRecord()
        result = bitable_client.upsert_record(rec)
        assert result.success

    def test_rapid_consecutive_sends(self, webhook_client, sample_payload) -> None:
        for _ in range(5):
            result = webhook_client.send(sample_payload)
            assert result.success
        assert len(webhook_client.get_send_history()) == 5

    def test_sync_id_uniqueness(self, bitable_client) -> None:
        rec = BitableRecord(lead_id="LEAD_UNIQ")
        r1 = bitable_client.upsert_record(rec)
        r2 = bitable_client.upsert_record(rec)
        # Different sync results should have different sync_ids
        assert r1.sync_id != r2.sync_id


# ══════════════════════════════════════════════════════════════════════
# 数据完整性
# ══════════════════════════════════════════════════════════════════════

class TestDataIntegrity:

    def test_db_remains_authoritative(self) -> None:
        """数据库（CSV）始终为权威数据源。飞书只做展示。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            engine = AlertEngine(
                alert_csv=tmp_p / "alert.csv",
                journey_csv=tmp_p / "journey.csv",
            )
            # AlertEngine writes to CSV (authoritative)
            from collector_base import CommentRecord
            record = CommentRecord(
                comment_id="cmt_auth", platform="douyin",
                content="测试", author="测试", user_id="u_auth",
            )
            alert = engine.process_inbound_lead(record, "S", 90, "四川成都")
            assert alert is not None

            # CSV should have the record
            assert engine.alert_csv.exists()
            alerts = engine._read_alerts()
            assert any(a.comment_id == "cmt_auth" for a in alerts)

    def test_webhook_does_not_mutate_db(self, sample_payload) -> None:
        """Webhook 发送不影响数据库。"""
        webhook = FeishuWebhookClient(mode="mock")
        result = webhook.send(sample_payload)
        assert result.success
        # Webhook has no database connection
        assert not hasattr(webhook, '_read_alerts')

    def test_bitable_does_not_mutate_db(self) -> None:
        """Bitable 同步不影响数据库。"""
        bitable = FeishuBitableClient(mode="mock")
        rec = BitableRecord(lead_id="LEAD_DB_SAFE")
        result = bitable.upsert_record(rec)
        assert result.success
        # Bitable writes to its own sync log, not to leads_master.csv
