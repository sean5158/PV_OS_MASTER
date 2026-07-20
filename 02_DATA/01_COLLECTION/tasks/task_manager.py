"""PV_OS 采集任务管理器。

管理采集任务的完整生命周期：创建 → 调度 → 执行 → 完成/失败 → 重试。

任务存储：02_DATA/01_COLLECTION/tasks/{task_id}.json
采用单文件单任务模式，避免并发写冲突。

Usage::

    from tasks.task_manager import TaskManager

    tm = TaskManager()
    task = tm.create(platform="douyin", account_id="acc_001", account_name="某光伏博主")
    tm.start(task.task_id)
    # ... 采集完成 ...
    tm.complete(task.task_id, last_cursor="comment_789", collected_count=50)
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── 常量 ──
TZ_SHANGHAI = timezone(timedelta(hours=8))
TASKS_DIR = Path(__file__).resolve().parent  # 02_DATA/01_COLLECTION/tasks/

# 状态机定义
VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending":       ["running", "cancelled"],
    "running":       ["completed", "failed", "paused"],
    "completed":     ["pending"],          # 自动生成下一周期任务
    "failed":        ["running", "cancelled", "failed_final"],  # 重试或放弃
    "failed_final":  [],                    # 终态，需人工介入
    "paused":        ["running", "cancelled"],
    "cancelled":     [],                    # 终态
}

# 重试退避间隔（分钟）
RETRY_BACKOFF_MINUTES = [5, 30, 120]

# 采集频率 → 下次执行间隔
FREQUENCY_INTERVALS: dict[str, timedelta] = {
    "6h":     timedelta(hours=6),
    "daily":  timedelta(days=1),
    "3d":     timedelta(days=3),
    "weekly": timedelta(weeks=1),
}


# ── 数据结构 ──

@dataclass
class VideoFilter:
    """视频筛选配置。"""
    time_range_days: int = 30
    housing_match_only: bool = False
    video_types: list[str] = field(default_factory=lambda: [
        "installation", "roof_renovation", "home_energy", "revenue", "price"
    ])


@dataclass
class CommentLimit:
    """评论采集限制。"""
    per_video: int = 50
    time_window_days: int = 0  # 0=不限


@dataclass
class ErrorEntry:
    """单次失败记录。"""
    attempt: int = 0
    time: str = ""
    error_type: str = ""
    error_message: str = ""


@dataclass
class CollectionTask:
    """采集任务完整数据结构。"""

    # ── 核心标识 ──
    task_id: str = ""
    task_type: str = "collection"   # discovery | monitor | collection (V3.0)
    platform: str = ""              # douyin | xiaohongshu | kuaishou | wechat_video
    account_id: str = ""
    account_name: str = ""
    account_category: str = ""      # national_brand | regional_installer | city_case | renovation
    is_first_collection: bool = True  # 首次采集标记 (V3.0: 首次=7天窗口)

    # ── 调度 ──
    collection_frequency: str = "6h"  # 6h | daily | 3d | weekly
    priority: str = "P0"             # P0 | P1 | P2

    # ── 范围控制 ──
    video_filter: VideoFilter = field(default_factory=VideoFilter)
    comment_limit: CommentLimit = field(default_factory=CommentLimit)

    # ── 状态 ──
    status: str = "pending"         # 见 VALID_TRANSITIONS
    retry_count: int = 0
    max_retries: int = 3

    # ── 增量游标 ──
    last_cursor: str = ""           # 上次采集的最后一条评论 ID（平台原始 ID）

    # ── 统计 ──
    last_collected_count: int = 0   # 上次采集到的评论数
    total_collected_count: int = 0  # 累计采集评论数

    # ── 时间 ──
    created_time: str = ""
    updated_time: str = ""
    last_run_time: str = ""
    next_run_time: str = ""

    # ── 错误日志 ──
    error_log: list[ErrorEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """序列化为 JSON 友好字典。"""
        d = asdict(self)
        # 嵌套 dataclass → dict
        d["video_filter"] = asdict(self.video_filter)
        d["comment_limit"] = asdict(self.comment_limit)
        d["error_log"] = [asdict(e) for e in self.error_log]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CollectionTask":
        """从字典反序列化。"""
        vf = data.pop("video_filter", {})
        cl = data.pop("comment_limit", {})
        el = data.pop("error_log", [])
        # Pop V3 fields that might not exist in old data
        data.pop("task_type", None)
        data.pop("is_first_collection", None)

        task = cls(**data)
        task.video_filter = VideoFilter(**vf) if isinstance(vf, dict) else vf
        task.comment_limit = CommentLimit(**cl) if isinstance(cl, dict) else cl
        task.error_log = [ErrorEntry(**e) if isinstance(e, dict) else e for e in el]
        return task


# ── 任务管理器 ──

class TaskManager:
    """采集任务管理器。

    所有任务持久化到 02_DATA/01_COLLECTION/tasks/{task_id}.json。
    """

    def __init__(self, tasks_dir: Path | None = None) -> None:
        self.tasks_dir = tasks_dir or TASKS_DIR
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    # ── 文件操作 ──

    def _task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def _load(self, task_id: str) -> CollectionTask | None:
        path = self._task_path(task_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CollectionTask.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("加载任务 %s 失败: %s", task_id, e)
            return None

    def _save(self, task: CollectionTask) -> None:
        task.updated_time = _now()
        path = self._task_path(task.task_id)
        path.write_text(
            json.dumps(task.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _delete(self, task_id: str) -> bool:
        path = self._task_path(task_id)
        if path.exists():
            path.unlink()
            return True
        return False

    # ── 状态转换校验 ──

    def _can_transition(self, current: str, target: str) -> bool:
        allowed = VALID_TRANSITIONS.get(current, [])
        return target in allowed

    # ── 创建任务 ──

    def create(
        self,
        platform: str,
        account_id: str,
        account_name: str = "",
        account_category: str = "",
        collection_frequency: str = "6h",
        priority: str = "P0",
        time_range_days: int = 30,
        per_video: int = 50,
        max_retries: int = 3,
        start_immediately: bool = True,
    ) -> CollectionTask:
        """创建新的采集任务。

        Args:
            platform: 平台名 (douyin/xiaohongshu/kuaishou/wechat_video)
            account_id: 竞品账号 ID
            account_name: 账号昵称
            account_category: 账号分类
            collection_frequency: 采集频率
            priority: 优先级 P0/P1/P2
            time_range_days: 视频时间范围
            per_video: 单视频最大评论数
            max_retries: 最大重试次数
            start_immediately: True=next_run_time=now, False=按频率推算

        Returns:
            创建的 CollectionTask
        """
        now = _now()
        today = datetime.now(TZ_SHANGHAI).strftime("%Y%m%d")

        # 生成唯一 task_id
        seq = _next_seq(self.tasks_dir, platform, account_id, today)
        task_id = f"{platform}_{account_id}_{today}_{seq:03d}"

        task = CollectionTask(
            task_id=task_id,
            platform=platform,
            account_id=account_id,
            account_name=account_name,
            account_category=account_category,
            collection_frequency=collection_frequency,
            priority=priority,
            video_filter=VideoFilter(
                time_range_days=time_range_days,
                housing_match_only=(priority != "P0"),
            ),
            comment_limit=CommentLimit(
                per_video=per_video,
                time_window_days=7 if priority == "P0" else 7,
            ),
            status="pending",
            retry_count=0,
            max_retries=max_retries,
            created_time=now,
            updated_time=now,
            next_run_time=now if start_immediately else _next_schedule(now, collection_frequency),
        )

        self._save(task)
        logger.info("创建任务 %s (%s/%s, priority=%s)", task_id, platform, account_name, priority)
        return task

    # ── 查询 ──

    def get(self, task_id: str) -> CollectionTask | None:
        """按 ID 获取任务。"""
        return self._load(task_id)

    def list_all(self) -> list[CollectionTask]:
        """列出所有任务。"""
        tasks: list[CollectionTask] = []
        for f in sorted(self.tasks_dir.glob("*.json")):
            task = self._load(f.stem)
            if task:
                tasks.append(task)
        return tasks

    def list_by_status(self, status: str | list[str]) -> list[CollectionTask]:
        """按状态查询。"""
        statuses = {status} if isinstance(status, str) else set(status)
        return [t for t in self.list_all() if t.status in statuses]

    def list_by_platform(self, platform: str) -> list[CollectionTask]:
        """按平台查询。"""
        return [t for t in self.list_all() if t.platform == platform]

    def list_by_account(self, platform: str, account_id: str) -> list[CollectionTask]:
        """按账号查询。"""
        return [t for t in self.list_all()
                if t.platform == platform and t.account_id == account_id]

    def get_pending(self, priority: str | None = None) -> list[CollectionTask]:
        """获取待执行任务（next_run_time <= now）。

        Args:
            priority: 可选优先级过滤
        """
        now = _now()
        tasks = self.list_by_status("pending")
        ready = [t for t in tasks if t.next_run_time and t.next_run_time <= now]
        if priority:
            ready = [t for t in ready if t.priority == priority]
        # 按优先级 + next_run_time 排序
        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        ready.sort(key=lambda t: (priority_order.get(t.priority, 99), t.next_run_time))
        return ready

    def has_active_task(self, platform: str, account_id: str) -> bool:
        """检查指定账号是否已有活跃任务（pending/running）。"""
        existing = self.list_by_account(platform, account_id)
        return any(t.status in ("pending", "running") for t in existing)

    # ── 状态转换 ──

    def start(self, task_id: str) -> CollectionTask | None:
        """开始执行任务 pending → running。"""
        task = self._load(task_id)
        if not task:
            logger.warning("任务不存在: %s", task_id)
            return None
        if not self._can_transition(task.status, "running"):
            logger.warning("无法从 %s 转换到 running (task=%s)", task.status, task_id)
            return None

        task.status = "running"
        task.last_run_time = _now()
        self._save(task)
        logger.info("开始执行任务 %s", task_id)
        return task

    def complete(
        self,
        task_id: str,
        last_cursor: str = "",
        collected_count: int = 0,
    ) -> CollectionTask | None:
        """标记任务完成 running → completed，自动生成下一周期任务。

        Args:
            task_id: 任务 ID
            last_cursor: 本次采集的最后一条评论 ID（用于增量采集）
            collected_count: 本次采集评论数
        """
        task = self._load(task_id)
        if not task:
            return None
        if not self._can_transition(task.status, "completed"):
            logger.warning("无法从 %s 转换到 completed (task=%s)", task.status, task_id)
            return None

        task.status = "completed"
        task.last_cursor = last_cursor
        task.last_collected_count = collected_count
        task.total_collected_count += collected_count
        task.retry_count = 0
        task.error_log = []
        task.last_run_time = task.last_run_time or _now()

        # 生成下一周期任务
        next_task_id = _derive_next_id(task_id)
        next_time = _next_schedule(_now(), task.collection_frequency)

        next_task = CollectionTask(
            task_id=next_task_id,
            platform=task.platform,
            account_id=task.account_id,
            account_name=task.account_name,
            account_category=task.account_category,
            collection_frequency=task.collection_frequency,
            priority=task.priority,
            video_filter=task.video_filter,
            comment_limit=task.comment_limit,
            status="pending",
            retry_count=0,
            max_retries=task.max_retries,
            last_cursor=last_cursor,  # 继承游标
            total_collected_count=task.total_collected_count,
            created_time=_now(),
            updated_time=_now(),
            next_run_time=next_time,
        )

        self._save(task)
        self._save(next_task)
        logger.info(
            "任务完成 %s (采集 %d 条, 游标=%s) → 下一周期 %s @%s",
            task_id, collected_count, last_cursor[:20] if last_cursor else "none",
            next_task_id, next_time,
        )
        return task

    def fail(self, task_id: str, error_type: str = "", error_message: str = "") -> CollectionTask | None:
        """标记任务失败 running → failed 或 failed_final。

        自动根据 retry_count 判断：未达上限则 failed（等待重试），达到上限 → failed_final。
        """
        task = self._load(task_id)
        if not task:
            return None
        if not self._can_transition(task.status, "failed"):
            logger.warning("无法从 %s 转换到 failed (task=%s)", task.status, task_id)
            return None

        task.retry_count += 1
        task.error_log.append(ErrorEntry(
            attempt=task.retry_count,
            time=_now(),
            error_type=error_type,
            error_message=error_message,
        ))

        if task.retry_count >= task.max_retries:
            task.status = "failed_final"
            logger.warning("任务 %s 已达最大重试次数 (%d/%d)", task_id, task.retry_count, task.max_retries)
        else:
            task.status = "failed"
            # 设置下次重试时间（退避）
            backoff_idx = min(task.retry_count - 1, len(RETRY_BACKOFF_MINUTES) - 1)
            retry_delay = RETRY_BACKOFF_MINUTES[backoff_idx]
            task.next_run_time = _now_offset(retry_delay)
            logger.info("任务 %s 失败 (第%d次), %d分钟后重试", task_id, task.retry_count, retry_delay)

        self._save(task)
        return task

    def retry(self, task_id: str) -> CollectionTask | None:
        """手动/自动重试失败任务 failed → running。"""
        task = self._load(task_id)
        if not task:
            return None
        if task.status == "failed" and self._can_transition("failed", "running"):
            task.status = "running"
            task.last_run_time = _now()
            self._save(task)
            logger.info("重试任务 %s (第%d次)", task_id, task.retry_count)
            return task
        logger.warning("任务 %s 无法重试 (status=%s)", task_id, task.status)
        return None

    def pause(self, task_id: str) -> CollectionTask | None:
        """暂停任务 running → paused。"""
        return self._transition(task_id, "paused")

    def resume(self, task_id: str) -> CollectionTask | None:
        """恢复任务 paused → running。"""
        return self._transition(task_id, "running")

    def cancel(self, task_id: str) -> CollectionTask | None:
        """取消任务。"""
        return self._transition(task_id, "cancelled")

    def _transition(self, task_id: str, target: str) -> CollectionTask | None:
        task = self._load(task_id)
        if not task:
            return None
        if not self._can_transition(task.status, target):
            logger.warning("无法从 %s 转换到 %s (task=%s)", task.status, target, task_id)
            return None
        task.status = target
        self._save(task)
        logger.info("任务 %s: %s → %s", task_id, task.status if task.status != target else "...", target)
        return task

    # ── 游标操作 ──

    def update_cursor(self, task_id: str, cursor: str) -> CollectionTask | None:
        """更新增量采集游标（运行中实时更新，不改变状态）。"""
        task = self._load(task_id)
        if not task:
            return None
        task.last_cursor = cursor
        self._save(task)
        return task

    def reset_cursor(self, task_id: str) -> CollectionTask | None:
        """重置游标 → 下次全量采集。"""
        task = self._load(task_id)
        if not task:
            return None
        task.last_cursor = ""
        self._save(task)
        logger.info("重置游标: %s", task_id)
        return task

    # ── 批量操作 ──

    def seed_from_accounts(
        self,
        accounts: list[dict[str, str]],
        platform: str | None = None,
    ) -> list[CollectionTask]:
        """从账号列表批量创建初始任务。

        为每个账号创建首次采集任务（pending, 立即执行）。

        Args:
            accounts: [{"account_id": "...", "account_name": "...", ...}, ...]
            platform: 统一平台（如果账号列表不含 platform 字段）

        Returns:
            创建的任务列表
        """
        created: list[CollectionTask] = []
        for acc in accounts:
            p = acc.get("platform", platform or "")
            if not p:
                continue
            aid = acc.get("account_id", "")
            if not aid:
                continue

            # 跳过已有活跃任务的账号
            if self.has_active_task(p, aid):
                logger.info("跳过 %s/%s: 已有活跃任务", p, aid)
                continue

            grade = acc.get("monitor_level", acc.get("grade", "B"))
            priority = "P0" if grade == "S" else "P1" if grade == "A" else "P2"
            freq = "6h" if grade == "S" else "daily" if grade == "A" else "weekly"

            task = self.create(
                platform=p,
                account_id=aid,
                account_name=acc.get("account_name", ""),
                account_category=acc.get("account_category", acc.get("account_type", "")),
                collection_frequency=freq,
                priority=priority,
                time_range_days=7 if priority == "P0" else 7,
            )
            created.append(task)

        logger.info("批量创建 %d 个任务（共 %d 个账号）", len(created), len(accounts))
        return created

    # ── 统计 ──

    def stats(self) -> dict[str, int]:
        """任务统计概览。"""
        all_tasks = self.list_all()
        counts: dict[str, int] = {}
        for t in all_tasks:
            counts[t.status] = counts.get(t.status, 0) + 1
        return dict(sorted(counts.items()))

    def clean_completed(self, keep_days: int = 7) -> int:
        """清理超过 N 天的已完成任务文件。"""
        cutoff = datetime.now(TZ_SHANGHAI) - timedelta(days=keep_days)
        removed = 0
        for t in self.list_by_status("completed"):
            try:
                t_time = datetime.strptime(t.updated_time, "%Y-%m-%d %H:%M:%S")
                t_time = t_time.replace(tzinfo=TZ_SHANGHAI)
                if t_time < cutoff:
                    self._delete(t.task_id)
                    removed += 1
            except (ValueError, TypeError):
                pass
        logger.info("清理 %d 个过期任务 (>%d天)", removed, keep_days)
        return removed


# ── 辅助函数 ──

def _now() -> str:
    return datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")


def _now_offset(minutes: int) -> str:
    return (datetime.now(TZ_SHANGHAI) + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")


def _next_schedule(from_time: str, frequency: str) -> str:
    """计算下次执行时间。"""
    try:
        ts = datetime.strptime(from_time, "%Y-%m-%d %H:%M:%S")
        ts = ts.replace(tzinfo=TZ_SHANGHAI)
    except (ValueError, TypeError):
        ts = datetime.now(TZ_SHANGHAI)

    delta = FREQUENCY_INTERVALS.get(frequency, timedelta(hours=6))
    return (ts + delta).strftime("%Y-%m-%d %H:%M:%S")


def _next_seq(tasks_dir: Path, platform: str, account_id: str, today: str) -> int:
    """计算下一个任务序号。"""
    prefix = f"{platform}_{account_id}_{today}_"
    existing = list(tasks_dir.glob(f"{prefix}*.json"))
    if not existing:
        return 1
    nums = []
    for f in existing:
        try:
            nums.append(int(f.stem.rsplit("_", 1)[-1]))
        except (ValueError, IndexError):
            pass
    return max(nums) + 1 if nums else 1


def _derive_next_id(current_id: str) -> str:
    """从当前 task_id 推导下一周期 task_id。

    格式: {platform}_{account_id}_{YYYYMMDD}_{seq}
    日期更新为今天，序号为同平台同账号今天已存在的最大序号+1。
    """
    parts = current_id.rsplit("_", 2)  # ["douyin", "acc001", "20260720", "001"]
    if len(parts) < 4:
        return f"{current_id}_{_now()[:10].replace('-', '')}_001"

    platform, account_id = parts[0], parts[1]
    today = datetime.now(TZ_SHANGHAI).strftime("%Y%m%d")
    seq = _next_seq(TASKS_DIR, platform, account_id, today)
    return f"{platform}_{account_id}_{today}_{seq:03d}"


# ── CLI 自检 ──
if __name__ == "__main__":
    print("=" * 50)
    print("  PV_OS Task Manager — 自检")
    print("=" * 50)

    tm = TaskManager()
    print(f"  存储目录: {tm.tasks_dir}")

    # 创建测试任务
    task = tm.create(
        platform="douyin",
        account_id="test_acc_001",
        account_name="成都光伏老王",
        account_category="regional_installer",
        collection_frequency="6h",
        priority="P0",
    )
    print(f"\n  ✓ 创建任务: {task.task_id}")
    print(f"    状态: {task.status}")
    print(f"    下次执行: {task.next_run_time}")

    # 状态流转
    tm.start(task.task_id)
    t = tm.get(task.task_id)
    print(f"    start → {t.status}")

    tm.complete(task.task_id, last_cursor="comment_456", collected_count=50)
    t = tm.get(task.task_id)
    print(f"    complete → {t.status}, 游标={t.last_cursor}")

    # 下一周期任务
    pending = tm.get_pending()
    print(f"\n  ✓ 下一周期任务: {len(pending)} 个待执行")

    # 统计
    print(f"\n  ✓ 任务统计: {tm.stats()}")

    # 清理
    tm.clean_completed(keep_days=0)
    print(f"  ✓ 清理后统计: {tm.stats()}")
    print()
