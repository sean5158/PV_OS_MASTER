"""Phase 2C Inbound 客户主动咨询闭环测试 (V3.0)。

覆盖: OwnAccountRegistry / InboundCommentDetector / AlertEngine /
       FeishuAlertPayload / ContactJourney / 完整 Inbound 数据流。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_phase_2c_inbound.py -v
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

from collector_base import CommentRecord  # noqa: E402
from own_account_registry import (  # noqa: E402
    OwnAccount, OwnAccountRegistry, create_default_own_accounts,
)
from inbound_comment_detector import (  # noqa: E402
    InboundCommentDetector, InboundDetectionResult,
)
from alert_engine import (  # noqa: E402
    Alert, AlertEngine, ContactJourney, FeishuAlertPayload,
)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_registry() -> OwnAccountRegistry:
    """临时自有账号注册表 (含默认数据)。"""
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "own_account_master.csv"
        registry = OwnAccountRegistry(csv_path=csv_path)
        for acct in create_default_own_accounts():
            registry.register(acct)
        yield registry


@pytest.fixture
def tmp_detector(tmp_registry) -> InboundCommentDetector:
    """临时 Inbound Comment Detector。"""
    with tempfile.TemporaryDirectory() as tmp:
        log_csv = Path(tmp) / "inbound_log.csv"
        yield InboundCommentDetector(registry=tmp_registry, log_csv=log_csv)


@pytest.fixture
def tmp_alert_engine() -> AlertEngine:
    """临时 Alert Engine (空数据)。"""
    with tempfile.TemporaryDirectory() as tmp:
        yield AlertEngine(
            alert_csv=Path(tmp) / "alert_log.csv",
            journey_csv=Path(tmp) / "contact_journey.csv",
        )


@pytest.fixture
def sample_own_comment() -> CommentRecord:
    """示例自有账号评论。"""
    return CommentRecord(
        comment_id="cmt_own_test_001",
        platform="douyin",
        content="我家在成都锦江区，别墅想装一套光伏发电系统，能报个价吗？",
        author="成都锦江业主刘先生",
        video_author_id="dy_own_chengdu_solar",
        video_author_name="成都光伏小马哥",
        source_url="https://douyin.com/video/own_v001",
        source_video_title="别墅光伏安装实拍",
        user_id="user_cd_001",
        user_profile_url="https://douyin.com/user/user_cd_001",
        ip_location="四川成都",
        is_own_account=True,
    )


@pytest.fixture
def sample_competitor_comment() -> CommentRecord:
    """示例竞品账号评论。"""
    return CommentRecord(
        comment_id="cmt_comp_test_001",
        platform="douyin",
        content="光伏安装需要多久？我家在重庆渝北区",
        author="重庆业主王先生",
        video_author_id="reg_install_001",
        video_author_name="成都光伏老王",
        source_url="https://douyin.com/video/comp_v001",
        source_video_title="光伏安装过程",
        user_id="user_cq_001",
        user_profile_url="https://douyin.com/user/user_cq_001",
        ip_location="重庆",
        is_own_account=False,
    )


# ══════════════════════════════════════════════════════════════════════
# OwnAccount
# ══════════════════════════════════════════════════════════════════════

class TestOwnAccount:

    def test_defaults(self) -> None:
        acct = OwnAccount(account_id="own_001")
        assert acct.monitor_comments is True
        assert acct.region == "四川"
        assert acct.status == "active"

    def test_to_dict(self) -> None:
        acct = OwnAccount(account_id="own_001", platform="douyin",
                          account_name="测试账号")
        d = acct.to_dict()
        assert d["account_id"] == "own_001"
        assert d["platform"] == "douyin"

    def test_from_dict(self) -> None:
        d = {"account_id": "own_002", "platform": "xiaohongshu",
             "account_name": "小红书测试"}
        acct = OwnAccount.from_dict(d)
        assert acct.platform == "xiaohongshu"

    def test_get_platform_account_ids(self) -> None:
        acct = OwnAccount(
            account_id="own_001",
            platform_account_id="dy_test_123",
            account_url="https://douyin.com/user/dy_test_123",
        )
        ids = acct.get_platform_account_ids()
        assert "dy_test_123" in ids
        assert "https://douyin.com/user/dy_test_123" in ids


# ══════════════════════════════════════════════════════════════════════
# OwnAccountRegistry
# ══════════════════════════════════════════════════════════════════════

class TestOwnAccountRegistry:

    def test_register_and_get(self, tmp_registry) -> None:
        a = tmp_registry.get("own_douyin_001")
        assert a is not None
        assert a.platform == "douyin"
        assert a.account_name == "成都光伏小马哥"

    def test_count(self, tmp_registry) -> None:
        # 默认3个 + 注册
        assert tmp_registry.count() == 3

    def test_count_active(self, tmp_registry) -> None:
        assert tmp_registry.count_active() == 3

    def test_list_all(self, tmp_registry) -> None:
        all_accts = tmp_registry.list_all()
        assert len(all_accts) == 3

    def test_list_by_platform(self, tmp_registry) -> None:
        douyin = tmp_registry.list_by_platform("douyin")
        assert len(douyin) == 2

    def test_list_active(self, tmp_registry) -> None:
        active = tmp_registry.list_active()
        assert len(active) == 3
        # own_douyin_002 的 monitor_comments=False 但仍为 active
        ids = {a.account_id for a in active}
        assert "own_douyin_002" in ids

    def test_update(self, tmp_registry) -> None:
        ok = tmp_registry.update("own_douyin_001", primary_topic="新方向")
        assert ok
        a = tmp_registry.get("own_douyin_001")
        assert a is not None and a.primary_topic == "新方向"

    def test_update_nonexistent(self, tmp_registry) -> None:
        ok = tmp_registry.update("nonexistent", primary_topic="x")
        assert not ok

    def test_delete(self, tmp_registry) -> None:
        ok = tmp_registry.delete("own_douyin_002")
        assert ok
        a = tmp_registry.get("own_douyin_002")
        assert a is not None and a.status == "deprecated"
        assert tmp_registry.count_active() == 2

    def test_is_own_account_by_id(self, tmp_registry) -> None:
        assert tmp_registry.is_own_account("dy_own_chengdu_solar")
        assert not tmp_registry.is_own_account("unknown_competitor")

    def test_is_own_account_by_url(self, tmp_registry) -> None:
        assert tmp_registry.is_own_account("",
            "https://douyin.com/user/dy_own_chengdu_solar")
        assert not tmp_registry.is_own_account("",
            "https://douyin.com/user/unknown")

    def test_create_default_accounts(self) -> None:
        accts = create_default_own_accounts()
        assert len(accts) >= 3
        platforms = {a.platform for a in accts}
        assert "douyin" in platforms
        assert "xiaohongshu" in platforms


# ══════════════════════════════════════════════════════════════════════
# InboundCommentDetector
# ══════════════════════════════════════════════════════════════════════

class TestInboundCommentDetector:

    def test_detect_own_comment(self, tmp_detector, sample_own_comment) -> None:
        result = tmp_detector.detect(sample_own_comment)
        assert result.is_inbound
        assert result.inbound_type == "own_comment"

    def test_detect_competitor_comment(self, tmp_detector, sample_competitor_comment) -> None:
        result = tmp_detector.detect(sample_competitor_comment)
        assert not result.is_inbound
        assert result.inbound_type == "competitor_comment"

    def test_detect_by_is_own_account_field(self, tmp_detector) -> None:
        """即使 video_author_id 不匹配，is_own_account=True 也应检测为 Inbound。"""
        record = CommentRecord(
            comment_id="cmt_x", video_author_id="unknown_id",
            is_own_account=True,
        )
        result = tmp_detector.detect(record)
        assert result.is_inbound

    def test_filter_inbound(self, tmp_detector, sample_own_comment, sample_competitor_comment) -> None:
        inbounds = tmp_detector.filter_inbound(
            [sample_own_comment, sample_competitor_comment])
        assert len(inbounds) == 1
        assert inbounds[0].comment_id == "cmt_own_test_001"

    def test_filter_outbound(self, tmp_detector, sample_own_comment, sample_competitor_comment) -> None:
        outbounds = tmp_detector.filter_outbound(
            [sample_own_comment, sample_competitor_comment])
        assert len(outbounds) == 1
        assert outbounds[0].comment_id == "cmt_comp_test_001"

    def test_mark_own_accounts(self, tmp_detector) -> None:
        records = [
            CommentRecord(comment_id="c1", video_author_id="dy_own_chengdu_solar"),
            CommentRecord(comment_id="c2", video_author_id="unknown"),
            CommentRecord(comment_id="c3", source_url="https://douyin.com/user/dy_own_chengdu_solar"),
        ]
        tmp_detector.mark_own_accounts(records)
        assert records[0].is_own_account is True
        assert records[1].is_own_account is False
        assert records[2].is_own_account is True

    def test_detect_batch(self, tmp_detector, sample_own_comment, sample_competitor_comment) -> None:
        results = tmp_detector.detect_batch([sample_own_comment, sample_competitor_comment])
        assert len(results) == 2
        assert results[0].is_inbound
        assert not results[1].is_inbound

    def test_detection_result_fields(self, tmp_detector, sample_own_comment) -> None:
        result = tmp_detector.detect(sample_own_comment)
        assert result.platform == "douyin"
        assert result.video_author_name == "成都光伏小马哥"
        assert result.comment_user_name == "成都锦江业主刘先生"
        assert result.own_account_id == "own_douyin_001"

    def test_get_stats(self, tmp_detector, sample_own_comment) -> None:
        tmp_detector.detect(sample_own_comment)
        stats = tmp_detector.get_stats()
        assert stats["monitored_own_accounts"] >= 2  # at least own_douyin_001 + own_xhs_001


# ══════════════════════════════════════════════════════════════════════
# Alert Engine — 通知策略
# ══════════════════════════════════════════════════════════════════════

class TestAlertEngineStrategy:

    def test_should_alert_s_level(self, tmp_alert_engine) -> None:
        assert tmp_alert_engine.should_alert("S", is_inbound=True)

    def test_should_alert_a_level(self, tmp_alert_engine) -> None:
        assert tmp_alert_engine.should_alert("A", is_inbound=True)

    def test_should_not_alert_b_level(self, tmp_alert_engine) -> None:
        assert not tmp_alert_engine.should_alert("B", is_inbound=True)

    def test_should_not_alert_c_level(self, tmp_alert_engine) -> None:
        assert not tmp_alert_engine.should_alert("C", is_inbound=True)

    def test_should_not_alert_outbound(self, tmp_alert_engine) -> None:
        assert not tmp_alert_engine.should_alert("S", is_inbound=False)

    def test_notify_level_mapping(self, tmp_alert_engine) -> None:
        assert tmp_alert_engine.get_notify_level("S") == "immediate"
        assert tmp_alert_engine.get_notify_level("A") == "batch"
        assert tmp_alert_engine.get_notify_level("B") == "none"

    def test_response_deadline(self, tmp_alert_engine) -> None:
        assert "24小时" in tmp_alert_engine.get_response_deadline("S")
        assert "48小时" in tmp_alert_engine.get_response_deadline("A")
        assert tmp_alert_engine.get_response_deadline("B") == "-"


# ══════════════════════════════════════════════════════════════════════
# Alert Engine — Alert
# ══════════════════════════════════════════════════════════════════════

class TestAlertEngineAlert:

    def test_create_alert(self, tmp_alert_engine, sample_own_comment) -> None:
        alert = tmp_alert_engine.create_alert(
            sample_own_comment, "S", 92, "四川成都", "PV_LEAD_001")
        assert alert.lead_grade == "S"
        assert alert.lead_score == 92
        assert alert.region == "四川成都"
        assert alert.notify_level == "immediate"
        assert alert.alert_status == "pending"

    def test_alert_unique_ids(self, tmp_alert_engine, sample_own_comment) -> None:
        a1 = tmp_alert_engine.create_alert(sample_own_comment, "S", 90)
        a2 = tmp_alert_engine.create_alert(sample_own_comment, "A", 70)
        assert a1.alert_id != a2.alert_id

    def test_dedup_same_comment(self, tmp_alert_engine, sample_own_comment) -> None:
        alert = tmp_alert_engine.create_alert(sample_own_comment, "S", 90)
        tmp_alert_engine._save_alert(alert)
        assert tmp_alert_engine.is_duplicate("cmt_own_test_001")

    def test_no_dedup_different_comment(self, tmp_alert_engine) -> None:
        assert not tmp_alert_engine.is_duplicate("unknown_comment_id")


# ══════════════════════════════════════════════════════════════════════
# Alert Engine — process_inbound_lead
# ══════════════════════════════════════════════════════════════════════

class TestAlertEngineProcess:

    def test_process_s_lead(self, tmp_alert_engine, sample_own_comment) -> None:
        alert = tmp_alert_engine.process_inbound_lead(
            sample_own_comment, "S", 92, "四川成都", "PV_LEAD_001")
        assert alert is not None
        assert alert.lead_grade == "S"

    def test_process_a_lead(self, tmp_alert_engine, sample_own_comment) -> None:
        alert = tmp_alert_engine.process_inbound_lead(
            sample_own_comment, "A", 72, "四川成都")
        assert alert is not None
        assert alert.notify_level == "batch"

    def test_process_b_lead_no_alert(self, tmp_alert_engine, sample_own_comment) -> None:
        alert = tmp_alert_engine.process_inbound_lead(
            sample_own_comment, "B", 45)
        assert alert is None

    def test_dedup_prevents_duplicate(self, tmp_alert_engine, sample_own_comment) -> None:
        # 第一次应触发
        alert1 = tmp_alert_engine.process_inbound_lead(
            sample_own_comment, "S", 90)
        assert alert1 is not None
        # 第二次应被抑制
        alert2 = tmp_alert_engine.process_inbound_lead(
            sample_own_comment, "S", 90)
        assert alert2 is None

    def test_fresh_comment_not_deduped(self, tmp_alert_engine) -> None:
        record = CommentRecord(comment_id="cmt_unique_new", platform="douyin",
                               content="新评论", author="新用户")
        alert = tmp_alert_engine.process_inbound_lead(record, "S", 88)
        assert alert is not None


# ══════════════════════════════════════════════════════════════════════
# FeishuAlertPayload
# ══════════════════════════════════════════════════════════════════════

class TestFeishuAlertPayload:

    def test_to_feishu_message_s_level(self) -> None:
        payload = FeishuAlertPayload(
            platform="douyin", video_title="别墅光伏实拍",
            customer_name="刘先生", comment_content="能报价吗",
            region="四川成都", lead_grade="S", lead_score=92,
            alert_time="2026-07-20 10:30",
            user_profile_url="https://douyin.com/user/xxx",
            comment_url="https://douyin.com/video/xxx",
            video_url="https://douyin.com/video/xxx",
            response_deadline="24小时内",
        )
        msg = payload.to_feishu_message()
        assert msg["msg_type"] == "interactive"
        assert msg["card"]["header"]["template"] == "red"
        assert len(msg["card"]["elements"]) >= 5

    def test_to_feishu_message_a_level(self) -> None:
        payload = FeishuAlertPayload(
            lead_grade="A", lead_score=65,
            response_deadline="48小时内",
        )
        msg = payload.to_feishu_message()
        assert msg["card"]["header"]["template"] == "blue"

    def test_to_text_summary(self) -> None:
        payload = FeishuAlertPayload(
            platform="douyin", video_title="测试视频",
            customer_name="张三", comment_content="怎么收费",
            region="重庆", lead_grade="S", lead_score=88,
            alert_time="2026-07-20 14:00",
            user_profile_url="https://douyin.com/user/z3",
            comment_url="https://douyin.com/video/v1",
            video_url="https://douyin.com/video/v1",
            response_deadline="24小时内",
        )
        text = payload.to_text_summary()
        assert "张三" in text
        assert "S级 (88分)" in text
        assert "24小时" in text
        assert "https://douyin.com/user/z3" in text

    def test_alert_to_payload_roundtrip(self, tmp_alert_engine, sample_own_comment) -> None:
        alert = tmp_alert_engine.create_alert(sample_own_comment, "S", 95)
        payload = tmp_alert_engine.build_feishu_payload(alert)
        assert payload.lead_grade == "S"
        assert payload.customer_name == sample_own_comment.author


# ══════════════════════════════════════════════════════════════════════
# ContactJourney
# ══════════════════════════════════════════════════════════════════════

class TestContactJourney:

    def test_create_journey(self, tmp_alert_engine) -> None:
        journey = tmp_alert_engine.create_journey(
            "PV_LEAD_001", "user_001", "刘先生", "douyin",
            "想装光伏", "https://douyin.com/video/v1",
            "https://douyin.com/user/u1",
        )
        assert journey.status == "pending"
        assert journey.lead_id == "PV_LEAD_001"

    def test_full_status_flow(self, tmp_alert_engine) -> None:
        journey = tmp_alert_engine.create_journey(
            "PV_LEAD_002", "user_002", "test", "douyin")
        jid = journey.journey_id

        assert tmp_alert_engine.update_journey(jid, "contacted")
        j = tmp_alert_engine.get_journey(jid)
        assert j.status == "contacted"
        assert j.first_contact_at != ""

        assert tmp_alert_engine.update_journey(jid, "replied")
        assert tmp_alert_engine.update_journey(jid, "wechat_added")
        assert tmp_alert_engine.update_journey(jid, "site_visit")
        assert tmp_alert_engine.update_journey(jid, "deal_closed")

        j = tmp_alert_engine.get_journey(jid)
        assert j.status == "deal_closed"

    def test_no_backward_transition(self, tmp_alert_engine) -> None:
        journey = tmp_alert_engine.create_journey("PV_LEAD_003", "user_003", "test", "douyin")
        tmp_alert_engine.update_journey(journey.journey_id, "contacted")
        assert not tmp_alert_engine.update_journey(journey.journey_id, "pending")

    def test_no_need_transition(self, tmp_alert_engine) -> None:
        journey = tmp_alert_engine.create_journey("PV_LEAD_004", "user_004", "test", "douyin")
        assert tmp_alert_engine.update_journey(journey.journey_id, "no_need")
        j = tmp_alert_engine.get_journey(journey.journey_id)
        assert j.status == "no_need"

    def test_get_journey_by_lead(self, tmp_alert_engine) -> None:
        tmp_alert_engine.create_journey("PV_LEAD_005", "user_005", "test", "douyin")
        j = tmp_alert_engine.get_journey_by_lead("PV_LEAD_005")
        assert j is not None

    def test_list_active(self, tmp_alert_engine) -> None:
        j1 = tmp_alert_engine.create_journey("PV_LEAD_006", "u6", "test", "douyin")
        j2 = tmp_alert_engine.create_journey("PV_LEAD_007", "u7", "test", "douyin")
        tmp_alert_engine.update_journey(j2.journey_id, "deal_closed")

        active = tmp_alert_engine.list_active_journeys()
        assert len(active) == 1

    def test_list_pending(self, tmp_alert_engine) -> None:
        tmp_alert_engine.create_journey("PV_LEAD_008", "u8", "test", "douyin")
        pending = tmp_alert_engine.list_pending_journeys()
        assert len(pending) == 1

    def test_save_and_reload(self, tmp_alert_engine) -> None:
        j = tmp_alert_engine.create_journey("PV_LEAD_009", "u9", "持久化测试", "douyin",
            source_url="https://douyin.com/video/persist",
            user_profile_url="https://douyin.com/user/persist")
        loaded = tmp_alert_engine.get_journey(j.journey_id)
        assert loaded is not None
        assert loaded.user_name == "持久化测试"
        assert loaded.source_url == "https://douyin.com/video/persist"


# ══════════════════════════════════════════════════════════════════════
# 集成测试: 完整 Inbound 数据流
# ══════════════════════════════════════════════════════════════════════

class TestInboundIntegration:

    def test_full_inbound_pipeline(
        self, tmp_registry, tmp_alert_engine,
        sample_own_comment
    ) -> None:
        """完整 Inbound 流程:
        CommentRecord → Detection → Alert → ContactJourney
        """
        with tempfile.TemporaryDirectory() as tmp:
            log_csv = Path(tmp) / "inbound_log.csv"
            detector = InboundCommentDetector(registry=tmp_registry, log_csv=log_csv)

            # Step 1: 标记自有账号评论
            detector.mark_own_accounts([sample_own_comment])

            # Step 2: 检测为 Inbound
            result = detector.detect(sample_own_comment)
            assert result.is_inbound
            assert result.inbound_type == "own_comment"

            # Step 3: 判断是否需要提醒
            assert tmp_alert_engine.should_alert("S", is_inbound=True)

            # Step 4: 创建 Alert
            alert = tmp_alert_engine.process_inbound_lead(
                sample_own_comment, "S", 92, "四川成都", "PV_LEAD_INT_001")
            assert alert is not None

            # Step 5: 构建飞书通知
            payload = tmp_alert_engine.build_feishu_payload(alert)
            feishu_msg = payload.to_feishu_message()
            assert feishu_msg["msg_type"] == "interactive"

            # Step 6: 创建触达旅程
            journey = tmp_alert_engine.create_journey(
                "PV_LEAD_INT_001", sample_own_comment.user_id,
                sample_own_comment.author, sample_own_comment.platform,
                sample_own_comment.content, sample_own_comment.source_url,
                sample_own_comment.user_profile_url,
            )
            assert journey.status == "pending"

    def test_outbound_not_alerted(
        self, tmp_detector, tmp_alert_engine,
        sample_competitor_comment
    ) -> None:
        """竞品评论不应触发 Inbound Alert。"""
        result = tmp_detector.detect(sample_competitor_comment)
        assert not result.is_inbound
        assert not tmp_alert_engine.should_alert("S", is_inbound=False)

    def test_b_level_inbound_no_alert(
        self, tmp_detector, tmp_alert_engine,
        sample_own_comment
    ) -> None:
        """B级 Inbound 不触发提醒，进入培育池。"""
        alert = tmp_alert_engine.process_inbound_lead(sample_own_comment, "B", 45)
        assert alert is None


# ══════════════════════════════════════════════════════════════════════
# 边界条件
# ══════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_empty_registry(self) -> None:
        """空注册表应正常工作。"""
        with tempfile.TemporaryDirectory() as tmp:
            reg = OwnAccountRegistry(csv_path=Path(tmp) / "empty.csv")
            assert reg.count() == 0
            assert reg.count_active() == 0
            assert not reg.is_own_account("any_id")

    def test_detector_no_registry(self) -> None:
        """没有注册任何自有账号时，Detector 正常处理。"""
        with tempfile.TemporaryDirectory() as tmp:
            reg_csv = Path(tmp) / "empty_reg.csv"
            reg = OwnAccountRegistry(csv_path=reg_csv)
            log_csv = Path(tmp) / "empty_log.csv"
            detector = InboundCommentDetector(registry=reg, log_csv=log_csv)
            record = CommentRecord(comment_id="c1", video_author_id="any")
            result = detector.detect(record)
            assert not result.is_inbound

    def test_record_missing_fields(self, tmp_detector) -> None:
        """字段缺失的 CommentRecord 不应崩溃。"""
        record = CommentRecord(comment_id="c_min")
        result = tmp_detector.detect(record)
        assert not result.is_inbound

    def test_stats_consistency(self, tmp_alert_engine) -> None:
        """初始统计应为 0。"""
        stats = tmp_alert_engine.get_stats()
        assert stats["total_alerts"] == 0
        assert stats["total_journeys"] == 0
        assert stats["pending_journeys"] == 0
        assert stats["active_journeys"] == 0

    def test_update_nonexistent_journey(self, tmp_alert_engine) -> None:
        """更新不存在的旅程应返回 False。"""
        assert not tmp_alert_engine.update_journey("nonexistent", "contacted")

    def test_invalid_status_transition(self) -> None:
        """无效状态被拒绝。"""
        j = ContactJourney(journey_id="test", status="pending")
        assert not j.transition_to("invalid_status")


# ══════════════════════════════════════════════════════════════════════
# 数据流验证 (模拟 Pipeline 集成)
# ══════════════════════════════════════════════════════════════════════

class TestPipelineIntegration:

    def test_comment_record_to_pipeline_event(self) -> None:
        """CommentRecord.to_pipeline_event 保留 is_own_account。"""
        record = CommentRecord(
            comment_id="cmt_pipe_001", platform="douyin",
            content="测试评论", author="测试用户",
            is_own_account=True,
            user_id="u_pipe_001",
            user_profile_url="https://douyin.com/user/u_pipe_001",
        )
        event = record.to_pipeline_event()
        assert event["is_own_account"] is True
        assert event["user_id"] == "u_pipe_001"
        assert "user_profile_url" in event

    def test_pipeline_routing_by_is_own_account(self) -> None:
        """Pipeline 可根据 is_own_account 分流出 Inbound/Outbound。"""
        records = [
            CommentRecord(comment_id="c1", is_own_account=True, content="S级评论"),
            CommentRecord(comment_id="c2", is_own_account=False, content="竞品评论"),
            CommentRecord(comment_id="c3", is_own_account=True, content="A级评论"),
        ]
        inbound = [r for r in records if r.is_own_account]
        outbound = [r for r in records if not r.is_own_account]
        assert len(inbound) == 2
        assert len(outbound) == 1
        assert inbound[0].comment_id == "c1"
        assert outbound[0].comment_id == "c2"

    def test_feishu_payload_json_serializable(self, tmp_alert_engine, sample_own_comment) -> None:
        """飞书 Payload 应可直接 JSON 序列化。"""
        alert = tmp_alert_engine.create_alert(sample_own_comment, "S", 95)
        payload = tmp_alert_engine.build_feishu_payload(alert)
        msg = payload.to_feishu_message()
        # 应不抛出异常
        json_str = json.dumps(msg, ensure_ascii=False)
        assert len(json_str) > 100
        # 应能反序列化
        reloaded = json.loads(json_str)
        assert reloaded["msg_type"] == "interactive"
