"""PV_OS 快手评论采集连接器（桩）。

快手平台：城市+农村混合用户，光伏安装咨询存在但密度低于抖音。
"""

from __future__ import annotations

import logging
from typing import Any

from collector_base import BaseCollector, CommentRecord

logger = logging.getLogger(__name__)


class KuaishouConnector(BaseCollector):
    """快手平台评论采集器（待实现）。"""

    def __init__(self, credentials: dict[str, Any] | None = None) -> None:
        super().__init__(credentials)
        self.platform_name = "kuaishou"

    def collect(
        self,
        account_id: str,
        max_count: int = 30,
        **kwargs: Any,
    ) -> list[CommentRecord]:
        logger.info("快手采集尚未实现 (account=%s)", account_id)
        return []
