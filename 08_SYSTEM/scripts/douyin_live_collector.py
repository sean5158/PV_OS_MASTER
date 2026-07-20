"""PV_OS 抖音真实采集器。

继承 LiveCollectorBase，实现抖音平台评论采集。
当前为架构框架：接口完整，API 实现标为 TODO，失败自动降级 Mock。

架构::

    DouyinLiveCollector(LiveCollectorBase)
    ├─ collect()              # 继承: 速率限制 + 视频获取 + 评论采集
    ├─ _fetch_video_list()    # 抖音视频列表 (TODO: 真实API)
    ├─ _fetch_comments()      # 抖音评论获取 (TODO: 真实API)
    └─ _parse_to_record()     # 抖音数据→CommentRecord

使用方式::

    from platform_adapter import get_collector
    collector = get_collector("douyin", mode="live")
    collector.collect_and_save(account_id="xxx", account_name="某光伏博主")

降级策略:
    - 凭证缺失 → 自动降级 Mock (Platform Adapter 层)
    - API 未实现 → 使用 Mock 数据 (本层 fallback)
    - 网络错误 → 指数退避重试 (LiveCollectorBase)

Mock 模式覆盖场景:
    别墅/叠拼报价 | 区域安装咨询 | 叠拼省钱 | 顶楼装光伏 |
    民宿小商业 | 农村自建房 | 纯讨论 (P0 已定义 6 种场景)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from collector_base import CommentRecord
from live_collector_base import LiveCollectorBase, RateLimiter
from collector_state import CollectorState, CollectorLogger, CollectionLogEntry

logger = logging.getLogger(__name__)

TZ_SHANGHAI = timezone(timedelta(hours=8))

# ── 抖音 Mock 数据 ──
# 覆盖城市家庭光伏全部业务场景，保持与 douyin_connector.py 数据一致

DOUYIN_MOCK_VIDEOS: list[dict[str, Any]] = [
    {
        "video_id": "dy_video_001",
        "title": "成都别墅光伏安装实拍案例",
        "url": "https://www.douyin.com/video/dy_video_001",
        "create_time": "2026-07-19 10:00:00",
        "topic": "别墅光伏",
    },
    {
        "video_id": "dy_video_002",
        "title": "叠拼别墅光伏省钱实拍",
        "url": "https://www.douyin.com/video/dy_video_002",
        "create_time": "2026-07-18 15:00:00",
        "topic": "叠拼光伏省钱",
    },
    {
        "video_id": "dy_video_003",
        "title": "光伏发电能用多少年科普",
        "url": "https://www.douyin.com/video/dy_video_003",
        "create_time": "2026-07-17 11:00:00",
        "topic": "光伏科普",
    },
    {
        "video_id": "dy_video_004",
        "title": "民宿光伏发电改造案例",
        "url": "https://www.douyin.com/video/dy_video_004",
        "create_time": "2026-07-20 08:00:00",
        "topic": "民宿光伏",
    },
]

DOUYIN_MOCK_COMMENTS: dict[str, list[dict[str, Any]]] = {
    "dy_video_001": [
        {
            "comment_id": "dy_real_001",
            "content": "我在成都这边，家里是别墅，想装一套光伏发电，能报个价吗？",
            "author": "成都张先生",
            "create_time": "2026-07-20 10:00:00",
            "ip_location": "四川成都",
            "like_count": "12",
        },
        {
            "comment_id": "dy_real_002",
            "content": "绵阳有没有做光伏安装的？大概多少钱一平方？",
            "author": "绵阳小王",
            "create_time": "2026-07-20 09:30:00",
            "ip_location": "四川绵阳",
            "like_count": "5",
        },
    ],
    "dy_video_002": [
        {
            "comment_id": "dy_real_003",
            "content": "重庆渝北的，叠拼别墅，装了光伏一年能省多少电费？",
            "author": "重庆老李",
            "create_time": "2026-07-19 15:00:00",
            "ip_location": "重庆",
            "like_count": "23",
        },
    ],
    "dy_video_003": [
        {
            "comment_id": "dy_real_004",
            "content": "这个光伏板能用多少年？我家顶楼想装",
            "author": "贵阳老陈",
            "create_time": "2026-07-19 11:00:00",
            "ip_location": "贵州贵阳",
            "like_count": "8",
        },
        {
            "comment_id": "dy_real_005",
            "content": "光伏发电靠谱吗？我朋友说用几年就不行了，是真的吗？",
            "author": "观望者老刘",
            "create_time": "2026-07-15 10:00:00",
            "ip_location": "四川德阳",
            "like_count": "3",
        },
    ],
    "dy_video_004": [
        {
            "comment_id": "dy_real_006",
            "content": "我在成都开了个民宿，装光伏能省多少钱？有联系方式吗",
            "author": "民宿老板赵哥",
            "create_time": "2026-07-20 07:00:00",
            "ip_location": "四川成都",
            "like_count": "31",
        },
        {
            "comment_id": "dy_real_007",
            "content": "农村自建房想装光伏，有没有补贴啊？",
            "author": "德阳老刘",
            "create_time": "2026-07-18 08:00:00",
            "ip_location": "四川德阳",
            "like_count": "15",
        },
    ],
}


class DouyinLiveCollector(LiveCollectorBase):
    """抖音真实平台采集器。

    当前状态: 架构框架 (P2-3 第一阶段)
    - 接口完整: _fetch_video_list / _fetch_comments / _parse_to_record
    - API 实现: TODO (标记为 P2-4)
    - 降级 Mock: 凭证无效或 API 不可用时自动使用 Mock 数据

    生产就绪后对接:
    1. 抖音开放平台 API (需企业认证)
    2. 第三方数据服务商 SDK
    3. 浏览器自动化 (Playwright/Selenium) — 最后手段

    业务边界:
    ✅ 城市家庭光伏 / 别墅/叠拼 / 小商业 (民宿)
    ❌ 农村光伏 / 大型工商业光伏
    """

    def __init__(
        self,
        credentials: dict[str, Any] | None = None,
        rate_limiter: RateLimiter | None = None,
        last_cursor: str = "",
        state_dir: str = "",
    ) -> None:
        super().__init__(credentials, rate_limiter)
        # 覆盖 BaseCollector 的类名推导
        self.platform_name = "douyin"
        # 同时更新 session 的平台名
        self.session.platform = "douyin"

        # P2-3: 检测真实 API 可用性
        self._api_available = self._check_api_availability()
        if not self._api_available:
            logger.info("抖音: API 不可用，使用 Mock 降级模式")

        # P2-4: 状态管理
        self._collector_logger = CollectorLogger(
            "douyin",
            logs_dir=Path(state_dir) if state_dir else None,
        )
        self._state: CollectorState | None = None

        # 从 TaskModel 传入的游标
        self._initial_cursor = last_cursor

    # ── 抽象方法实现 ──

    def _fetch_video_list(
        self, account_id: str, cursor: str, limit: int
    ) -> list[dict[str, Any]]:
        """获取抖音账号视频列表。

        TODO (P2-4): 对接抖音开放平台 API
        接口: /video/list/
        参数: sec_uid, cursor, count

        P2-3: 返回 Mock 数据作为降级
        """
        if self._api_available:
            return self._fetch_video_list_live(account_id, cursor, limit)
        else:
            return self._fetch_video_list_mock(account_id, limit)

    def _fetch_comments(
        self, video_id: str, cursor: str, limit: int
    ) -> list[dict[str, Any]]:
        """获取抖音视频评论列表。

        TODO (P2-4): 对接抖音开放平台 API
        接口: /comment/list/
        参数: item_id, cursor, count

        P2-3: 返回 Mock 数据作为降级
        """
        if self._api_available:
            return self._fetch_comments_live(video_id, cursor, limit)
        else:
            return self._fetch_comments_mock(video_id, limit)

    def _parse_to_record(self, raw_item: dict[str, Any]) -> CommentRecord:
        """抖音原始评论数据 → CommentRecord。

        抖音字段映射:
            comment_id       → comment_id
            content          → content
            author           → author (昵称脱敏)
            create_time      → create_time
            ip_location      → ip_location
            like_count       → like_count
        """
        return CommentRecord(
            comment_id=str(raw_item.get("comment_id", "")),
            platform="douyin",
            content=str(raw_item.get("content", "")),
            author=str(raw_item.get("author", "")),
            create_time=str(raw_item.get("create_time", "")),
            ip_location=str(raw_item.get("ip_location", "")),
            like_count=int(raw_item.get("like_count", 0)),
            collected_time=datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"),
            processing_status="collected",
        )

    # ── API 可用性检测 ──

    def _check_api_availability(self) -> bool:
        """检测抖音真实 API 是否可用。

        P2-3: 检查凭证中是否包含 api_key 或有效的 cookie。
        返回 False 时自动降级 Mock。
        """
        if not self.credentials:
            return False

        # 有 api_key → 认为 API 可用
        if self.credentials.get("api_key"):
            return True

        # 有 cookie → 认为可尝试 (但 P2-3 不实际调用)
        if self.credentials.get("cookie"):
            # P2-3: 暂不验证 cookie 是否有效，标记为可用
            # P2-4: 增加 cookie 有效性探活
            return True

        return False

    # ── Mock 降级实现 (P2-3) ──

    def _fetch_video_list_mock(
        self, account_id: str, limit: int
    ) -> list[dict[str, Any]]:
        """Mock 视频列表 — 用于降级和测试。

        返回 4 个预置视频，覆盖别墅/叠拼/科普/民宿场景。
        """
        logger.info("抖音 Mock: 返回 %d 个视频 (账号=%s)", min(limit, len(DOUYIN_MOCK_VIDEOS)), account_id)
        return DOUYIN_MOCK_VIDEOS[:limit]

    def _fetch_comments_mock(
        self, video_id: str, limit: int
    ) -> list[dict[str, Any]]:
        """Mock 评论数据 — 用于降级和测试。

        按 video_id 返回预置评论，覆盖:
        - 别墅报价 (dy_video_001)
        - 区域安装咨询 (dy_video_001)
        - 叠拼省钱 (dy_video_002)
        - 顶楼光伏 (dy_video_003)
        - 科普讨论 (dy_video_003)
        - 民宿小商业 (dy_video_004)
        - 农村自建房 (dy_video_004, 业务边界外但保留用于测试)
        """
        comments = DOUYIN_MOCK_COMMENTS.get(video_id, [])
        logger.info("抖音 Mock: 视频 %s → %d 条评论", video_id, min(limit, len(comments)))
        return comments[:limit]

    # ── 真实 API 桩 (P2-4 实现) ──

    def _fetch_video_list_live(
        self, account_id: str, cursor: str, limit: int
    ) -> list[dict[str, Any]]:
        """真实 API: 获取抖音账号视频列表。

        TODO (P2-4):
        1. 构造请求: GET https://open.douyin.com/video/list/
        2. 签名: MD5(参数+client_secret)
        3. 解析响应: data.list[] → {video_id, title, url, create_time}
        4. 翻页: 使用 cursor 参数
        """
        logger.warning("抖音 Live API: _fetch_video_list_live 待实现 (P2-4)")
        return self._fetch_video_list_mock(account_id, limit)

    def _fetch_comments_live(
        self, video_id: str, cursor: str, limit: int
    ) -> list[dict[str, Any]]:
        """真实 API: 获取抖音视频评论。

        TODO (P2-4):
        1. 构造请求: GET https://open.douyin.com/comment/list/
        2. 签名: MD5(参数+client_secret)
        3. 解析响应: data.list[] → {comment_id, content, author, create_time, ip_location, like_count}
        4. 翻页: 使用 cursor 参数
        """
        logger.warning("抖音 Live API: _fetch_comments_live 待实现 (P2-4)")
        return self._fetch_comments_mock(video_id, limit)

    # ── P2-4: 增强采集 (cursor + 分页 + 状态) ──

    def collect_with_state(
        self,
        account_id: str,
        account_name: str = "",
        max_count: int = 50,
        last_cursor: str = "",
        **kwargs: Any,
    ) -> tuple[list[CommentRecord], CollectorState]:
        """增强采集：带游标、分页、状态追踪。

        Args:
            account_id: 竞品账号 ID
            account_name: 竞品账号名称
            max_count: 最大采集数
            last_cursor: 上次采集的最后评论 ID (增量采集锚点)

        Returns:
            (评论列表, 采集状态)
        """
        # 初始化状态
        self._state = CollectorState(
            platform="douyin",
            account_id=account_id,
            account_name=account_name,
            mode="live" if self._api_available else "mock",
            api_available=self._api_available,
        )
        self._state.mark_run_start()

        # 日志
        log_entry = self._collector_logger.create_entry(
            account_id=account_id,
            account_name=account_name,
            mode=self._state.mode,
        )
        log_entry.start_cursor = last_cursor or self._initial_cursor

        all_comments: list[CommentRecord] = []
        status = "success"

        try:
            # Phase 1: 分页获取视频列表
            self._collect_videos_paginated(account_id, **kwargs)

            # Phase 2: 分页获取评论
            all_comments = self._collect_comments_paginated(
                max_count,
                last_cursor=last_cursor or self._initial_cursor,
            )

            # Phase 3: 注入来源信息
            for r in all_comments:
                r.source_account_id = account_id
                r.source_account = account_name or r.source_account

            # 校验
            valid = [r for r in all_comments if self.validate(r)]
            self._state.add_comments(
                fetched=len(all_comments),
                valid=len(valid),
            )

            # 更新最后游标
            if valid:
                self._state.last_comment_id = valid[-1].comment_id

            self._state.add_saved(len(valid))

        except Exception as e:
            status = "partial" if all_comments else "failed"
            self._state.record_error(str(e))
            logger.error("抖音采集异常: %s", e)

        # 完成日志
        self._collector_logger.finalize_entry(log_entry, self._state, status)
        self._collector_logger.write_log(log_entry)

        # 校验后的评论
        valid = [r for r in all_comments if self.validate(r)]
        return valid, self._state

    def _collect_videos_paginated(
        self, account_id: str, **kwargs: Any
    ) -> None:
        """分页获取视频列表，模拟真实 API 的分页行为。

        每页 2 个视频，共 2 页（4 个 mock 视频）。
        """
        if self._state is None:
            return

        page_size = 2  # 模拟每页 2 个视频
        all_videos: list[dict[str, Any]] = []
        cursor = ""
        page = 0
        max_pages = 2

        while page < max_pages:
            self._rate_limit_check()

            videos = self._fetch_video_list(account_id, cursor, page_size)
            if not videos:
                break

            # 模拟分页：每次取 page_size 条
            start = page * page_size
            end = start + page_size
            page_videos = DOUYIN_MOCK_VIDEOS[start:end] if not self._api_available else videos

            if not page_videos:
                break

            all_videos.extend(page_videos)
            page += 1

            has_more = len(DOUYIN_MOCK_VIDEOS) > end if not self._api_available else len(videos) >= page_size
            self._state.update_video_cursor(
                cursor=f"video_page_{page + 1}",
                has_more=has_more,
            )

            if not has_more:
                break

        self._state.add_videos(len(all_videos))
        self._state.video_pagination.total_pages = page
        logger.info(
            "抖音视频分页: %d 页, %d 个视频 (账号=%s)",
            page, len(all_videos), account_id,
        )

    def _collect_comments_paginated(
        self, max_count: int, last_cursor: str = ""
    ) -> list[CommentRecord]:
        """分页获取评论，支持增量采集。

        Mock 模式: 每个视频只返回 1 页（所有该视频评论）。
        Live 模式: 通过 cursor 参数真正分页 (P2-4 TODO)。

        - last_cursor 非空: 只采集游标之后的新评论
        - last_cursor 为空: 全量采集
        """
        if self._state is None:
            return []

        all_comments: list[CommentRecord] = []
        seen_cursor = last_cursor
        has_new_data = False

        for video in DOUYIN_MOCK_VIDEOS:
            if len(all_comments) >= max_count:
                break

            vid = video["video_id"]
            self._rate_limit_check()

            # Mock: 一次获取该视频全部评论
            raw_comments = self._fetch_comments(vid, "", 50)
            if not raw_comments:
                continue

            added_this_video = 0
            for raw in raw_comments:
                if len(all_comments) >= max_count:
                    break

                record = self._parse_to_record(raw)
                record.source_video_id = vid
                record.source_video_title = video.get("title", "")
                record.source_url = video.get("url", "")

                # 增量采集：跳过游标之前的评论
                if last_cursor and record.comment_id <= last_cursor:
                    continue

                all_comments.append(record)
                seen_cursor = record.comment_id
                has_new_data = True
                added_this_video += 1

            # 更新分页状态
            if self._state:
                self._state.update_comment_cursor(
                    cursor=vid,
                    comment_id=seen_cursor,
                    has_more=False,  # Mock 无真正分页
                )

        if self._state:
            self._state.comment_pagination.total_pages = len(DOUYIN_MOCK_VIDEOS)

        if last_cursor and not has_new_data:
            logger.info("抖音增量采集: 无新评论 (游标=%s)", last_cursor[:20])

        return all_comments

    def get_last_state(self) -> CollectorState | None:
        """获取最近一次采集的状态。"""
        return self._state

    def get_state_dict(self) -> dict[str, Any] | None:
        """获取状态字典（用于序列化）。"""
        if self._state:
            return self._state.to_dict()
        return None

    def save_state(self, path: str) -> bool:
        """保存采集状态到文件。"""
        if self._state and path:
            self._state.save(Path(path))
            return True
        return False

    def get_today_logs(self) -> list[dict[str, Any]]:
        """获取今日采集日志。"""
        return self._collector_logger.get_today_entries()

    # ── 业务边界过滤 ──

    def validate(self, record: CommentRecord) -> bool:
        """抖音评论业务校验。

        基础校验 (BaseCollector):
        - 非空内容
        - 包含文字字符

        业务规则 (本层):
        - 允许: 城市家庭光伏、别墅/叠拼、小商业
        - 不在此层过滤农村 (交给 comment_analyzer 的 region_engine)
        - 仅过滤明显无效数据
        """
        if not super().validate(record):
            return False

        # P2-3: 不做业务边界过滤，交给下游 Pipeline
        # 原因: 农村评论可能在 Pipeline 中路由到 nurture
        return True


# ── 自检 ──

if __name__ == "__main__":
    print("=" * 60)
    print("  Douyin Live Collector — 自检")
    print("=" * 60)

    # 无凭证 → Mock 降级
    print("\n── Mock 降级模式 (无凭证) ──")
    collector = DouyinLiveCollector(credentials={})
    print(f"  API 可用: {collector._api_available}")
    print(f"  模式: {'Live' if collector._api_available else 'Mock 降级'}")

    records = collector.collect(account_id="test_acc_001", max_count=10)
    print(f"  采集评论: {len(records)} 条")

    for r in records[:3]:
        print(f"    [{r.comment_id}] {r.content[:50]}...")

    # 有凭证 → 尝试 Live (但仍降级，因为 API 未实现)
    print("\n── Live 模式 (有凭证) ──")
    collector2 = DouyinLiveCollector(credentials={"cookie": "mock_cookie"})
    print(f"  API 可用: {collector2._api_available}")

    records2 = collector2.collect(account_id="test_acc_002", max_count=10)
    print(f"  采集评论: {len(records2)} 条")

    # Collect and Save
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        from pathlib import Path
        result = collector.collect_and_save(
            account_id="test_acc_001",
            account_name="成都光伏老王",
            max_count=10,
            output_root=Path(tmp),
        )
        if result:
            print(f"\n  保存: {result}")
        else:
            print("\n  保存: 无有效数据")

    # 抽象方法验证
    print("\n── 抽象方法验证 ──")
    videos = collector._fetch_video_list("acc_001", "", 5)
    print(f"  _fetch_video_list: {len(videos)} 视频")

    comments = collector._fetch_comments("dy_video_001", "", 5)
    print(f"  _fetch_comments: {len(comments)} 评论")

    record = collector._parse_to_record(comments[0])
    print(f"  _parse_to_record: {record.comment_id} → {record.content[:40]}...")

    # 速率限制
    print("\n── 速率限制 ──")
    print(f"  RateLimiter: {collector.rate_limiter.requests_per_minute} req/min")

    print("\n✓ Douyin Live Collector 自检完成")
    print()
