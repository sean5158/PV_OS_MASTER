"""PV_OS 小红书评论采集连接器。

实现 BaseCollector 接口，对接小红书评论区数据。

平台特征：
- 一线/新一线城市女性为主，消费力强
- 光伏内容以阳光房改造/家庭能源分享为主
- "求推荐""多少钱""哪里做的" 询价自然高频
- 反爬严格，建议手动导出 + 脚本导入方式

Usage::

    from xiaohongshu_connector import XiaohongshuConnector

    collector = XiaohongshuConnector(credentials={"cookie": "..."})
    comments = collector.collect(account_id="xxx", max_count=30)
"""

from __future__ import annotations

import logging
from typing import Any

from collector_base import BaseCollector, CommentRecord

logger = logging.getLogger(__name__)


class XiaohongshuConnector(BaseCollector):
    """小红书平台评论采集器。"""

    def __init__(self, credentials: dict[str, Any] | None = None) -> None:
        super().__init__(credentials)
        self.platform_name = "xiaohongshu"
        self._mock_mode = not credentials or not credentials.get("cookie")

    def collect(
        self,
        account_id: str,
        max_count: int = 30,
        **kwargs: Any,
    ) -> list[CommentRecord]:
        note_id = kwargs.get("note_id", "")

        if self._mock_mode:
            return self._mock_collect(account_id, max_count, note_id)
        else:
            return self._live_collect(account_id, max_count, note_id)

    def _mock_collect(
        self, account_id: str, max_count: int, note_id: str
    ) -> list[CommentRecord]:
        """模拟采集：小红书典型阳光房/花园洋房场景评论。"""
        logger.info("小红书 Mock 模式: 采集账号 %s (max=%d)", account_id, max_count)

        mock_comments = [
            CommentRecord(
                comment_id=f"xhs_mock_{account_id}_001",
                platform="xiaohongshu",
                content="我家有个露台，想做阳光房加光伏顶，成都这边有推荐的吗？",
                author="成都小A",
                source_account="阳光房改造日记",
                source_account_id=account_id,
                source_video_title="我家露台变身阳光房+光伏发电",
                source_url=f"https://www.xiaohongshu.com/explore/{note_id or 'test_001'}",
                create_time="2026-07-19 14:00:00",
                ip_location="四川成都",
                like_count=45,
            ),
            CommentRecord(
                comment_id=f"xhs_mock_{account_id}_002",
                platform="xiaohongshu",
                content="花园洋房装光伏影响美观吗？想装又怕破坏外观",
                author="装修中的CC",
                source_account="阳光房改造日记",
                source_account_id=account_id,
                source_video_title="花园洋房光伏安装前后对比",
                source_url=f"https://www.xiaohongshu.com/explore/{note_id or 'test_002'}",
                create_time="2026-07-18 20:00:00",
                ip_location="重庆",
                like_count=67,
            ),
            CommentRecord(
                comment_id=f"xhs_mock_{account_id}_003",
                platform="xiaohongshu",
                content="别墅装了光伏，夏天开空调完全不用省，太香了！求安装师傅联系方式",
                author="重庆小D",
                source_account="阳光房改造日记",
                source_account_id=account_id,
                source_video_title="别墅光伏夏天电费对比",
                source_url=f"https://www.xiaohongshu.com/explore/{note_id or 'test_003'}",
                create_time="2026-07-17 10:00:00",
                ip_location="重庆渝北",
                like_count=128,
            ),
            CommentRecord(
                comment_id=f"xhs_mock_{account_id}_004",
                platform="xiaohongshu",
                content="求问贵阳这边光伏安装公司，想给叠拼装一套",
                author="贵阳小林",
                source_account="阳光房改造日记",
                source_account_id=account_id,
                source_video_title="叠拼别墅光伏发电方案",
                source_url=f"https://www.xiaohongshu.com/explore/{note_id or 'test_004'}",
                create_time="2026-07-20 08:00:00",
                ip_location="贵州贵阳",
                like_count=22,
            ),
            CommentRecord(
                comment_id=f"xhs_mock_{account_id}_005",
                platform="xiaohongshu",
                content="这个阳光房加光伏一共花了多少钱？能分享一下吗",
                author="装修小白兔",
                source_account="阳光房改造日记",
                source_account_id=account_id,
                source_video_title="阳光房光伏20万全包分享",
                source_url=f"https://www.xiaohongshu.com/explore/{note_id or 'test_005'}",
                create_time="2026-07-15 16:00:00",
                ip_location="四川成都",
                like_count=89,
            ),
        ]

        return mock_comments[:max_count]

    def _live_collect(
        self, account_id: str, max_count: int, note_id: str
    ) -> list[CommentRecord]:
        """真实 API 采集（待实现）。

        TODO: 小红书反爬严格，建议使用以下方式：
        1. 小红书开放平台 API（如有权限）
        2. 手动导出笔记评论 CSV/JSON → 脚本导入
        3. 第三方数据服务商
        """
        logger.warning(
            "小红书 Live 模式尚未实现。建议手动导出评论后使用 import_from_file() 导入。"
        )
        return []

    def import_from_file(self, file_path: str, source_account: str = "") -> list[CommentRecord]:
        """从手动导出的 JSON/CSV 文件导入评论。

        支持格式：
        - JSON 数组: [{"comment_text": "...", "nickname": "...", ...}, ...]
        - CSV (需 pandas，暂未实现)
        """
        import json
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            logger.error("文件不存在: %s", file_path)
            return []

        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raw = [raw]

        records = [CommentRecord.from_dict(r) for r in raw]
        for r in records:
            r.platform = "xiaohongshu"
            if source_account:
                r.source_account = source_account

        logger.info("从文件导入 %d 条小红书评论", len(records))
        return records
