"""PV_OS 采集调度器 V2 — 任务队列驱动 + 执行日志 + 重试 + 并发控制。

从 TaskManager 读取就绪任务 → 执行采集 → 触发 Pipeline。
支持：执行日志持久化、失败重试拾取、per-priority 并发限制。

Usage::

    python scheduler/collection_scheduler.py --once          # 单次运行
    python scheduler/collection_scheduler.py --once --seed   # 播种+运行
    python scheduler/collection_scheduler.py --daemon        # 持续运行(5min scan)
    python scheduler/collection_scheduler.py --once --platform douyin
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# ── 路径 ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
ENGINE_DIR = Path(__file__).resolve().parent.parent
TASKS_DIR = PROJECT_ROOT / "02_DATA" / "01_COLLECTION" / "tasks"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(TASKS_DIR.parent))

from tasks.task_manager import TaskManager  # noqa: E402
from config_loader import load_collection_config, load_platform_credentials, get_enabled_platforms  # noqa: E402
from collector_base import create_collector  # noqa: E402
from triggers.event_bus import EventBus  # noqa: E402
from engine import Engine  # noqa: E402

# ── 常量 ──
TZ_SHANGHAI = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ_SHANGHAI)
NOW_STR = lambda: NOW().strftime("%Y-%m-%d %H:%M:%S")
LOGS_DIR = Path(__file__).resolve().parent / "schedule_logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

COMPETITOR_CSV = PROJECT_ROOT / "02_DATA" / "02_COMPETITOR_DATABASE" / "competitor_accounts.csv"

# 并发限制: {priority: max_concurrent}
MAX_CONCURRENT: dict[str, int] = {"P0": 3, "P1": 5, "P2": 2}
# per-platform 并发 (同一平台同时最多 N 个采集任务)
PER_PLATFORM_LIMIT: dict[str, int] = {"douyin": 2, "xiaohongshu": 1, "kuaishou": 1, "wechat_video": 1}


# ══════════════════════════════════════════════════════════════════════
# 执行日志
# ══════════════════════════════════════════════════════════════════════

class ScheduleLogger:
    """调度执行日志 — 持久化到 schedule_logs/YYYY-MM-DD.json。

    每次调度运行生成一个 entry，记录：时间、任务数、成功/失败数、详情。
    """

    def __init__(self) -> None:
        self.logs_dir = LOGS_DIR

    def log_run(self, run_result: dict[str, Any]) -> Path:
        """记录一次调度运行结果。"""
        entry = {
            "run_time": NOW_STR(),
            "scan_mode": run_result.get("scan_mode", "once"),
            "tasks_total": run_result.get("tasks_total", 0),
            "tasks_executed": run_result.get("tasks_executed", 0),
            "success": run_result.get("success", 0),
            "failed": run_result.get("failed", 0),
            "skipped": run_result.get("skipped", 0),
            "retried": run_result.get("retried", 0),
            "no_new_comments": run_result.get("no_new_comments", 0),
            "task_details": run_result.get("task_details", []),
            "task_pool_stats": run_result.get("task_pool_stats", {}),
            "duration_seconds": run_result.get("duration_seconds", 0),
        }

        today = NOW().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"

        # Append to daily log
        existing: list[dict] = []
        if log_file.exists():
            try:
                existing = json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = []

        existing.append(entry)
        log_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

        logging.getLogger(__name__).info("调度日志 → %s (%d entries today)", log_file.name, len(existing))
        return log_file

    def get_today_logs(self) -> list[dict[str, Any]]:
        """读取今天的日志。"""
        today = NOW().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.json"
        if log_file.exists():
            try:
                return json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def clean_old_logs(self, keep_days: int = 30) -> int:
        """清理超过 N 天的日志文件。"""
        cutoff = NOW() - timedelta(days=keep_days)
        removed = 0
        for f in self.logs_dir.glob("*.json"):
            try:
                date_str = f.stem  # YYYY-MM-DD
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=TZ_SHANGHAI)
                if file_date < cutoff:
                    f.unlink()
                    removed += 1
            except (ValueError, TypeError):
                pass
        return removed


# ══════════════════════════════════════════════════════════════════════
# 账号加载
# ══════════════════════════════════════════════════════════════════════

def load_competitor_accounts(min_grade: str = "B") -> list[dict[str, str]]:
    import csv
    if not COMPETITOR_CSV.exists():
        return _default_accounts()
    grade_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    min_rank = grade_order.get(min_grade, 99)
    accounts: list[dict[str, str]] = []
    with open(COMPETITOR_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            grade = row.get("monitor_level", row.get("grade", "C"))
            if grade_order.get(grade, 99) <= min_rank:
                accounts.append(row)
    return accounts


def _default_accounts() -> list[dict[str, str]]:
    return [
        {"account_id": "test_dy_001", "account_name": "某光伏安装公司", "platform": "douyin", "monitor_level": "S"},
        {"account_id": "test_dy_002", "account_name": "光伏知识科普", "platform": "douyin", "monitor_level": "A"},
        {"account_id": "test_xhs_001", "account_name": "阳光房改造日记", "platform": "xiaohongshu", "monitor_level": "A"},
    ]


# ══════════════════════════════════════════════════════════════════════
# 单任务执行
# ══════════════════════════════════════════════════════════════════════

def execute_task(
    task: Any,
    credentials: dict[str, Any],
    bus: EventBus,
    dry_run: bool = False,
) -> dict[str, Any]:
    """执行单个采集任务。"""
    tm = TaskManager()
    logger = logging.getLogger(__name__)

    if dry_run:
        logger.info("[DRY RUN] %s (%s/%s)", task.task_id, task.platform, task.account_name)
        return {"task_id": task.task_id, "status": "dry_run", "platform": task.platform}

    # 1. 启动
    task = tm.start(task.task_id)
    if not task:
        return {"task_id": task.task_id, "status": "start_failed", "platform": task.platform}

    # 2. 连接器
    collector = create_collector(task.platform, credentials.get(task.platform, {}))
    if collector is None:
        tm.fail(task.task_id, error_type="no_connector", error_message=f"无 {task.platform} 连接器")
        return {"task_id": task.task_id, "status": "no_connector", "platform": task.platform}

    # 3. 采集
    try:
        result_path = collector.collect_and_save(
            account_id=task.account_id,
            account_name=task.account_name,
            max_count=task.comment_limit.per_video,
        )
    except Exception as e:
        tm.fail(task.task_id, error_type="collect_error", error_message=str(e)[:200])
        return {"task_id": task.task_id, "status": "collect_error", "platform": task.platform, "error": str(e)[:100]}

    if result_path is None:
        tm.complete(task.task_id, last_cursor=task.last_cursor, collected_count=0)
        return {"task_id": task.task_id, "status": "no_new_comments", "platform": task.platform}

    # 4. 游标提取
    last_cursor = task.last_cursor
    collected_count = 0
    try:
        data = json.loads(result_path.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else [data]
        collected_count = len(records)
        if records:
            last_cursor = records[-1].get("comment_id", records[-1].get("id", ""))
    except (json.JSONDecodeError, OSError, IndexError):
        pass

    # 5. 完成
    tm.complete(task.task_id, last_cursor=last_cursor, collected_count=collected_count)

    # 6. 数据清洗（采集后 → cleaned/）
    if collected_count > 0:
        try:
            from data_cleaner import clean_raw_files
            clean_report = clean_raw_files(platforms=[task.platform])
            logger.info("数据清洗: %d 条 → %d 条 (去重%d 噪声%d)",
                         clean_report.get("total", 0),
                         clean_report.get("cleaned", 0),
                         clean_report.get("duplicates", 0),
                         clean_report.get("noise", 0))
        except Exception as e:
            logger.warning("数据清洗失败: %s", e)

    # 7. Pipeline 触发
    if collected_count > 0:
        _trigger_pipeline_for_batch(result_path, bus)

    return {
        "task_id": task.task_id,
        "status": "completed",
        "platform": task.platform,
        "collected": collected_count,
        "cursor": last_cursor[:30] if last_cursor else "",
    }


def _trigger_pipeline_for_batch(batch_file: Path, bus: EventBus) -> int:
    if not batch_file.exists():
        return 0
    try:
        data = json.loads(batch_file.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else [data]
    except (json.JSONDecodeError, OSError):
        return 0

    count = 0
    for record in records:
        bus.emit("new_comment_received", {
            "id": record.get("comment_id", record.get("id", "")),
            "platform": record.get("platform", ""),
            "content": record.get("content", record.get("comment_text", "")),
            "author": record.get("author", record.get("nickname", "")),
            "create_time": record.get("create_time", record.get("comment_time", "")),
            "source_url": record.get("source_url", ""),
            "source_account": record.get("source_account", ""),
            "source_account_id": record.get("source_account_id", ""),
            "ip_location": record.get("ip_location", ""),
            "video_title": record.get("source_video_title", ""),
            "keyword": "",
        })
        count += 1

    if count:
        logging.getLogger(__name__).info("触发 %d 条 Pipeline 事件 ← %s", count, batch_file.name)
    return count


# ══════════════════════════════════════════════════════════════════════
# 种子任务
# ══════════════════════════════════════════════════════════════════════

def seed_tasks(
    platforms: list[str] | None = None,
    min_grade: str = "B",
    dry_run: bool = False,
) -> dict[str, Any]:
    tm = TaskManager()
    accounts = load_competitor_accounts(min_grade)
    if platforms:
        accounts = [a for a in accounts if a.get("platform", "") in platforms]
    if dry_run:
        logging.getLogger(__name__).info("[DRY RUN] 将为 %d 个账号创建种子任务", len(accounts))
        return {"accounts": len(accounts), "tasks": 0}
    created = tm.seed_from_accounts(accounts)
    return {"accounts": len(accounts), "tasks": len(created)}


# ══════════════════════════════════════════════════════════════════════
# 主调度循环 (增强版)
# ══════════════════════════════════════════════════════════════════════

def run_once(
    platforms: list[str] | None = None,
    dry_run: bool = False,
    seed: bool = False,
    scan_mode: str = "once",
) -> dict[str, Any]:
    """单次调度运行。

    流程：
    1. (可选) 播种初始任务
    2. 拾取 failed 任务 → 检查退避时间 → 重试
    3. 拾取 pending 任务 → 并发控制 → 执行
    4. 记录执行日志
    """
    start_time = NOW()
    config = load_collection_config()
    credentials = load_platform_credentials()
    tm = TaskManager()
    slog = ScheduleLogger()
    logger = logging.getLogger(__name__)

    # ── 播种 ──
    if seed:
        seed_result = seed_tasks(platforms=platforms, dry_run=dry_run)
        logger.info("播种: %d 个账号 → %d 个新任务", seed_result["accounts"], seed_result["tasks"])

    # ── Pipeline Engine ──
    bus = EventBus()
    workflow_path = ENGINE_DIR / "workflows" / "comment_to_lead_pipeline.yml"
    engine = Engine(workflow_path)
    for event_name in engine.workflow.get("trigger", {}).get("event", []):
        bus.subscribe(event_name, lambda ev: engine._execute(ev))

    # ── 任务池统计 ──
    all_tasks = tm.list_all()
    pending_all = tm.list_by_status("pending")
    failed_all = tm.list_by_status("failed")
    now_str = NOW_STR()

    logger.info("=" * 55)
    logger.info("PV_OS 采集调度 V2 (%s)", scan_mode)
    logger.info("  任务池: %d total | %d pending | %d failed | %d ready",
                 len(all_tasks), len(pending_all), len(failed_all),
                 len([t for t in pending_all if t.next_run_time and t.next_run_time <= now_str]))
    if dry_run:
        logger.info("  [DRY RUN 模式]")
    logger.info("=" * 55)

    results: list[dict[str, Any]] = []
    task_details: list[dict[str, Any]] = []

    # ── Phase 1: 重试 failed 任务 ──
    retried_count = 0
    if not dry_run:
        for ftask in failed_all:
            if ftask.next_run_time and ftask.next_run_time <= now_str:
                if platforms and ftask.platform not in platforms:
                    continue
                logger.info("重试 failed 任务: %s (尝试 %d/%d)", ftask.task_id, ftask.retry_count, ftask.max_retries)
                result = execute_task(ftask, credentials, bus)
                results.append(result)
                task_details.append({"task_id": ftask.task_id, "action": "retry", "status": result.get("status")})
                retried_count += 1

    # ── Phase 2: 执行 pending 任务 ──
    pending_tasks = tm.get_pending()
    if platforms:
        pending_tasks = [t for t in pending_tasks if t.platform in platforms]

    if not pending_tasks and not dry_run and retried_count == 0:
        logger.info("无就绪任务。使用 --seed 从竞品主表创建初始任务。")
        return _build_result(0, 0, 0, 0, 0, 0, tm, slog, start_time, scan_mode)

    # 并发控制: per-priority + per-platform
    running_priority: dict[str, int] = {}
    running_platform: dict[str, int] = {}
    skipped_count = 0

    for task in pending_tasks:
        if dry_run:
            logger.info("[DRY RUN] %s (%s/%s, priority=%s)", task.task_id, task.platform, task.account_name, task.priority)
            task_details.append({"task_id": task.task_id, "action": "dry_run", "status": "dry_run"})
            continue

        prio = task.priority
        plat = task.platform

        # per-priority 限制
        prio_limit = MAX_CONCURRENT.get(prio, 2)
        if running_priority.get(prio, 0) >= prio_limit:
            skipped_count += 1
            continue

        # per-platform 限制
        plat_limit = PER_PLATFORM_LIMIT.get(plat, 1)
        if running_platform.get(plat, 0) >= plat_limit:
            skipped_count += 1
            continue

        # 执行
        result = execute_task(task, credentials, bus)
        results.append(result)
        task_details.append({"task_id": task.task_id, "action": "execute", "status": result.get("status")})
        running_priority[prio] = running_priority.get(prio, 0) + 1
        running_platform[plat] = running_platform.get(plat, 0) + 1

    # ── 统计 ──
    success = [r for r in results if r.get("status") == "completed"]
    failed = [r for r in results if r.get("status") not in ("completed", "dry_run", "no_new_comments")]
    no_new = [r for r in results if r.get("status") == "no_new_comments"]
    dry_runs = [r for r in results if r.get("status") == "dry_run"]

    tasks_executed = len([r for r in results if r.get("status") != "dry_run"])

    logger.info(
        "调度结束: %d 成功 | %d 失败 | %d 空结果 | %d 跳过 | %d 重试",
        len(success), len(failed), len(no_new), skipped_count, retried_count,
    )
    logger.info("任务池状态: %s", tm.stats())

    result = _build_result(
        tasks_executed, len(success), len(failed), len(no_new), skipped_count, retried_count,
        tm, slog, start_time, scan_mode,
    )
    result["task_details"] = task_details
    return result


def _build_result(
    executed: int, success: int, failed: int, no_new: int,
    skipped: int, retried: int,
    tm: TaskManager, slog: ScheduleLogger,
    start_time: datetime, scan_mode: str,
) -> dict[str, Any]:
    """构建调度结果并写入日志。"""
    duration = (NOW() - start_time).total_seconds()
    result = {
        "scan_mode": scan_mode,
        "tasks_total": len(tm.list_all()),
        "tasks_executed": executed,
        "success": success,
        "failed": failed,
        "no_new_comments": no_new,
        "skipped": skipped,
        "retried": retried,
        "task_pool_stats": tm.stats(),
        "duration_seconds": round(duration, 2),
        "task_details": [],
    }

    # 持久化日志
    if executed > 0 or retried > 0:
        slog.log_run(result)

    return result


# ══════════════════════════════════════════════════════════════════════
# Cron 表达式支持（简化版）
# ══════════════════════════════════════════════════════════════════════

def parse_simple_cron(expr: str) -> int | None:
    """解析简化的 cron 表达式为扫描间隔（秒）。

    支持格式：
        "* * * * *"          → 60s (每分钟)
        "*/5 * * * *"        → 300s
        "0 */6 * * *"        → 21600s (每6小时)
        "0 9 * * *"          → 每日09:00 → 返回 None (需用next_run_time计算)
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return None
    minute_part = parts[0]
    if minute_part.startswith("*/"):
        try:
            return int(minute_part[2:]) * 60
        except ValueError:
            return None
    return 300  # default 5min


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="PV_OS 采集调度器 V2 (任务驱动)")
    parser.add_argument("--once", action="store_true", default=True, help="单次运行")
    parser.add_argument("--seed", action="store_true", help="从竞品主表播种初始任务")
    parser.add_argument("--daemon", action="store_true", help="持续运行")
    parser.add_argument("--scan", type=int, default=300, help="守护模式扫描间隔(秒), 默认300")
    parser.add_argument("--platform", type=str, help="仅运行指定平台")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    args = parser.parse_args()

    platforms = [args.platform] if args.platform else None

    if args.daemon:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        logger = logging.getLogger(__name__)
        logger.info("守护模式启动，每 %d 秒扫描任务池...", args.scan)
        iteration = 0
        while True:
            iteration += 1
            logger.info("── 第 %d 次扫描 ──", iteration)
            run_once(platforms=platforms, seed=args.seed, scan_mode=f"daemon(#{iteration})")
            logger.info("等待 %d 秒...", args.scan)
            time.sleep(args.scan)
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        run_once(platforms=platforms, seed=args.seed, dry_run=args.dry_run, scan_mode="once")


if __name__ == "__main__":
    main()
