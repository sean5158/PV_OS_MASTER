"""PV_OS 视频号评论采集连接器（桩）。

视频号：微信生态内，光伏内容密度低，优先度最低。
"""

from __future__ import annotations

import logging
from typing import Any

from collector_base import BaseCollector, CommentRecord

logger = logging.getLogger(__name__)


class WechatVideoConnector(BaseCollector):
    """视频号平台评论采集器（待实现）。"""

    def __init__(self, credentials: dict[str, Any] | None = None) -> None:
        super().__init__(credentials)
        self.platform_name = "wechat_video"

    def collect(
        self,
        account_id: str,
        max_count: int = 30,
        **kwargs: Any,
    ) -> list[CommentRecord]:
        logger.info("视频号采集尚未实现 (account=%s)", account_id)
        return []
