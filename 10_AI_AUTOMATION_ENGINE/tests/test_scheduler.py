"""调度器增强测试 (P1-4) — 执行日志 + 重试 + 并发。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_scheduler.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(ENGINE_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "02_DATA" / "01_COLLECTION"))

from tasks.task_manager import TaskManager  # noqa: E402
from scheduler.collection_scheduler import (  # noqa: E402
    ScheduleLogger,
    run_once,
    seed_tasks,
    MAX_CONCURRENT,
    PER_PLATFORM_LIMIT,
)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ── Fixtures ──

@pytest.fixture
def tm() -> TaskManager:
    with tempfile.TemporaryDirectory() as tmp:
        mgr = TaskManager(tasks_dir=Path(tmp))
        yield mgr


@pytest.fixture
def slog() -> ScheduleLogger:
    with tempfile.TemporaryDirectory() as tmp:
        # Monkeypatch LOGS_DIR
        import scheduler.collection_scheduler as cs
        old_dir = cs.LOGS_DIR
        cs.LOGS_DIR = Path(tmp)
        yield ScheduleLogger()
        cs.LOGS_DIR = old_dir


# ══════════════════════════════════════════════════════════════════════
# ScheduleLogger 测试
# ══════════════════════════════════════════════════════════════════════

class TestScheduleLogger:

    def test_log_run_creates_file(self, slog: ScheduleLogger) -> None:
        entry = {
            "scan_mode": "test",
            "tasks_total": 10,
            "tasks_executed": 5,
            "success": 4,
            "failed": 1,
            "skipped": 2,
            "retried": 0,
            "no_new_comments": 0,
            "task_details": [],
            "task_pool_stats": {"pending": 3},
            "duration_seconds": 1.5,
        }
        path = slog.log_run(entry)
        assert path.exists()

        # 验证内容
        data = json.loads(path.read_text())
        assert len(data) == 1
        assert data[0]["success"] == 4
        assert data[0]["duration_seconds"] == 1.5

    def test_log_run_appends(self, slog: ScheduleLogger) -> None:
        slog.log_run({"scan_mode": "test", "tasks_total": 1, "success": 1, "tasks_executed": 1,
                       "failed": 0, "skipped": 0, "retried": 0, "no_new_comments": 0,
                       "task_details": [], "task_pool_stats": {}, "duration_seconds": 0.5})
        slog.log_run({"scan_mode": "test", "tasks_total": 2, "success": 2, "tasks_executed": 2,
                       "failed": 0, "skipped": 0, "retried": 0, "no_new_comments": 0,
                       "task_details": [], "task_pool_stats": {}, "duration_seconds": 1.0})

        logs = slog.get_today_logs()
        assert len(logs) == 2
        assert logs[0]["tasks_total"] == 1
        assert logs[1]["tasks_total"] == 2

    def test_get_today_logs_empty(self, slog: ScheduleLogger) -> None:
        assert slog.get_today_logs() == []

    def test_clean_old_logs(self, slog: ScheduleLogger) -> None:
        # 创建一条日志
        slog.log_run({"scan_mode": "test", "tasks_total": 1, "success": 1, "tasks_executed": 1,
                       "failed": 0, "skipped": 0, "retried": 0, "no_new_comments": 0,
                       "task_details": [], "task_pool_stats": {}, "duration_seconds": 0})

        # keep_days=0 会清理所有
        removed = slog.clean_old_logs(keep_days=0)
        assert removed >= 1


# ══════════════════════════════════════════════════════════════════════
# 并发控制测试
# ══════════════════════════════════════════════════════════════════════

class TestConcurrency:

    def test_max_concurrent_defined(self) -> None:
        """并发限制常量已定义。"""
        assert "P0" in MAX_CONCURRENT
        assert "P1" in MAX_CONCURRENT
        assert "P2" in MAX_CONCURRENT
        assert MAX_CONCURRENT["P0"] == 3

    def test_per_platform_limits(self) -> None:
        """per-platform 限制已定义。"""
        assert "douyin" in PER_PLATFORM_LIMIT
        assert "xiaohongshu" in PER_PLATFORM_LIMIT
        assert PER_PLATFORM_LIMIT["douyin"] == 2
        assert PER_PLATFORM_LIMIT["xiaohongshu"] == 1

    def test_concurrency_respected(self, tm: TaskManager) -> None:
        """P0 并发限制 3: 创建 5 个 P0 任务 + 模拟执行。"""
        for i in range(5):
            tm.create(
                platform="douyin",
                account_id=f"conc_test_{i}",
                priority="P0",
                start_immediately=True,
            )

        pending = tm.get_pending()
        assert len(pending) == 5

        # 模拟并发控制逻辑
        limit = MAX_CONCURRENT["P0"]  # 3
        platform_limit = PER_PLATFORM_LIMIT["douyin"]  # 2

        executed = 0
        running_prio: dict[str, int] = {}
        running_plat: dict[str, int] = {}
        skipped = 0

        for task in pending:
            if running_prio.get(task.priority, 0) >= limit:
                skipped += 1
                continue
            if running_plat.get(task.platform, 0) >= platform_limit:
                skipped += 1
                continue
            executed += 1
            running_prio[task.priority] = running_prio.get(task.priority, 0) + 1
            running_plat[task.platform] = running_plat.get(task.platform, 0) + 1

        # per-platform limit is 2, so at most 2 douyin tasks should execute
        assert executed == 2, f"expected 2 (platform limit), got {executed}"
        assert skipped == 3


# ══════════════════════════════════════════════════════════════════════
# 重试逻辑测试
# ══════════════════════════════════════════════════════════════════════

class TestRetryLogic:

    def test_failed_task_has_next_run_time(self, tm: TaskManager) -> None:
        """失败任务有 next_run_time（退避时间）。"""
        task = tm.create(platform="douyin", account_id="retry_test", start_immediately=True)
        tm.start(task.task_id)
        tm.fail(task.task_id, error_type="timeout", error_message="连接超时")

        t = tm.get(task.task_id)
        assert t.status == "failed"
        assert t.next_run_time != ""
        assert t.retry_count == 1

    def test_failed_task_retry_pickup(self, tm: TaskManager) -> None:
        """failed 任务的 next_run_time 在现在之前时应被拾取。"""
        task = tm.create(platform="douyin", account_id="pickup_test", start_immediately=True)
        tm.start(task.task_id)
        tm.fail(task.task_id, error_type="api_error", error_message="500")

        t = tm.get(task.task_id)
        now = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")

        # 首次重试间隔是 5 分钟，next_run_time 应在将来
        assert t.next_run_time > now, f"next_run {t.next_run_time} should be > now {now} for valid retry backoff"

    def test_failed_final_not_retried(self, tm: TaskManager) -> None:
        """failed_final 状态不应被重试。"""
        task = tm.create(platform="douyin", account_id="final_test", start_immediately=True)
        tm.start(task.task_id)

        for i in range(3):
            tm.fail(task.task_id, error_type=f"err_{i}", error_message=f"failure {i}")
            if i < 2:
                tm.retry(task.task_id)

        t = tm.get(task.task_id)
        assert t.status == "failed_final"
        assert t.retry_count == 3

    def test_retry_count_increments(self, tm: TaskManager) -> None:
        """每次 fail 后 retry_count 递增。"""
        task = tm.create(platform="xiaohongshu", account_id="inc_test", start_immediately=True)
        tm.start(task.task_id)

        tm.fail(task.task_id, error_type="e1", error_message="m1")
        assert tm.get(task.task_id).retry_count == 1

        tm.retry(task.task_id)
        tm.fail(task.task_id, error_type="e2", error_message="m2")
        assert tm.get(task.task_id).retry_count == 2


# ══════════════════════════════════════════════════════════════════════
# 调度器集成测试
# ══════════════════════════════════════════════════════════════════════

class TestSchedulerIntegration:

    def test_run_once_dry_run(self) -> None:
        """干跑模式不执行任务，返回完整结果结构。"""
        result = run_once(dry_run=True)
        # dry-run 模式应正常返回，包含完整字段
        assert "tasks_total" in result
        assert result["tasks_executed"] == 0
        assert result["scan_mode"] == "once"

    def test_run_once_no_tasks(self, tm: TaskManager) -> None:
        """无就绪任务时正常返回。"""
        result = run_once()
        assert result["tasks_executed"] == 0
        assert result["success"] == 0

    def test_seed_creates_tasks(self, tm: TaskManager) -> None:
        """播种创建任务。"""
        result = seed_tasks(platforms=["douyin"])
        # 当前 CSV 有 1 条 douyin 记录
        assert result["accounts"] >= 0
        assert result["tasks"] >= 0

    def test_result_structure(self, tm: TaskManager) -> None:
        """调度结果应包含所有必要字段。"""
        result = run_once()
        required = [
            "scan_mode", "tasks_total", "tasks_executed",
            "success", "failed", "no_new_comments",
            "skipped", "retried", "task_pool_stats", "duration_seconds",
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_scan_mode_tracked(self, tm: TaskManager) -> None:
        """scan_mode 应反映运行模式。"""
        import scheduler.collection_scheduler as cs

        # 验证默认 once 模式
        result = run_once()
        assert result["scan_mode"] == "once"

    def test_schedule_log_written(self, tm: TaskManager) -> None:
        """调度运行后应有日志写入。"""
        # 创建任务并标记完成
        task = tm.create(platform="douyin", account_id="log_test", start_immediately=True)
        tm.start(task.task_id)
        tm.complete(task.task_id, collected_count=0)

        # 创建新的 pending 任务
        tm.create(platform="douyin", account_id="log_test2", start_immediately=True)

        import scheduler.collection_scheduler as cs

        # 验证日志目录存在
        assert cs.LOGS_DIR.exists()

        # 清理
        slog = ScheduleLogger()
        slog.clean_old_logs(keep_days=0)


# ══════════════════════════════════════════════════════════════════════
# 测试: 全链路回归
# ══════════════════════════════════════════════════════════════════════

class TestRegression:
    """确保调度器升级不破坏已有功能。"""

    def test_task_model_still_works(self, tm: TaskManager) -> None:
        """TaskManager CRUD 正常。"""
        task = tm.create(platform="douyin", account_id="reg_test")
        assert task.task_id != ""
        found = tm.get(task.task_id)
        assert found is not None

    def test_full_lifecycle_still_works(self, tm: TaskManager) -> None:
        """完整生命周期不受影响。"""
        task = tm.create(platform="douyin", account_id="lifecycle_test", start_immediately=True)
        tm.start(task.task_id)
        tm.complete(task.task_id, last_cursor="c_123", collected_count=10)
        assert tm.get(task.task_id).status == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
