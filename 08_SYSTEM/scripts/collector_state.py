"""PV_OS 采集器状态管理。

为 Collector 提供游标、分页、统计等运行时状态持久化能力。
与 TaskModel 的 last_cursor 协作，但不依赖 TaskModel。

Usage::

    from collector_state import CollectorState, CollectorLogger

    state = CollectorState(platform="douyin", account_id="acc_001")
    state.update_cursor(video_cursor="page_2", comment_id="c_789")
    state.to_dict()  # 可持久化到 JSON

    logger = CollectorLogger(platform="douyin")
    logger.log_collection(state, duration_seconds=12.5)
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

TZ_SHANGHAI = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ_SHANGHAI)
NOW_STR = lambda: NOW().strftime("%Y-%m-%d %H:%M:%S")

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# CollectorState — 采集运行时状态
# ══════════════════════════════════════════════════════════════════════

@dataclass
class PaginationState:
    """分页状态。"""
    has_more: bool = True
    next_cursor: str = ""
    current_page: int = 0
    total_pages: int = 0


@dataclass
class CollectorState:
    """采集器运行时状态。

    与 TaskModel.last_cursor 兼容:
    - last_comment_id 对应 TaskModel.last_cursor
    - 采集完成后，调用方将 last_comment_id 写入 TaskModel
    """

    # ── 标识 ──
    platform: str = ""
    account_id: str = ""
    account_name: str = ""

    # ── 游标 (增量采集锚点) ──
    last_video_cursor: str = ""      # 视频列表分页游标
    last_comment_cursor: str = ""    # 评论列表分页游标
    last_comment_id: str = ""        # 最后一条评论原始 ID → TaskModel.last_cursor

    # ── 分页 ──
    video_pagination: PaginationState = field(default_factory=PaginationState)
    comment_pagination: PaginationState = field(default_factory=PaginationState)

    # ── 统计 ──
    total_videos_fetched: int = 0
    total_comments_fetched: int = 0
    total_comments_valid: int = 0
    total_comments_saved: int = 0

    # ── 时间 ──
    run_start_time: str = ""
    last_run_time: str = ""
    last_video_fetch_time: str = ""
    last_comment_fetch_time: str = ""

    # ── 错误 ──
    error_count: int = 0
    last_error: str = ""
    last_error_time: str = ""

    # ── 元数据 ──
    mode: str = "mock"               # mock | live
    api_available: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    # ── 游标操作 ──

    def update_video_cursor(self, cursor: str, has_more: bool = True) -> None:
        """更新视频列表分页游标。"""
        self.last_video_cursor = cursor
        self.video_pagination.has_more = has_more
        self.video_pagination.next_cursor = cursor
        self.video_pagination.current_page += 1
        self.last_video_fetch_time = NOW_STR()

    def update_comment_cursor(self, cursor: str, comment_id: str, has_more: bool = True) -> None:
        """更新评论列表分页游标和最后一条评论 ID。"""
        self.last_comment_cursor = cursor
        self.last_comment_id = comment_id
        self.comment_pagination.has_more = has_more
        self.comment_pagination.next_cursor = cursor
        self.comment_pagination.current_page += 1
        self.last_comment_fetch_time = NOW_STR()

    def add_videos(self, count: int) -> None:
        self.total_videos_fetched += count

    def add_comments(self, fetched: int, valid: int) -> None:
        self.total_comments_fetched += fetched
        self.total_comments_valid += valid

    def add_saved(self, count: int) -> None:
        self.total_comments_saved += count

    def record_error(self, error_msg: str) -> None:
        self.error_count += 1
        self.last_error = error_msg
        self.last_error_time = NOW_STR()

    def mark_run_start(self) -> None:
        self.run_start_time = NOW_STR()
        self.last_run_time = self.run_start_time

    def reset_pagination(self) -> None:
        """重置分页状态（新采集周期）。"""
        self.video_pagination = PaginationState()
        self.comment_pagination = PaginationState()

    # ── 兼容 TaskModel ──

    def get_task_cursor(self) -> str:
        """返回与 TaskModel.last_cursor 兼容的游标值。"""
        return self.last_comment_id

    def has_new_data(self, previous_cursor: str) -> bool:
        """判断自上次采集后是否有新数据。"""
        return self.last_comment_id != previous_cursor

    # ── 序列化 ──

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["video_pagination"] = asdict(self.video_pagination)
        d["comment_pagination"] = asdict(self.comment_pagination)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CollectorState":
        vp = data.pop("video_pagination", {})
        cp = data.pop("comment_pagination", {})

        state = cls(**data)
        state.video_pagination = PaginationState(**vp) if isinstance(vp, dict) else vp
        state.comment_pagination = PaginationState(**cp) if isinstance(cp, dict) else cp
        return state

    def save(self, path: Path) -> None:
        """保存状态到 JSON 文件。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> "CollectorState":
        """从 JSON 文件加载状态。"""
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)


# ══════════════════════════════════════════════════════════════════════
# CollectorLogger — 采集执行日志
# ══════════════════════════════════════════════════════════════════════

@dataclass
class CollectionLogEntry:
    """单次采集的执行日志条目。"""
    run_id: str = ""
    platform: str = ""
    account_id: str = ""
    account_name: str = ""
    mode: str = "mock"

    # 时间
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0

    # 结果
    videos_fetched: int = 0
    comments_fetched: int = 0
    comments_valid: int = 0
    comments_saved: int = 0

    # 游标
    start_cursor: str = ""
    end_cursor: str = ""
    cursor_changed: bool = False

    # 分页
    video_pages: int = 0
    comment_pages: int = 0

    # 速率
    rate_limit_waits: int = 0
    rate_limit_wait_seconds: float = 0.0

    # 错误
    errors: int = 0
    last_error: str = ""
    status: str = "success"         # success | partial | failed

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CollectorLogger:
    """采集执行日志管理。

    日志按日期归档: logs/collector/{platform}/{YYYY-MM-DD}.json
    """

    def __init__(self, platform: str, logs_dir: Path | None = None) -> None:
        self.platform = platform
        self.logs_dir = logs_dir or Path(__file__).resolve().parent.parent.parent / "logs" / "collector"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def create_entry(
        self,
        account_id: str = "",
        account_name: str = "",
        mode: str = "mock",
    ) -> CollectionLogEntry:
        """创建新的日志条目（标记开始时间）。"""
        return CollectionLogEntry(
            run_id=NOW().strftime("%Y%m%d%H%M%S"),
            platform=self.platform,
            account_id=account_id,
            account_name=account_name,
            mode=mode,
            start_time=NOW_STR(),
        )

    def finalize_entry(
        self,
        entry: CollectionLogEntry,
        state: CollectorState,
        status: str = "success",
    ) -> CollectionLogEntry:
        """填充日志条目的结束字段。"""
        entry.end_time = NOW_STR()
        try:
            start_dt = datetime.strptime(entry.start_time, "%Y-%m-%d %H:%M:%S")
            start_dt = start_dt.replace(tzinfo=TZ_SHANGHAI)
            entry.duration_seconds = (NOW() - start_dt).total_seconds()
        except (ValueError, TypeError):
            entry.duration_seconds = 0

        entry.videos_fetched = state.total_videos_fetched
        entry.comments_fetched = state.total_comments_fetched
        entry.comments_valid = state.total_comments_valid
        entry.comments_saved = state.total_comments_saved
        entry.end_cursor = state.last_comment_id
        entry.cursor_changed = entry.start_cursor != entry.end_cursor
        entry.video_pages = state.video_pagination.current_page
        entry.comment_pages = state.comment_pagination.current_page
        entry.errors = state.error_count
        entry.last_error = state.last_error
        entry.status = status

        return entry

    def write_log(self, entry: CollectionLogEntry) -> Path:
        """写入一天日志文件（追加模式）。"""
        today = NOW().strftime("%Y-%m-%d")
        platform_dir = self.logs_dir / self.platform
        platform_dir.mkdir(parents=True, exist_ok=True)
        log_file = platform_dir / f"{today}.json"

        existing: list[dict] = []
        if log_file.exists():
            try:
                existing = json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = []

        existing.append(entry.to_dict())
        log_file.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("采集日志 → %s (%d entries)", log_file.name, len(existing))
        return log_file

    def get_today_entries(self) -> list[dict[str, Any]]:
        today = NOW().strftime("%Y-%m-%d")
        log_file = self.logs_dir / self.platform / f"{today}.json"
        if log_file.exists():
            try:
                return json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return []


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Collector State & Logger — 自检")
    print("=" * 60)

    # CollectorState
    print("\n── CollectorState ──")
    state = CollectorState(platform="douyin", account_id="acc_001", account_name="测试")
    state.mark_run_start()
    state.update_video_cursor("video_page_2", has_more=True)
    state.update_comment_cursor("comment_page_3", "dy_c_789", has_more=True)
    state.add_videos(8)
    state.add_comments(fetched=50, valid=45)
    state.add_saved(45)

    print(f"  视频游标: {state.last_video_cursor}")
    print(f"  评论游标: {state.last_comment_id}")
    print(f"  视频分页: page {state.video_pagination.current_page}, has_more={state.video_pagination.has_more}")
    print(f"  统计: {state.total_videos_fetched}视频/{state.total_comments_fetched}评论/{state.total_comments_valid}有效")

    # 序列化
    d = state.to_dict()
    restored = CollectorState.from_dict(d)
    assert restored.last_comment_id == "dy_c_789"
    print("  ✓ 序列化往返正确")

    # 保存/加载
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test_state.json"
        state.save(path)
        loaded = CollectorState.load(path)
        assert loaded.last_comment_id == "dy_c_789"
        print("  ✓ 文件保存/加载正确")

    # CollectorLogger
    print("\n── CollectorLogger ──")
    with tempfile.TemporaryDirectory() as tmp:
        clog = CollectorLogger("douyin", logs_dir=Path(tmp))
        entry = clog.create_entry(account_id="acc_001", account_name="测试", mode="mock")
        entry.start_cursor = "dy_c_100"
        clog.finalize_entry(entry, state, status="success")
        log_path = clog.write_log(entry)
        print(f"  日志文件: {log_path}")
        print(f"  Entry: run_id={entry.run_id}, status={entry.status}, duration={entry.duration_seconds:.1f}s")
        print("  ✓ CollectorLogger 自检通过")

    print()
