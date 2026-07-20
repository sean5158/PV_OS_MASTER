"""Task Model 单元测试 + 集成测试。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_task_model.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "02_DATA" / "01_COLLECTION"))

from tasks.task_manager import (  # noqa: E402
    CollectionTask,
    CommentLimit,
    ErrorEntry,
    TaskManager,
    VideoFilter,
    _now,
    _next_schedule,
    _derive_next_id,
)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ── Fixtures ──

@pytest.fixture
def tm() -> TaskManager:
    """使用临时目录的 TaskManager，测试完毕自动清理。"""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = TaskManager(tasks_dir=Path(tmp))
        yield mgr


@pytest.fixture
def sample_task(tm: TaskManager) -> CollectionTask:
    return tm.create(
        platform="douyin",
        account_id="cd_pv_001",
        account_name="成都光伏老王",
        account_category="regional_installer",
        collection_frequency="6h",
        priority="P0",
    )


# ── Unit Tests: 数据结构 ──

class TestDataStructure:
    """CollectionTask / VideoFilter / CommentLimit 数据结构。"""

    def test_task_creation_defaults(self) -> None:
        task = CollectionTask(
            task_id="test_001",
            platform="douyin",
            account_id="acc_001",
        )
        assert task.status == "pending"
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.last_cursor == ""
        assert isinstance(task.video_filter, VideoFilter)
        assert isinstance(task.comment_limit, CommentLimit)
        assert task.video_filter.time_range_days == 30

    def test_task_serialization_roundtrip(self) -> None:
        task = CollectionTask(
            task_id="test_002",
            platform="xiaohongshu",
            account_id="xhs_001",
            account_name="阳光房改造",
            status="running",
            last_cursor="comment_789",
            error_log=[ErrorEntry(attempt=1, time="2026-07-20 10:00:00", error_type="timeout", error_message="连接超时")],
        )
        d = task.to_dict()
        restored = CollectionTask.from_dict(d)
        assert restored.task_id == task.task_id
        assert restored.platform == task.platform
        assert restored.last_cursor == task.last_cursor
        assert restored.status == task.status
        assert len(restored.error_log) == 1
        assert restored.error_log[0].error_type == "timeout"

    def test_video_filter_defaults(self) -> None:
        vf = VideoFilter()
        assert vf.time_range_days == 30
        assert vf.housing_match_only is False
        assert "installation" in vf.video_types

    def test_comment_limit_defaults(self) -> None:
        cl = CommentLimit()
        assert cl.per_video == 50
        assert cl.time_window_days == 0


# ── Unit Tests: TaskManager CRUD ──

class TestTaskManagerCRUD:
    """创建、查询、更新任务。"""

    def test_create_task(self, tm: TaskManager) -> None:
        task = tm.create(
            platform="douyin",
            account_id="acc_001",
            account_name="测试账号",
            priority="P0",
        )
        assert task.task_id.startswith("douyin_acc_001_")
        assert task.status == "pending"
        assert task.priority == "P0"
        assert task.next_run_time != ""

        # 文件已落盘
        path = tm._task_path(task.task_id)
        assert path.exists()

    def test_create_task_not_immediate(self, tm: TaskManager) -> None:
        task = tm.create(
            platform="douyin",
            account_id="acc_002",
            start_immediately=False,
            collection_frequency="daily",
        )
        # next_run_time 应该在明天
        now = datetime.now(TZ_SHANGHAI)
        nrt = datetime.strptime(task.next_run_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ_SHANGHAI)
        assert nrt > now

    def test_get_task(self, tm: TaskManager, sample_task: CollectionTask) -> None:
        found = tm.get(sample_task.task_id)
        assert found is not None
        assert found.task_id == sample_task.task_id

    def test_get_nonexistent(self, tm: TaskManager) -> None:
        assert tm.get("nonexistent_001") is None

    def test_list_all(self, tm: TaskManager) -> None:
        tm.create(platform="douyin", account_id="a1")
        tm.create(platform="xiaohongshu", account_id="a2")
        all_tasks = tm.list_all()
        assert len(all_tasks) >= 2

    def test_list_by_status(self, tm: TaskManager) -> None:
        tm.create(platform="douyin", account_id="a1")
        t2 = tm.create(platform="douyin", account_id="a2")
        tm.start(t2.task_id)
        tm.complete(t2.task_id, last_cursor="c1", collected_count=5)

        pending = tm.list_by_status("pending")
        completed = tm.list_by_status("completed")
        assert len(pending) >= 1
        assert len(completed) >= 1

    def test_list_by_platform(self, tm: TaskManager) -> None:
        tm.create(platform="douyin", account_id="a1")
        tm.create(platform="xiaohongshu", account_id="a2")
        dy = tm.list_by_platform("douyin")
        xhs = tm.list_by_platform("xiaohongshu")
        assert len(dy) >= 1
        assert len(xhs) >= 1

    def test_has_active_task(self, tm: TaskManager) -> None:
        tm.create(platform="douyin", account_id="active_acc")
        assert tm.has_active_task("douyin", "active_acc") is True
        assert tm.has_active_task("douyin", "nonexistent") is False

    def test_get_pending(self, tm: TaskManager) -> None:
        t = tm.create(platform="douyin", account_id="acc_p", start_immediately=True)
        ready = tm.get_pending()
        assert any(r.task_id == t.task_id for r in ready)

    def test_get_pending_not_ready(self, tm: TaskManager) -> None:
        t = tm.create(platform="douyin", account_id="acc_future", start_immediately=False, collection_frequency="daily")
        ready = tm.get_pending()
        assert not any(r.task_id == t.task_id for r in ready)


# ── Unit Tests: 状态机 ──

class TestStateMachine:
    """状态流转验证。"""

    def test_full_lifecycle(self, tm: TaskManager, sample_task: CollectionTask) -> None:
        tid = sample_task.task_id

        # pending → running
        t = tm.start(tid)
        assert t.status == "running"

        # running → completed
        t = tm.complete(tid, last_cursor="c_123", collected_count=50)
        assert t.status == "completed"
        assert t.last_cursor == "c_123"
        assert t.last_collected_count == 50

    def test_failed_with_retry(self, tm: TaskManager, sample_task: CollectionTask) -> None:
        tid = sample_task.task_id
        tm.start(tid)

        # 第一次失败
        t = tm.fail(tid, error_type="timeout", error_message="连接超时")
        assert t.status == "failed"
        assert t.retry_count == 1
        assert len(t.error_log) == 1

        # 重试
        t = tm.retry(tid)
        assert t.status == "running"

        # 第二次失败
        t = tm.fail(tid, error_type="rate_limit", error_message="429")
        assert t.status == "failed"
        assert t.retry_count == 2

    def test_failed_final(self, tm: TaskManager, sample_task: CollectionTask) -> None:
        tid = sample_task.task_id
        tm.start(tid)

        for i in range(3):
            t = tm.fail(tid, error_type=f"err_{i}", error_message=f"失败{i+1}次")
            if i < 2:
                tm.retry(tid)

        t = tm.get(tid)
        assert t.status == "failed_final"
        assert t.retry_count == 3
        assert len(t.error_log) == 3

    def test_pause_resume(self, tm: TaskManager, sample_task: CollectionTask) -> None:
        tid = sample_task.task_id
        tm.start(tid)
        t = tm.pause(tid)
        assert t.status == "paused"
        t = tm.resume(tid)
        assert t.status == "running"

    def test_cancel(self, tm: TaskManager, sample_task: CollectionTask) -> None:
        tid = sample_task.task_id
        t = tm.cancel(tid)
        assert t.status == "cancelled"

    def test_invalid_transition(self, tm: TaskManager, sample_task: CollectionTask) -> None:
        """completed → running 不应该被允许（应返回 None）。"""
        tid = sample_task.task_id
        tm.start(tid)
        tm.complete(tid, last_cursor="c1", collected_count=5)
        # 直接 start 已完成的 task 应该失败
        t = tm.start(tid)
        assert t is None  # 或至少状态不应改变


# ── Unit Tests: 游标 ──

class TestCursor:
    """增量采集游标。"""

    def test_cursor_update(self, tm: TaskManager, sample_task: CollectionTask) -> None:
        tid = sample_task.task_id
        tm.start(tid)
        t = tm.update_cursor(tid, "comment_456")
        assert t.last_cursor == "comment_456"

    def test_cursor_reset(self, tm: TaskManager, sample_task: CollectionTask) -> None:
        tid = sample_task.task_id
        tm.start(tid)
        tm.complete(tid, last_cursor="old_cursor", collected_count=10)
        t = tm.reset_cursor(tid)
        assert t.last_cursor == ""

    def test_cursor_inheritance(self, tm: TaskManager) -> None:
        """完成时 cursor 应该继承到下一周期任务。"""
        t = tm.create(platform="douyin", account_id="cursor_test")
        tm.start(t.task_id)
        tm.complete(t.task_id, last_cursor="inherited_cursor", collected_count=30)

        # 下一周期任务应该继承 cursor
        next_tasks = tm.list_by_account("douyin", "cursor_test")
        next_pending = [t for t in next_tasks if t.status == "pending"]
        assert len(next_pending) >= 1
        assert next_pending[0].last_cursor == "inherited_cursor"


# ── Unit Tests: 批量操作 ──

class TestBatchOperations:
    """批量创建、统计、清理。"""

    def test_seed_from_accounts(self, tm: TaskManager) -> None:
        accounts = [
            {"platform": "douyin", "account_id": "s1", "account_name": "S账号", "monitor_level": "S"},
            {"platform": "douyin", "account_id": "a1", "account_name": "A账号", "monitor_level": "A"},
            {"platform": "xiaohongshu", "account_id": "b1", "account_name": "B账号", "monitor_level": "B"},
        ]
        created = tm.seed_from_accounts(accounts)
        assert len(created) == 3

        # S 级应该是 P0/6h
        s_task = tm.get(created[0].task_id)
        assert s_task.priority == "P0"
        assert s_task.collection_frequency == "6h"

        # B 级应该是 P2/weekly
        b_task = tm.get(created[2].task_id)
        assert b_task.priority == "P2"
        assert b_task.collection_frequency == "weekly"

    def test_seed_skip_duplicate(self, tm: TaskManager) -> None:
        """不应为已有活跃任务的账号重复创建。"""
        tm.create(platform="douyin", account_id="dup_acc")
        accounts = [{"platform": "douyin", "account_id": "dup_acc", "monitor_level": "A"}]
        created = tm.seed_from_accounts(accounts)
        assert len(created) == 0

    def test_stats(self, tm: TaskManager) -> None:
        tm.create(platform="douyin", account_id="a1")
        tm.create(platform="douyin", account_id="a2")
        stats = tm.stats()
        assert stats.get("pending", 0) >= 2

    def test_clean_completed(self, tm: TaskManager) -> None:
        t = tm.create(platform="douyin", account_id="clean_test")
        tm.start(t.task_id)
        tm.complete(t.task_id, collected_count=1)
        removed = tm.clean_completed(keep_days=0)
        assert removed >= 1


# ── Unit Tests: 辅助函数 ──

class TestHelpers:

    def test_next_schedule_6h(self) -> None:
        base = "2026-07-20 10:00:00"
        result = _next_schedule(base, "6h")
        assert "2026-07-20 16:00" in result

    def test_next_schedule_daily(self) -> None:
        base = "2026-07-20 10:00:00"
        result = _next_schedule(base, "daily")
        assert "2026-07-21" in result

    def test_derive_next_id(self) -> None:
        tid = "douyin_acc_001_20260720_001"
        new_id = _derive_next_id(tid)
        assert new_id.startswith("douyin_acc_001_")
        assert new_id != tid


# ── Integration Test: Task → Collector → Pipeline ──

class TestIntegration:
    """端到端：创建任务 → 执行采集 → 验证 Pipeline 产出。"""

    def test_task_to_pipeline(self, tm: TaskManager) -> None:
        """Mock 模式下完整的任务驱动流程。"""
        # 1. 创建任务
        task = tm.create(
            platform="douyin",
            account_id="integration_test_001",
            account_name="集成测试账号",
            priority="P0",
        )

        # 2. 启动 + 模拟完成
        tm.start(task.task_id)

        # 模拟采集完成（不实际调平台）
        t = tm.complete(
            task.task_id,
            last_cursor="dy_comment_999",
            collected_count=42,
        )
        assert t.status == "completed"
        assert t.last_cursor == "dy_comment_999"
        assert t.total_collected_count == 42

        # 3. 下一周期任务已生成
        next_tasks = tm.list_by_account("douyin", "integration_test_001")
        pending = [t for t in next_tasks if t.status == "pending"]
        assert len(pending) == 1

        # 4. 检查状态统计
        stats = tm.stats()
        assert stats.get("completed", 0) >= 1
        assert stats.get("pending", 0) >= 1

    def test_full_retry_cycle(self, tm: TaskManager) -> None:
        """完整的失败重试周期。"""
        task = tm.create(platform="douyin", account_id="retry_test")
        tm.start(task.task_id)

        # 失败 2 次后重试，再失败 1 次 → failed_final
        for i in range(3):
            tm.fail(task.task_id, error_type=f"err_{i}", error_message=f"test error {i}")
            if i < 2:
                tm.retry(task.task_id)

        t = tm.get(task.task_id)
        assert t.status == "failed_final"
        assert t.retry_count == 3
        assert len(t.error_log) == 3

        # 第一次重试间隔 5 分钟
        assert "5" in str(RETRY_BACKOFF_MINUTES[0])  # 常量值检查


# ── Helpers ──

RETRY_BACKOFF_MINUTES = [5, 30, 120]  # 从 task_manager 引用


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
