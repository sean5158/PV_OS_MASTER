"""Platform Adapter + LiveCollectorBase 测试 (P2-1)。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_platform_adapter.py -v
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from collector_base import BaseCollector, CommentRecord  # noqa: E402
from live_collector_base import (  # noqa: E402
    CollectorSession,
    LiveCollectorBase,
    RateLimiter,
)
from platform_adapter import (  # noqa: E402
    CollectorMode,
    PlatformAdapterManager,
    SUPPORTED_PLATFORMS,
    get_adapter,
    get_collector,
    get_platform_status,
)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# RateLimiter 测试
# ══════════════════════════════════════════════════════════════════════

class TestRateLimiter:

    def test_acquire_within_limit(self) -> None:
        rl = RateLimiter(requests_per_minute=10)
        for _ in range(10):
            assert rl.acquire() is True

    def test_acquire_exceeds_limit(self) -> None:
        rl = RateLimiter(requests_per_minute=3)
        for _ in range(3):
            assert rl.acquire() is True
        assert rl.acquire() is False

    def test_cooldown_blocks(self) -> None:
        rl = RateLimiter(requests_per_minute=10, cooldown_seconds=0.5)
        rl.cooldown()
        assert rl.acquire() is False

    def test_cooldown_expires(self) -> None:
        rl = RateLimiter(requests_per_minute=10, cooldown_seconds=0.1)
        rl.cooldown()
        time.sleep(0.2)
        assert rl.acquire() is True

    def test_reset(self) -> None:
        rl = RateLimiter(requests_per_minute=2)
        for _ in range(2):
            rl.acquire()
        assert rl.acquire() is False
        rl.reset()
        assert rl.acquire() is True

    def test_jitter_disabled(self) -> None:
        rl = RateLimiter(requests_per_minute=10, cooldown_seconds=0.1, jitter=False)
        rl.cooldown()
        time.sleep(0.2)
        assert rl.acquire() is True

    def test_wait_if_needed_no_wait(self) -> None:
        rl = RateLimiter(requests_per_minute=10)
        waited = rl.wait_if_needed()
        assert waited == 0.0


# ══════════════════════════════════════════════════════════════════════
# CollectorSession 测试
# ══════════════════════════════════════════════════════════════════════

class TestCollectorSession:

    def test_valid_with_cookie(self) -> None:
        sess = CollectorSession("douyin", {"cookie": "abc123"})
        assert sess.is_valid is True

    def test_invalid_without_cookie(self) -> None:
        sess = CollectorSession("douyin", {})
        assert sess.is_valid is False

    def test_invalid_with_empty_cookie(self) -> None:
        sess = CollectorSession("douyin", {"cookie": ""})
        assert sess.is_valid is False

    def test_invalidate(self) -> None:
        sess = CollectorSession("douyin", {"cookie": "abc"})
        assert sess.is_valid is True
        sess.invalidate()
        assert sess.is_valid is False

    def test_touch(self) -> None:
        sess = CollectorSession("douyin", {"cookie": "abc"})
        old_time = sess.last_used_at
        time.sleep(0.01)
        sess.touch()
        assert sess.last_used_at > old_time

    def test_age_seconds(self) -> None:
        sess = CollectorSession("douyin", {"cookie": "abc"})
        assert sess.age_seconds() >= 0
        assert sess.age_seconds() < 5


# ══════════════════════════════════════════════════════════════════════
# CollectorMode 测试
# ══════════════════════════════════════════════════════════════════════

class TestCollectorMode:

    def test_values(self) -> None:
        assert CollectorMode.AUTO == "auto"
        assert CollectorMode.MOCK == "mock"
        assert CollectorMode.PUBLIC == "public"

    def test_string_conversion(self) -> None:
        assert str(CollectorMode.AUTO) == "auto"
        assert str(CollectorMode.MOCK) == "mock"


# ══════════════════════════════════════════════════════════════════════
# PlatformAdapterManager 测试
# ══════════════════════════════════════════════════════════════════════

class TestPlatformAdapterManager:

    @pytest.fixture
    def adapter(self) -> PlatformAdapterManager:
        """创建无凭证的适配器 (全部降级 Mock)。"""
        return PlatformAdapterManager(
            config={"platforms": {}},
            credentials={},
        )

    @pytest.fixture
    def adapter_with_creds(self) -> PlatformAdapterManager:
        """创建有凭证的适配器 (douyin 可 Live)。"""
        return PlatformAdapterManager(
            config={"platforms": {}},
            credentials={
                "douyin": {"cookie": "test_dy_cookie"},
                "xiaohongshu": {"cookie": ""},
            },
        )

    # ── 模式解析 ──

    def test_resolve_mode_auto_without_creds(self, adapter: PlatformAdapterManager) -> None:
        assert adapter.resolve_mode("douyin", "auto") == CollectorMode.MOCK

    def test_resolve_mode_auto_with_creds(self, adapter_with_creds: PlatformAdapterManager) -> None:
        assert adapter_with_creds.resolve_mode("douyin", "auto") == CollectorMode.PUBLIC

    def test_resolve_mode_mock_always(self, adapter_with_creds: PlatformAdapterManager) -> None:
        """即使有凭证，mock 模式也返回 mock。"""
        assert adapter_with_creds.resolve_mode("douyin", "mock") == CollectorMode.MOCK

    def test_resolve_mode_live_without_creds_raises(self, adapter: PlatformAdapterManager) -> None:
        with pytest.raises(ValueError, match="凭证无效"):
            adapter.resolve_mode("douyin", "public")

    def test_resolve_mode_live_with_creds(self, adapter_with_creds: PlatformAdapterManager) -> None:
        assert adapter_with_creds.resolve_mode("douyin", "public") == CollectorMode.PUBLIC

    def test_resolve_mode_auto_xiaohongshu_no_cookie(self, adapter_with_creds: PlatformAdapterManager) -> None:
        """小红书 auto → file (P2: 文件导入优先)。"""
        assert adapter_with_creds.resolve_mode("xiaohongshu", "auto") == CollectorMode.FILE

    # ── 凭证校验 ──

    def test_validate_credentials_empty(self, adapter: PlatformAdapterManager) -> None:
        assert adapter.validate_credentials("douyin") is False

    def test_validate_credentials_valid(self, adapter_with_creds: PlatformAdapterManager) -> None:
        assert adapter_with_creds.validate_credentials("douyin") is True

    def test_validate_credentials_empty_cookie(self, adapter_with_creds: PlatformAdapterManager) -> None:
        assert adapter_with_creds.validate_credentials("xiaohongshu") is False

    def test_validate_credentials_unknown_platform(self, adapter: PlatformAdapterManager) -> None:
        assert adapter.validate_credentials("unknown_platform") is False

    def test_validate_credentials_api_key(self) -> None:
        adapter = PlatformAdapterManager(
            config={"platforms": {}},
            credentials={"douyin": {"api_key": "dy_key_123"}},
        )
        assert adapter.validate_credentials("douyin") is True

    # ── Collector 创建 ──

    def test_get_collector_mock(self, adapter: PlatformAdapterManager) -> None:
        for p in SUPPORTED_PLATFORMS:
            if p == "csv_import":
                continue  # csv_import 仅支持 file 模式
            c = adapter.get_collector(p, mode="mock")
            assert c is not None
            assert isinstance(c, BaseCollector)

    def test_get_collector_auto_without_creds(self, adapter: PlatformAdapterManager) -> None:
        """无凭证时 auto → mock。"""
        c = adapter.get_collector("douyin", mode="auto")
        assert c is not None
        # Mock 模式下 _mock_collect 存在（douyin + xiaohongshu）
        # kuaishou/wechat_video 的桩 connector 无 mock 方法

    def test_get_collector_unknown_platform(self, adapter: PlatformAdapterManager) -> None:
        assert adapter.get_collector("bilibili", mode="mock") is None

    def test_get_collector_live_without_creds_raises(self, adapter: PlatformAdapterManager) -> None:
        with pytest.raises(ValueError, match="凭证无效"):
            adapter.get_collector("douyin", mode="public")

    def test_get_collector_live_import_fallback(self, adapter_with_creds: PlatformAdapterManager) -> None:
        """Live Collector 类未实现时降级为现有 Connector + 真实凭证。"""
        c = adapter_with_creds.get_collector("douyin", mode="public")
        assert c is not None
        assert isinstance(c, BaseCollector)

    # ── 速率限制 ──

    def test_rate_limiter_defaults(self, adapter: PlatformAdapterManager) -> None:
        rl = adapter.get_rate_limiter("douyin")
        assert rl.requests_per_minute == 10
        assert rl.cooldown_seconds == 30

    def test_rate_limiter_from_config(self) -> None:
        adapter = PlatformAdapterManager(
            config={
                "platforms": {
                    "douyin": {
                        "enabled": True,
                        "rate_limit": {
                            "requests_per_minute": 20,
                            "cooldown_seconds": 15,
                        },
                    },
                },
            },
            credentials={},
        )
        rl = adapter.get_rate_limiter("douyin")
        assert rl.requests_per_minute == 20
        assert rl.cooldown_seconds == 15

    # ── 可用模式 ──

    def test_list_modes_without_creds(self, adapter: PlatformAdapterManager) -> None:
        modes = adapter.list_available_modes("douyin")
        assert "mock" in modes
        assert "auto" in modes
        assert "public" not in modes

    def test_list_modes_with_creds(self, adapter_with_creds: PlatformAdapterManager) -> None:
        modes = adapter_with_creds.list_available_modes("douyin")
        assert "mock" in modes
        assert "public" in modes
        assert "auto" in modes

    # ── 状态 ──

    def test_status_structure(self, adapter: PlatformAdapterManager) -> None:
        status = adapter.status()
        assert set(status.keys()) == set(SUPPORTED_PLATFORMS)
        for p, s in status.items():
            assert "mode_available" in s
            assert "credentials_valid" in s
            assert "rate_limit" in s
            assert "enabled_in_config" in s


# ══════════════════════════════════════════════════════════════════════
# 便捷函数测试
# ══════════════════════════════════════════════════════════════════════

class TestConvenienceFunctions:

    def test_get_collector_convenience(self) -> None:
        c = get_collector("douyin", mode="mock")
        assert c is not None
        assert isinstance(c, BaseCollector)

    def test_get_platform_status(self) -> None:
        status = get_platform_status()
        assert "douyin" in status

    def test_get_adapter_singleton(self) -> None:
        a1 = get_adapter()
        a2 = get_adapter()
        assert a1 is a2


# ══════════════════════════════════════════════════════════════════════
# Mock 兼容性测试: 确保新增模块不影响现有 Mock Collector
# ══════════════════════════════════════════════════════════════════════

class TestMockCompatibility:

    @pytest.fixture
    def adapter(self) -> PlatformAdapterManager:
        return PlatformAdapterManager(
            config={"platforms": {}},
            credentials={},
        )

    def test_douyin_mock_returns_6_comments(self, adapter: PlatformAdapterManager) -> None:
        c = adapter.get_collector("douyin", mode="mock")
        comments = c.collect(account_id="test_001", max_count=50)
        assert len(comments) == 6

    def test_douyin_mock_content_has_villa(self, adapter: PlatformAdapterManager) -> None:
        c = adapter.get_collector("douyin", mode="mock")
        comments = c.collect(account_id="test_001", max_count=50)
        villa_comments = [cm for cm in comments if "别墅" in cm.content]
        assert len(villa_comments) >= 1

    def test_xiaohongshu_mock_returns_5_comments(self, adapter: PlatformAdapterManager) -> None:
        c = adapter.get_collector("xiaohongshu", mode="mock")
        comments = c.collect(account_id="test_001", max_count=30)
        assert len(comments) == 5

    def test_mock_collect_and_save(self, adapter: PlatformAdapterManager, tmp_path: Path) -> None:
        c = adapter.get_collector("douyin", mode="mock")
        result = c.collect_and_save(
            account_id="test_001",
            account_name="测试账号",
            max_count=10,
            output_root=tmp_path,
        )
        assert result is not None
        assert result.exists()

    def test_all_platforms_mock_no_error(self, adapter: PlatformAdapterManager) -> None:
        """所有平台 Mock 模式不报错。"""
        for p in SUPPORTED_PLATFORMS:
            if p == "csv_import":
                continue  # csv_import 仅支持 file 模式
            c = adapter.get_collector(p, mode="mock")
            assert c is not None
            comments = c.collect(account_id="test", max_count=5)
            assert isinstance(comments, list)

    def test_pipeline_comment_record_format(self, adapter: PlatformAdapterManager) -> None:
        """Mock 评论格式符合 CommentRecord 规范。"""
        c = adapter.get_collector("douyin", mode="mock")
        comments = c.collect(account_id="test_001", max_count=50)
        for cm in comments:
            assert cm.platform in SUPPORTED_PLATFORMS or cm.platform == "douyin"
            assert cm.content != ""
            assert cm.comment_id != ""
            pipeline_event = cm.to_pipeline_event()
            assert "id" in pipeline_event
            assert "content" in pipeline_event
            assert "platform" in pipeline_event


# ══════════════════════════════════════════════════════════════════════
# LiveCollectorBase 抽象类测试
# ══════════════════════════════════════════════════════════════════════

class StubLiveCollector(LiveCollectorBase):
    """用于测试的桩 Live Collector。"""

    def __init__(self, credentials=None, rate_limiter=None):
        super().__init__(credentials, rate_limiter)

    def _fetch_video_list(self, account_id, cursor, limit):
        return [
            {"video_id": f"v_{account_id}_001", "title": "测试视频1", "url": "https://example.com/1"},
            {"video_id": f"v_{account_id}_002", "title": "测试视频2", "url": "https://example.com/2"},
        ]

    def _fetch_comments(self, video_id, cursor, limit):
        return [
            {"comment_id": f"c_{video_id}_1", "content": "测试评论1", "author": "用户A"},
            {"comment_id": f"c_{video_id}_2", "content": "测试评论2", "author": "用户B"},
        ]

    def _parse_to_record(self, raw_item):
        return CommentRecord(
            comment_id=raw_item["comment_id"],
            platform=self.platform_name,
            content=raw_item["content"],
            author=raw_item.get("author", ""),
        )


class TestLiveCollectorBase:

    def test_collect_returns_records(self) -> None:
        collector = StubLiveCollector({"cookie": "test"})
        records = collector.collect(account_id="test_acc", max_count=10)
        assert len(records) > 0
        assert all(isinstance(r, CommentRecord) for r in records)

    def test_collect_respects_max_count(self) -> None:
        collector = StubLiveCollector({"cookie": "test"})
        # 2 视频 × 2 评论 = 4，但 max_count=2
        records = collector.collect(account_id="test_acc", max_count=2)
        assert len(records) <= 2

    def test_connector_mode_is_live(self) -> None:
        collector = StubLiveCollector({"cookie": "test"})
        assert collector.connector_mode == "live"

    def test_rate_limit_check_called(self) -> None:
        """速率限制不应报错。"""
        rl = RateLimiter(requests_per_minute=10)
        collector = StubLiveCollector({"cookie": "test"}, rate_limiter=rl)
        records = collector.collect(account_id="test_acc", max_count=5)
        assert len(records) > 0

    def test_session_valid_with_cookie(self) -> None:
        collector = StubLiveCollector({"cookie": "test"})
        assert collector.is_session_valid() is True

    def test_session_invalid_without_cookie(self) -> None:
        collector = StubLiveCollector({})
        assert collector.is_session_valid() is False

    def test_retry_with_backoff_success(self) -> None:
        collector = StubLiveCollector({"cookie": "test"})
        result = collector._retry_with_backoff(lambda x: x * 2, 21)
        assert result == 42

    def test_retry_with_backoff_eventually_fails(self) -> None:
        collector = StubLiveCollector({"cookie": "test"})
        call_count = [0]

        def flaky():
            call_count[0] += 1
            raise ConnectionError("网络错误")

        with pytest.raises(ConnectionError):
            collector._retry_with_backoff(flaky, max_retries=2)
        assert call_count[0] == 3  # 1 initial + 2 retries

    def test_should_retry_forbidden(self) -> None:
        collector = StubLiveCollector({"cookie": "test"})
        assert collector._should_retry(Exception("403 Forbidden"), 0, 3) is False

    def test_should_retry_rate_limit(self) -> None:
        collector = StubLiveCollector({"cookie": "test"})
        assert collector._should_retry(Exception("429 rate limit"), 0, 3) is True

    def test_should_retry_network_error(self) -> None:
        collector = StubLiveCollector({"cookie": "test"})
        assert collector._should_retry(ConnectionError("连接超时"), 0, 3) is True

    def test_validate_passthrough(self) -> None:
        """BaseCollector.validate() 仍然有效。"""
        collector = StubLiveCollector({"cookie": "test"})
        assert collector.validate(CommentRecord(comment_id="1", content="有效评论")) is True
        assert collector.validate(CommentRecord(comment_id="2", content="")) is False
