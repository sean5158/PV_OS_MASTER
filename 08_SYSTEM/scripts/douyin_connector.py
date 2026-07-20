"""PV_OS 抖音评论采集连接器。

实现 BaseCollector 接口，对接抖音平台评论区数据。

平台特征：
- 城市家庭用户基数最大
- 安装咨询类评论最密集 ("多少钱""怎么装""联系我")
- 本地安装商账号运营活跃

Usage::

    from douyin_connector import DouyinConnector

    collector = DouyinConnector(credentials={"cookie": "..."})
    comments = collector.collect(account_id="xxx", max_count=50)
    collector.collect_and_save(account_id="xxx", account_name="某光伏博主")
"""

from __future__ import annotations

import logging
from typing import Any

from collector_base import BaseCollector, CommentRecord

logger = logging.getLogger(__name__)


class DouyinConnector(BaseCollector):
    """抖音平台评论采集器。

    支持两种模式：
    1. mock 模式（默认）：用测试数据模拟采集，验证链路
    2. live 模式：对接真实抖音 API（需配置 cookie/API key）
    """

    def __init__(self, credentials: dict[str, Any] | None = None) -> None:
        super().__init__(credentials)
        self.platform_name = "douyin"
        # 检测是否是 mock 模式
        self._mock_mode = not credentials or not credentials.get("cookie")

    def collect(
        self,
        account_id: str,
        max_count: int = 50,
        **kwargs: Any,
    ) -> list[CommentRecord]:
        """从指定抖音账号采集评论。

        Args:
            account_id: 抖音账号 ID 或 sec_uid
            max_count: 最大采集数
            video_id: (可选) 指定视频 ID，不传则采集最近视频的评论
        """
        video_id = kwargs.get("video_id", "")

        if self._mock_mode:
            return self._mock_collect(account_id, max_count, video_id)
        else:
            return self._live_collect(account_id, max_count, video_id)

    def _mock_collect(
        self, account_id: str, max_count: int, video_id: str
    ) -> list[CommentRecord]:
        """模拟采集：返回 6 条典型测试评论覆盖各种场景。"""
        logger.info("抖音 Mock 模式: 采集账号 %s (max=%d)", account_id, max_count)

        mock_comments = [
            CommentRecord(
                comment_id=f"dy_mock_{account_id}_001",
                platform="douyin",
                content="我在成都这边，家里是别墅，想装一套光伏发电，能报个价吗？",
                author="成都张先生",
                source_account="某光伏安装公司",
                source_account_id=account_id,
                source_video_title="别墅光伏安装实拍案例",
                source_url=f"https://www.douyin.com/video/{video_id or 'test_001'}",
                create_time="2026-07-20 10:00:00",
                ip_location="四川成都",
                like_count=12,
            ),
            CommentRecord(
                comment_id=f"dy_mock_{account_id}_002",
                platform="douyin",
                content="绵阳有没有做光伏安装的？大概多少钱一平方？",
                author="绵阳小王",
                source_account="某光伏安装公司",
                source_account_id=account_id,
                source_video_title="别墅光伏安装实拍案例",
                source_url=f"https://www.douyin.com/video/{video_id or 'test_001'}",
                create_time="2026-07-20 09:30:00",
                ip_location="四川绵阳",
                like_count=5,
            ),
            CommentRecord(
                comment_id=f"dy_mock_{account_id}_003",
                platform="douyin",
                content="重庆渝北的，叠拼别墅，装了光伏一年能省多少电费？",
                author="重庆老李",
                source_account="某光伏安装公司",
                source_account_id=account_id,
                source_video_title="叠拼别墅光伏省钱实拍",
                source_url=f"https://www.douyin.com/video/{video_id or 'test_002'}",
                create_time="2026-07-19 15:00:00",
                ip_location="重庆",
                like_count=23,
            ),
            CommentRecord(
                comment_id=f"dy_mock_{account_id}_004",
                platform="douyin",
                content="这个光伏板能用多少年？我家顶楼想装",
                author="贵阳老陈",
                source_account="某光伏安装公司",
                source_account_id=account_id,
                source_video_title="光伏发电能用多少年科普",
                source_url=f"https://www.douyin.com/video/{video_id or 'test_003'}",
                create_time="2026-07-19 11:00:00",
                ip_location="贵州贵阳",
                like_count=8,
            ),
            CommentRecord(
                comment_id=f"dy_mock_{account_id}_005",
                platform="douyin",
                content="农村自建房想装光伏，有没有补贴啊？",
                author="德阳老刘",
                source_account="某光伏安装公司",
                source_account_id=account_id,
                source_video_title="农村光伏发电省钱吗",
                source_url=f"https://www.douyin.com/video/{video_id or 'test_004'}",
                create_time="2026-07-18 08:00:00",
                ip_location="四川德阳",
                like_count=15,
            ),
            CommentRecord(
                comment_id=f"dy_mock_{account_id}_006",
                platform="douyin",
                content="我在成都开了个民宿，装光伏能省多少钱？有联系方式吗",
                author="民宿老板赵哥",
                source_account="某光伏安装公司",
                source_account_id=account_id,
                source_video_title="民宿光伏发电改造案例",
                source_url=f"https://www.douyin.com/video/{video_id or 'test_005'}",
                create_time="2026-07-20 07:00:00",
                ip_location="四川成都",
                like_count=31,
            ),
        ]

        return mock_comments[:max_count]

    def _live_collect(
        self, account_id: str, max_count: int, video_id: str
    ) -> list[CommentRecord]:
        """真实 API 采集（待实现）。

        TODO: 对接抖音开放平台 API 或使用第三方采集工具。
        需要的接口：
        1. 获取账号视频列表
        2. 获取视频评论列表
        3. 解析评论字段
        """
        logger.warning(
            "抖音 Live 模式尚未实现。请配置第三方采集工具或使用 Mock 模式。"
        )
        return []
