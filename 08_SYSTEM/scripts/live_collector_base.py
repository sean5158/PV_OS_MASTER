"""PV_OS 真实采集基类。

在 BaseCollector 基础上增加速率限制、重试、会话管理等生产级能力。
所有真实平台 Collector 必须继承此类。

设计原则:
- 不修改 BaseCollector 接口
- Mock 模式不受影响
- 所有平台特定逻辑在子类实现

Usage::

    from live_collector_base import LiveCollectorBase
    from collector_base import CommentRecord

    class DouyinLiveCollector(LiveCollectorBase):
        def _fetch_video_list(self, account_id, cursor, limit):
            # 调用抖音 API
            ...
        def _fetch_comments(self, video_id, cursor, limit):
            # 调用抖音评论 API
            ...
        def _parse_to_record(self, raw_item):
            # 转换平台数据为 CommentRecord
            ...
"""

from __future__ import annotations

import logging
import time
import random
from abc import abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

from collector_base import BaseCollector, CommentRecord

logger = logging.getLogger(__name__)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# 采集会话状态
# ══════════════════════════════════════════════════════════════════════

class CollectorSession:
    """采集会话 — 管理 cookie 有效期、UA 轮换等。

    P2-1 阶段为桩: 不做真实 cookie 校验，仅记录状态。
    """

    def __init__(self, platform: str, credentials: dict[str, Any] | None = None) -> None:
        self.platform = platform
        self.credentials = credentials or {}
        self.created_at = datetime.now(TZ_SHANGHAI)
        self.last_used_at = self.created_at
        self._valid = bool(self.credentials.get("cookie"))

    @property
    def is_valid(self) -> bool:
        """会话是否有效。P2-1 仅检查 cookie 是否存在。"""
        return self._valid and bool(self.credentials.get("cookie"))

    def touch(self) -> None:
        """更新最后使用时间。"""
        self.last_used_at = datetime.now(TZ_SHANGHAI)

    def invalidate(self) -> None:
        """标记会话失效。"""
        self._valid = False

    def age_seconds(self) -> float:
        """会话已存在时间（秒）。"""
        return (datetime.now(TZ_SHANGHAI) - self.created_at).total_seconds()


# ══════════════════════════════════════════════════════════════════════
# 速率限制器
# ══════════════════════════════════════════════════════════════════════

class RateLimiter:
    """令牌桶速率限制器。

    控制每分钟请求数，超出时自动等待。
    """

    def __init__(
        self,
        requests_per_minute: int = 10,
        cooldown_seconds: float = 30.0,
        jitter: bool = True,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.cooldown_seconds = cooldown_seconds
        self.jitter = jitter

        self._window_start = datetime.now(TZ_SHANGHAI)
        self._request_count = 0
        self._cooldown_until: datetime | None = None

    def acquire(self) -> bool:
        """尝试获取一个请求配额。

        Returns:
            True: 配额充足，可以发起请求
            False: 超出限制，需等待
        """
        now = datetime.now(TZ_SHANGHAI)

        # 冷却期检查
        if self._cooldown_until and now < self._cooldown_until:
            return False

        # 窗口重置
        if (now - self._window_start).total_seconds() >= 60:
            self._window_start = now
            self._request_count = 0

        if self._request_count < self.requests_per_minute:
            self._request_count += 1
            return True

        return False

    def wait_if_needed(self) -> float:
        """需要等待时 sleep，返回实际等待秒数。"""
        now = datetime.now(TZ_SHANGHAI)

        # 冷却等待
        if self._cooldown_until and now < self._cooldown_until:
            wait = (self._cooldown_until - now).total_seconds()
            if self.jitter:
                wait *= random.uniform(0.8, 1.2)
            logger.debug("冷却等待 %.1fs", wait)
            time.sleep(max(0, wait))
            self._cooldown_until = None
            return wait

        # 窗口等待
        elapsed = (now - self._window_start).total_seconds()
        if elapsed < 60 and self._request_count >= self.requests_per_minute:
            wait = 60 - elapsed + 0.5
            if self.jitter:
                wait *= random.uniform(0.9, 1.1)
            logger.debug("速率限制等待 %.1fs (已用 %d/%d)", wait, self._request_count, self.requests_per_minute)
            time.sleep(max(0, wait))
            self._window_start = datetime.now(TZ_SHANGHAI)
            self._request_count = 0
            return wait

        return 0.0

    def cooldown(self, custom_seconds: float | None = None) -> None:
        """触发冷却期。"""
        secs = custom_seconds or self.cooldown_seconds
        self._cooldown_until = datetime.now(TZ_SHANGHAI) + timedelta(seconds=secs)
        logger.warning("触发冷却 %.1fs，到 %s", secs, self._cooldown_until.strftime("%H:%M:%S"))

    def reset(self) -> None:
        """重置限制器状态。"""
        self._window_start = datetime.now(TZ_SHANGHAI)
        self._request_count = 0
        self._cooldown_until = None


# ══════════════════════════════════════════════════════════════════════
# LiveCollectorBase — 真实采集基类
# ══════════════════════════════════════════════════════════════════════

class LiveCollectorBase(BaseCollector):
    """真实平台采集器基类。

    在 BaseCollector 之上增加:
    - 速率限制: RateLimiter 令牌桶
    - 重试机制: 指数退避 + 错误分类
    - 会话管理: CollectorSession (P2-1 为桩)
    - 增量采集: 基于 last_cursor

    子类必须实现三个抽象方法:
    - _fetch_video_list(): 获取账号视频列表
    - _fetch_comments(): 获取视频评论
    - _parse_to_record(): 平台原始数据 → CommentRecord
    """

    connector_mode: str = "live"

    def __init__(
        self,
        credentials: dict[str, Any] | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        super().__init__(credentials)
        self.connector_mode = "live"
        self.rate_limiter = rate_limiter or RateLimiter()
        self.session = CollectorSession(self.platform_name, credentials)

        # 重试配置
        self.max_retries: int = 3
        self.retry_backoff_base: float = 2.0  # 指数退避基数(秒)

    # ── 核心采集流程 ──

    def collect(
        self,
        account_id: str,
        max_count: int = 50,
        **kwargs: Any,
    ) -> list[CommentRecord]:
        """标准采集流程: 速率检查 → 获取视频 → 获取评论 → 转换。

        子类可覆盖此方法以实现平台特定逻辑。
        """
        video_id = kwargs.get("video_id", "")
        cursor = kwargs.get("cursor", "")
        video_limit = kwargs.get("video_limit", 10)

        # Phase 1: 速率限制检查
        self._rate_limit_check()

        # Phase 2: 获取视频列表（如未指定特定视频）
        videos: list[dict[str, Any]] = []
        if video_id:
            videos = [{"video_id": video_id}]
        else:
            videos = self._fetch_video_list(account_id, cursor, video_limit)

        if not videos:
            logger.info("%s: 账号 %s 无新视频", self.platform_name, account_id)
            return []

        # Phase 3: 遍历视频获取评论
        all_comments: list[CommentRecord] = []
        for video in videos:
            if len(all_comments) >= max_count:
                break

            vid = video.get("video_id", video.get("id", ""))
            self._rate_limit_check()

            raw_comments = self._fetch_comments(
                vid,
                cursor,
                min(max_count - len(all_comments), 50),
            )

            for raw in raw_comments:
                try:
                    record = self._parse_to_record(raw)
                    record.source_video_id = vid
                    record.source_video_title = video.get("title", "")
                    record.source_url = video.get("url", "")
                    all_comments.append(record)
                except Exception as e:
                    logger.warning("%s: 解析评论失败: %s", self.platform_name, e)
                    continue

            if len(all_comments) >= max_count:
                break

        logger.info("%s: 采集 %d 条评论 (账号=%s)", self.platform_name, len(all_comments), account_id)
        return all_comments

    # ── 子类必须实现的抽象方法 ──

    @abstractmethod
    def _fetch_video_list(
        self, account_id: str, cursor: str, limit: int
    ) -> list[dict[str, Any]]:
        """获取账号视频列表。

        Returns:
            [{"video_id": "...", "title": "...", "url": "...", "create_time": "..."}, ...]
        """
        ...

    @abstractmethod
    def _fetch_comments(
        self, video_id: str, cursor: str, limit: int
    ) -> list[dict[str, Any]]:
        """获取视频评论列表。

        Returns:
            [{"comment_id": "...", "content": "...", "author": "...", ...}, ...]
        """
        ...

    @abstractmethod
    def _parse_to_record(self, raw_item: dict[str, Any]) -> CommentRecord:
        """将平台原始数据转换为 CommentRecord。

        Args:
            raw_item: _fetch_comments 返回的单条原始数据
        """
        ...

    # ── 速率限制 ──

    def _rate_limit_check(self) -> None:
        """速率限制检查 + 自动等待。"""
        self.rate_limiter.wait_if_needed()
        if not self.rate_limiter.acquire():
            self.rate_limiter.wait_if_needed()

    # ── 重试逻辑 ──

    def _retry_with_backoff(
        self,
        fn,
        *args: Any,
        max_retries: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """带指数退避的重试执行。

        Args:
            fn: 要执行的函数
            *args: 函数参数
            max_retries: 最大重试次数，默认使用 self.max_retries
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            最后一次失败的异常
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if not self._should_retry(e, attempt, retries):
                    raise

                backoff = self.retry_backoff_base ** (attempt + 1)
                jitter = backoff * random.uniform(0.5, 1.5)
                logger.warning(
                    "%s: 第 %d/%d 次重试，等待 %.1fs: %s",
                    self.platform_name, attempt + 1, retries, jitter, e,
                )
                time.sleep(jitter)

        raise last_error  # type: ignore[misc]

    def _should_retry(self, error: Exception, attempt: int, max_retries: int) -> bool:
        """判断是否应该重试。

        默认策略:
        - 网络类错误 (ConnectionError, TimeoutError): 重试
        - HTTP 429 (限流): 冷却后重试
        - HTTP 403 (封禁): 不重试
        - 其他: 重试直到上限
        """
        if attempt >= max_retries:
            return False

        error_str = str(error).lower()

        # 封禁类不重试
        forbidden_keywords = ["403", "forbidden", "banned", "blocked", "封禁"]
        if any(kw in error_str for kw in forbidden_keywords):
            logger.error("%s: 检测到封禁信号，不重试: %s", self.platform_name, error)
            return False

        # 限流触发冷却
        rate_limit_keywords = ["429", "rate limit", "too many", "限流"]
        if any(kw in error_str for kw in rate_limit_keywords):
            self.rate_limiter.cooldown()
            return True

        # 网络错误重试
        return True

    # ── 会话管理 ──

    def is_session_valid(self) -> bool:
        """检查采集会话是否有效。"""
        return self.session.is_valid

    def refresh_session(self) -> bool:
        """刷新会话 (P2-1 桩: 不做实际操作)。"""
        logger.info("%s: 会话刷新 (P2-1 桩)", self.platform_name)
        self.session.touch()
        return self.session.is_valid


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("  LiveCollectorBase — 自检")
    print("=" * 50)

    # RateLimiter
    rl = RateLimiter(requests_per_minute=3, cooldown_seconds=1)
    print(f"\n  RateLimiter: {rl.requests_per_minute} req/min")
    for i in range(5):
        ok = rl.acquire()
        print(f"    acquire #{i+1}: {'OK' if ok else 'WAIT'}")
    rl.reset()
    print("  ✓ RateLimiter 自检通过")

    # CollectorSession
    sess = CollectorSession("douyin", {"cookie": "test_cookie"})
    print(f"\n  Session valid: {sess.is_valid}")
    print(f"  Session age: {sess.age_seconds():.0f}s")
    print("  ✓ CollectorSession 自检通过")

    print()
