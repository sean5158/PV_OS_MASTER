"""DouyinLiveCollector 测试 (P2-3 第一阶段)。

覆盖: 架构验证 / Mock 降级 / Live 模式 / 字段映射 / 业务边界 / 回归。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_douyin_live_collector.py -v
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ENGINE_ROOT))

from collector_base import CommentRecord, BaseCollector  # noqa: E402
from live_collector_base import LiveCollectorBase, RateLimiter  # noqa: E402
from douyin_live_collector import (  # noqa: E402
    DouyinLiveCollector,
    DOUYIN_MOCK_VIDEOS,
    DOUYIN_MOCK_COMMENTS,
)
from platform_adapter import PlatformAdapterManager  # noqa: E402
from engine import Engine  # noqa: E402

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_collector() -> DouyinLiveCollector:
    """无凭证 → Mock 降级。"""
    return DouyinLiveCollector(credentials={})


@pytest.fixture
def live_collector() -> DouyinLiveCollector:
    """有凭证 → Live 模式 (API 未实现，但仍启用)。"""
    return DouyinLiveCollector(credentials={"cookie": "test_session"})


@pytest.fixture
def engine() -> Engine:
    wf = PROJECT_ROOT / "10_AI_AUTOMATION_ENGINE" / "workflows" / "comment_to_lead_pipeline.yml"
    return Engine(wf)


# ══════════════════════════════════════════════════════════════════════
# 架构验证
# ══════════════════════════════════════════════════════════════════════

class TestArchitecture:

    def test_extends_live_collector_base(self) -> None:
        assert issubclass(DouyinLiveCollector, LiveCollectorBase)

    def test_extends_base_collector(self) -> None:
        assert issubclass(DouyinLiveCollector, BaseCollector)

    def test_connector_mode_is_live(self, live_collector: DouyinLiveCollector) -> None:
        assert live_collector.connector_mode == "live"

    def test_platform_name_is_douyin(self, mock_collector: DouyinLiveCollector) -> None:
        assert mock_collector.platform_name == "douyin"

    def test_has_rate_limiter(self, mock_collector: DouyinLiveCollector) -> None:
        assert isinstance(mock_collector.rate_limiter, RateLimiter)

    def test_has_session(self, mock_collector: DouyinLiveCollector) -> None:
        assert mock_collector.session is not None
        assert mock_collector.session.platform == "douyin"

    def test_all_abstract_methods_implemented(self, mock_collector: DouyinLiveCollector) -> None:
        """三个抽象方法全部实现。"""
        # _fetch_video_list
        videos = mock_collector._fetch_video_list("acc", "", 3)
        assert isinstance(videos, list)
        # _fetch_comments
        comments = mock_collector._fetch_comments("dy_video_001", "", 2)
        assert isinstance(comments, list)
        # _parse_to_record
        record = mock_collector._parse_to_record(comments[0])
        assert isinstance(record, CommentRecord)


# ══════════════════════════════════════════════════════════════════════
# Mock 降级测试
# ══════════════════════════════════════════════════════════════════════

class TestMockFallback:

    def test_no_credentials_falls_back(self, mock_collector: DouyinLiveCollector) -> None:
        assert mock_collector._api_available is False

    def test_empty_credentials_falls_back(self) -> None:
        c = DouyinLiveCollector(credentials={})
        assert c._api_available is False

    def test_mock_mode_collects_records(self, mock_collector: DouyinLiveCollector) -> None:
        records = mock_collector.collect(account_id="test", max_count=10)
        assert len(records) >= 5  # 7 条 Mock 评论
        assert all(isinstance(r, CommentRecord) for r in records)
        assert all(r.platform == "douyin" for r in records)

    def test_mock_video_list_has_expected_topics(self, mock_collector: DouyinLiveCollector) -> None:
        videos = mock_collector._fetch_video_list_mock("acc", 10)
        topics = {v["topic"] for v in videos}
        assert "别墅光伏" in topics
        assert "民宿光伏" in topics

    def test_mock_comments_cover_scenarios(self, mock_collector: DouyinLiveCollector) -> None:
        """Mock 评论覆盖: 别墅报价、区域安装、叠拼省钱、科普、民宿、农村。"""
        all_comments = mock_collector.collect(account_id="test", max_count=20)
        contents = " ".join(r.content for r in all_comments)

        # 业务场景覆盖
        assert "别墅" in contents  # 别墅安装
        assert "叠拼" in contents  # 叠拼咨询
        assert "民宿" in contents  # 小商业
        assert "报价" in contents or "多少钱" in contents  # 价格咨询
        assert "顶楼" in contents  # 普通住宅

    def test_mock_collect_and_save(self, mock_collector: DouyinLiveCollector) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = mock_collector.collect_and_save(
                account_id="test_acc",
                account_name="成都光伏老王",
                max_count=10,
                output_root=Path(tmp),
            )
            assert result is not None
            assert result.exists()


# ══════════════════════════════════════════════════════════════════════
# Live 模式测试
# ══════════════════════════════════════════════════════════════════════

class TestLiveMode:

    def test_with_credentials_api_available(self, live_collector: DouyinLiveCollector) -> None:
        assert live_collector._api_available is True

    def test_with_cookie_api_available(self) -> None:
        c = DouyinLiveCollector(credentials={"cookie": "session_abc"})
        assert c._api_available is True

    def test_with_api_key_available(self) -> None:
        c = DouyinLiveCollector(credentials={"api_key": "dy_key_123"})
        assert c._api_available is True

    def test_live_mode_still_collects(self, live_collector: DouyinLiveCollector) -> None:
        """Live 模式 API 未实现时，degrade 到 Mock 数据。"""
        records = live_collector.collect(account_id="test", max_count=5)
        assert len(records) >= 1

    def test_live_mode_via_platform_adapter(self) -> None:
        adapter = PlatformAdapterManager(
            config={"platforms": {"douyin": {"enabled": True}}},
            credentials={"douyin": {"cookie": "test"}},
        )
        c = adapter.get_collector("douyin", mode="public")
        assert c is not None
        assert "DouyinLiveCollector" in type(c).__name__

    def test_live_mode_session_valid(self, live_collector: DouyinLiveCollector) -> None:
        assert live_collector.is_session_valid() is True


# ══════════════════════════════════════════════════════════════════════
# 字段映射测试
# ══════════════════════════════════════════════════════════════════════

class TestFieldMapping:

    def test_parse_to_record_fields(self, mock_collector: DouyinLiveCollector) -> None:
        raw = {
            "comment_id": "dy_test_001",
            "content": "测试评论内容",
            "author": "测试用户",
            "create_time": "2026-07-20 12:00:00",
            "ip_location": "四川成都",
            "like_count": "15",
        }
        record = mock_collector._parse_to_record(raw)

        assert record.comment_id == "dy_test_001"
        assert record.platform == "douyin"
        assert record.content == "测试评论内容"
        assert record.author == "测试用户"
        assert record.create_time == "2026-07-20 12:00:00"
        assert record.ip_location == "四川成都"
        assert record.like_count == 15
        assert record.processing_status == "collected"
        assert record.collected_time != ""

    def test_parse_with_missing_fields(self, mock_collector: DouyinLiveCollector) -> None:
        """缺失字段使用默认值。"""
        raw: dict = {}
        record = mock_collector._parse_to_record(raw)
        assert record.comment_id == ""
        assert record.platform == "douyin"
        assert record.content == ""
        assert record.like_count == 0

    def test_all_mock_records_have_required_fields(self, mock_collector: DouyinLiveCollector) -> None:
        records = mock_collector.collect(account_id="test", max_count=20)
        for r in records:
            assert r.comment_id != ""
            assert r.platform == "douyin"
            assert r.content != ""
            assert r.collected_time != ""
            assert r.processing_status == "collected"

    def test_to_pipeline_event_format(self, mock_collector: DouyinLiveCollector) -> None:
        records = mock_collector.collect(account_id="test", max_count=5)
        for r in records:
            event = r.to_pipeline_event()
            assert "id" in event
            assert "platform" in event
            assert "content" in event
            assert event["platform"] == "douyin"


# ══════════════════════════════════════════════════════════════════════
# 业务边界测试
# ══════════════════════════════════════════════════════════════════════

class TestBusinessBoundary:

    def test_villa_comments_present(self, mock_collector: DouyinLiveCollector) -> None:
        """别墅评论在 Mock 数据中存在。"""
        records = mock_collector.collect(account_id="test", max_count=20)
        villa = [r for r in records if "别墅" in r.content]
        assert len(villa) >= 2

    def test_small_business_comments_present(self, mock_collector: DouyinLiveCollector) -> None:
        """小商业评论在 Mock 数据中存在。"""
        records = mock_collector.collect(account_id="test", max_count=20)
        biz = [r for r in records if "民宿" in r.content]
        assert len(biz) >= 1

    def test_urban_locations_present(self, mock_collector: DouyinLiveCollector) -> None:
        """城市 IP 属地在 Mock 数据中。"""
        records = mock_collector.collect(account_id="test", max_count=20)
        locations = {r.ip_location for r in records}
        assert "四川成都" in locations
        assert "重庆" in locations

    def test_validate_passes_valid_records(self, mock_collector: DouyinLiveCollector) -> None:
        """合法评论通过 validate。"""
        record = CommentRecord(comment_id="v", content="成都别墅想装光伏")
        assert mock_collector.validate(record) is True

    def test_validate_rejects_empty(self, mock_collector: DouyinLiveCollector) -> None:
        """空内容被 validate 拒绝。"""
        record = CommentRecord(comment_id="e", content="")
        assert mock_collector.validate(record) is False


# ══════════════════════════════════════════════════════════════════════
# 速率限制和重试
# ══════════════════════════════════════════════════════════════════════

class TestRateLimitAndRetry:

    def test_rate_limit_configured(self, mock_collector: DouyinLiveCollector) -> None:
        assert mock_collector.rate_limiter.requests_per_minute == 10

    def test_rate_limit_acquire(self, mock_collector: DouyinLiveCollector) -> None:
        for _ in range(10):
            assert mock_collector.rate_limiter.acquire() is True

    def test_should_retry_forbidden(self, mock_collector: DouyinLiveCollector) -> None:
        assert mock_collector._should_retry(Exception("403 Forbidden"), 0, 3) is False

    def test_should_retry_network(self, mock_collector: DouyinLiveCollector) -> None:
        assert mock_collector._should_retry(ConnectionError("timeout"), 0, 3) is True

    def test_max_retries_default(self, mock_collector: DouyinLiveCollector) -> None:
        assert mock_collector.max_retries == 3


# ══════════════════════════════════════════════════════════════════════
# Pipeline 集成测试
# ══════════════════════════════════════════════════════════════════════

class TestPipelineIntegration:

    def test_mock_record_through_pipeline(self, engine: Engine, mock_collector: DouyinLiveCollector) -> None:
        """DouyinLiveCollector Mock 数据通过 Pipeline。"""
        records = mock_collector.collect(account_id="test", max_count=5)
        for r in records:
            event = r.to_pipeline_event()
            result = engine.run_single(event)
            assert "_pipeline_error" not in result, f"Pipeline error: {r.comment_id}"
            assert "scoring" in result

    def test_villa_record_s_grade(self, engine: Engine, mock_collector: DouyinLiveCollector) -> None:
        """别墅报价评论 → S 级。"""
        records = mock_collector.collect(account_id="test", max_count=20)
        villa = [r for r in records if "别墅" in r.content and "报价" in r.content]
        if villa:
            result = engine.run_single(villa[0].to_pipeline_event())
            assert result["scoring"]["lead_grade"] == "S"

    def test_inquiry_record_not_s(self, engine: Engine, mock_collector: DouyinLiveCollector) -> None:
        """纯咨询评论应不是 S 级。"""
        records = mock_collector.collect(account_id="test", max_count=20)
        inquiry = [r for r in records if "靠谱吗" in r.content]
        if inquiry:
            result = engine.run_single(inquiry[0].to_pipeline_event())
            assert result["scoring"]["lead_grade"] in ("A", "B")

    def test_all_mock_pipeline_no_error(self, engine: Engine, mock_collector: DouyinLiveCollector) -> None:
        """全部 Mock 评论通过 Pipeline 不报错。"""
        records = mock_collector.collect(account_id="test", max_count=20)
        for r in records:
            event = r.to_pipeline_event()
            result = engine.run_single(event)
            assert "_pipeline_error" not in result
            assert result["scoring"]["lead_grade"] in ("S", "A", "B", "C")


# ══════════════════════════════════════════════════════════════════════
# 回归测试
# ══════════════════════════════════════════════════════════════════════

class TestRegression:

    def test_legacy_douyin_connector_still_works(self) -> None:
        """旧 DouyinConnector 不受影响。"""
        from collector_base import create_collector
        c = create_collector("douyin", credentials={})
        comments = c.collect(account_id="test", max_count=3)
        assert len(comments) == 3

    def test_platform_adapter_mock_still_works(self) -> None:
        """Platform Adapter mock 模式仍返回旧 Connector。"""
        from platform_adapter import get_collector
        c = get_collector("douyin", mode="mock")
        comments = c.collect(account_id="test", max_count=3)
        assert len(comments) == 3

    def test_platform_adapter_auto_no_creds_still_mock(self) -> None:
        """auto 模式无凭证仍返回 mock。"""
        from platform_adapter import get_collector
        c = get_collector("douyin", mode="auto")
        comments = c.collect(account_id="test", max_count=3)
        assert len(comments) == 3
