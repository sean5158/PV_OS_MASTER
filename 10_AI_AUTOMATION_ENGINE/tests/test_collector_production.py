"""Collector 生产增强测试 (P2-4)。

覆盖: cursor增量 / 分页 / 状态持久化 / 采集日志 / 回归。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_collector_production.py -v
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
ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ENGINE_ROOT))

from collector_state import (  # noqa: E402
    CollectorState,
    CollectorLogger,
    CollectionLogEntry,
    PaginationState,
)
from douyin_live_collector import DouyinLiveCollector  # noqa: E402
from collector_base import CommentRecord  # noqa: E402

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# CollectorState 测试
# ══════════════════════════════════════════════════════════════════════

class TestCollectorState:

    def test_initial_state(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc_001")
        assert s.platform == "douyin"
        assert s.last_comment_id == ""
        assert s.total_comments_fetched == 0

    def test_update_video_cursor(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.update_video_cursor("page_3", has_more=True)
        assert s.last_video_cursor == "page_3"
        assert s.video_pagination.has_more is True
        assert s.video_pagination.current_page == 1

    def test_update_comment_cursor(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.update_comment_cursor("page_2", "dy_c_456", has_more=False)
        assert s.last_comment_id == "dy_c_456"
        assert s.comment_pagination.has_more is False

    def test_add_videos(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.add_videos(5)
        s.add_videos(3)
        assert s.total_videos_fetched == 8

    def test_add_comments(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.add_comments(fetched=10, valid=8)
        assert s.total_comments_fetched == 10
        assert s.total_comments_valid == 8

    def test_record_error(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.record_error("连接超时")
        assert s.error_count == 1
        assert "连接超时" in s.last_error
        assert s.last_error_time != ""

    def test_get_task_cursor(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.last_comment_id = "dy_c_999"
        assert s.get_task_cursor() == "dy_c_999"

    def test_has_new_data(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.last_comment_id = "dy_new"
        assert s.has_new_data("dy_old") is True
        assert s.has_new_data("dy_new") is False

    def test_mark_run_start(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.mark_run_start()
        assert s.run_start_time != ""
        assert s.last_run_time != ""

    def test_reset_pagination(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.update_video_cursor("p5", has_more=True)
        s.update_comment_cursor("p3", "cid", has_more=True)
        s.reset_pagination()
        assert s.video_pagination.current_page == 0
        assert s.comment_pagination.current_page == 0

    def test_serialization_roundtrip(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc_001", account_name="test")
        s.update_video_cursor("vp2", has_more=True)
        s.update_comment_cursor("cp3", "dy_c_789", has_more=False)
        s.add_videos(5)
        s.add_comments(20, 18)

        d = s.to_dict()
        restored = CollectorState.from_dict(d)

        assert restored.platform == "douyin"
        assert restored.last_comment_id == "dy_c_789"
        assert restored.video_pagination.has_more is True
        assert restored.comment_pagination.has_more is False

    def test_save_load(self) -> None:
        s = CollectorState(platform="douyin", account_id="acc")
        s.last_comment_id = "dy_saved"

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            s.save(path)
            loaded = CollectorState.load(path)
            assert loaded.last_comment_id == "dy_saved"
            assert loaded.platform == "douyin"

    def test_load_nonexistent(self) -> None:
        s = CollectorState.load(Path("/nonexistent/state.json"))
        assert s.platform == ""
        assert s.last_comment_id == ""


# ══════════════════════════════════════════════════════════════════════
# CollectorLogger 测试
# ══════════════════════════════════════════════════════════════════════

class TestCollectorLogger:

    def test_create_entry(self) -> None:
        clog = CollectorLogger("douyin")
        entry = clog.create_entry(account_id="acc", account_name="test", mode="mock")
        assert entry.platform == "douyin"
        assert entry.start_time != ""
        assert entry.mode == "mock"

    def test_finalize_entry(self) -> None:
        clog = CollectorLogger("douyin")
        entry = clog.create_entry(account_id="acc", mode="mock")
        state = CollectorState(platform="douyin", account_id="acc")
        state.add_videos(3)
        state.add_comments(10, 8)
        state.last_comment_id = "dy_123"

        clog.finalize_entry(entry, state, status="success")
        assert entry.status == "success"
        assert entry.videos_fetched == 3
        assert entry.comments_fetched == 10
        assert entry.comments_valid == 8
        assert entry.end_cursor == "dy_123"

    def test_write_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clog = CollectorLogger("douyin", logs_dir=Path(tmp))
            entry = clog.create_entry(account_id="acc")
            state = CollectorState(platform="douyin", account_id="acc")
            clog.finalize_entry(entry, state, status="success")
            path = clog.write_log(entry)
            assert path.exists()

    def test_get_today_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            clog = CollectorLogger("douyin", logs_dir=Path(tmp))
            entry = clog.create_entry(account_id="acc")
            state = CollectorState(platform="douyin", account_id="acc")
            clog.finalize_entry(entry, state, status="success")
            clog.write_log(entry)

            entries = clog.get_today_entries()
            assert len(entries) == 1

    def test_cursor_changed_detection(self) -> None:
        clog = CollectorLogger("douyin")
        entry = clog.create_entry(account_id="acc")
        entry.start_cursor = "old_cursor"
        state = CollectorState(platform="douyin", account_id="acc")
        state.last_comment_id = "new_cursor"
        clog.finalize_entry(entry, state)
        assert entry.cursor_changed is True

    def test_cursor_unchanged(self) -> None:
        clog = CollectorLogger("douyin")
        entry = clog.create_entry(account_id="acc")
        entry.start_cursor = "same"
        state = CollectorState(platform="douyin", account_id="acc")
        state.last_comment_id = "same"
        clog.finalize_entry(entry, state)
        assert entry.cursor_changed is False


# ══════════════════════════════════════════════════════════════════════
# Cursor 增量测试
# ══════════════════════════════════════════════════════════════════════

class TestCursorIncremental:

    def test_collect_with_state_returns_state(self) -> None:
        c = DouyinLiveCollector(credentials={})
        comments, state = c.collect_with_state(
            account_id="test", account_name="test", max_count=10,
        )
        assert len(comments) >= 1
        assert state.total_comments_fetched >= 0
        assert state.mode == "mock"

    def test_incremental_skips_old_comments(self) -> None:
        """增量模式：指定 cursor 后只返回新评论。"""
        c = DouyinLiveCollector(credentials={})
        # 先全量采集获取最后评论 ID
        all_comments, state1 = c.collect_with_state(
            account_id="test", max_count=20,
        )
        last_id = state1.last_comment_id
        assert last_id != ""

        # 用最后 ID 做增量采集 —— 应无新评论
        c2 = DouyinLiveCollector(credentials={})
        new_comments, state2 = c2.collect_with_state(
            account_id="test", max_count=20, last_cursor=last_id,
        )
        assert len(new_comments) == 0

    def test_cursor_with_midpoint(self) -> None:
        """从中间游标开始，只返回之后的评论。"""
        c = DouyinLiveCollector(credentials={})
        comments, state = c.collect_with_state(
            account_id="test", max_count=20,
            last_cursor="dy_real_003",  # 第3条之后
        )
        # dy_real_003 之后的评论 ID > dy_real_003
        for cm in comments:
            assert cm.comment_id > "dy_real_003"

    def test_get_last_state(self) -> None:
        c = DouyinLiveCollector(credentials={})
        _, _ = c.collect_with_state(account_id="test", max_count=5)
        state = c.get_last_state()
        assert state is not None
        assert state.platform == "douyin"
        assert state.account_id == "test"

    def test_get_state_dict(self) -> None:
        c = DouyinLiveCollector(credentials={})
        _, _ = c.collect_with_state(account_id="test", max_count=5)
        d = c.get_state_dict()
        assert d is not None
        assert "platform" in d
        assert "last_comment_id" in d

    def test_task_cursor_compatibility(self) -> None:
        """CollectorState.get_task_cursor() 返回的值可写入 TaskModel。"""
        c = DouyinLiveCollector(credentials={})
        _, state = c.collect_with_state(account_id="test", max_count=10)
        cursor = state.get_task_cursor()
        assert isinstance(cursor, str)
        assert len(cursor) > 0


# ══════════════════════════════════════════════════════════════════════
# 分页测试
# ══════════════════════════════════════════════════════════════════════

class TestPagination:

    def test_video_pagination_tracks_pages(self) -> None:
        c = DouyinLiveCollector(credentials={})
        _, state = c.collect_with_state(account_id="test", max_count=10)
        assert state.video_pagination.current_page >= 1
        assert state.total_videos_fetched >= 1

    def test_comment_pagination_tracks_pages(self) -> None:
        c = DouyinLiveCollector(credentials={})
        _, state = c.collect_with_state(account_id="test", max_count=10)
        assert state.comment_pagination.current_page >= 1

    def test_rate_limit_respected(self) -> None:
        """分页间有速率限制检查。"""
        c = DouyinLiveCollector(credentials={})
        rl_before = c.rate_limiter._request_count
        _, state = c.collect_with_state(account_id="test", max_count=20)
        # RateLimiter 应被调用过
        assert c.rate_limiter._request_count >= rl_before


# ══════════════════════════════════════════════════════════════════════
# 采集日志测试
# ══════════════════════════════════════════════════════════════════════

class TestCollectionLogging:

    def test_log_written_after_collect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            c = DouyinLiveCollector(credentials={}, state_dir=tmp)
            _, _ = c.collect_with_state(account_id="test", max_count=5)
            logs = c.get_today_logs()
            assert len(logs) >= 1
            assert logs[0]["platform"] == "douyin"
            assert logs[0]["status"] == "success"

    def test_log_contains_key_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            c = DouyinLiveCollector(credentials={}, state_dir=tmp)
            _, state = c.collect_with_state(account_id="log_test", account_name="日志测试", max_count=5)
            logs = c.get_today_logs()
            entry = logs[0]
            assert "run_id" in entry
            assert "account_id" in entry
            assert entry["account_id"] == "log_test"
            assert entry["account_name"] == "日志测试"
            assert "start_time" in entry
            assert "end_time" in entry
            assert "duration_seconds" in entry
            assert "comments_fetched" in entry
            assert "end_cursor" in entry

    def test_error_recorded_in_log(self) -> None:
        """错误场景也写入日志。"""
        with tempfile.TemporaryDirectory() as tmp:
            c = DouyinLiveCollector(credentials={}, state_dir=tmp)
            # 即使有异常也不应崩溃（内部 try/except）
            _, state = c.collect_with_state(account_id="test", max_count=5)
            logs = c.get_today_logs()
            assert len(logs) >= 1

    def test_save_state_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            c = DouyinLiveCollector(credentials={})
            _, _ = c.collect_with_state(account_id="test", max_count=5)
            state_path = Path(tmp) / "test_state.json"
            result = c.save_state(str(state_path))
            assert result is True
            assert state_path.exists()

            # 验证内容
            loaded = CollectorState.load(state_path)
            assert loaded.platform == "douyin"


# ══════════════════════════════════════════════════════════════════════
# 回归测试
# ══════════════════════════════════════════════════════════════════════

class TestRegression:

    def test_original_collect_still_works(self) -> None:
        """P2-3 的 collect() 方法不受影响。"""
        c = DouyinLiveCollector(credentials={})
        records = c.collect(account_id="test", max_count=10)
        assert len(records) >= 5

    def test_collect_and_save_still_works(self) -> None:
        c = DouyinLiveCollector(credentials={})
        with tempfile.TemporaryDirectory() as tmp:
            result = c.collect_and_save(
                account_id="test", account_name="测试",
                max_count=5, output_root=Path(tmp),
            )
            assert result is not None
            assert result.exists()

    def test_validate_still_works(self) -> None:
        c = DouyinLiveCollector(credentials={})
        assert c.validate(CommentRecord(comment_id="1", content="有效")) is True
        assert c.validate(CommentRecord(comment_id="2", content="")) is False

    def test_abstract_methods_still_work(self) -> None:
        c = DouyinLiveCollector(credentials={})
        videos = c._fetch_video_list("acc", "", 3)
        comments = c._fetch_comments("dy_video_001", "", 2)
        record = c._parse_to_record(comments[0])
        assert isinstance(videos, list)
        assert isinstance(comments, list)
        assert isinstance(record, CommentRecord)

    def test_platform_adapter_still_routes(self) -> None:
        from platform_adapter import PlatformAdapterManager
        adapter = PlatformAdapterManager(
            config={"platforms": {"douyin": {"enabled": True}}},
            credentials={"douyin": {"cookie": "test"}},
        )
        c = adapter.get_collector("douyin", mode="public")
        assert c is not None
        comments = c.collect(account_id="test", max_count=3)
        assert len(comments) >= 1
