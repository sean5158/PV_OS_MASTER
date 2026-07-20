"""PV_OS 评论采集器基座。

定义平台连接器的抽象接口和数据输出规范。
所有平台连接器必须继承 BaseCollector。

Usage::

    from collector_base import BaseCollector, CommentRecord
    from douyin_connector import DouyinConnector

    collector = DouyinConnector(credentials={})
    comments = collector.collect(account_id="xxx", max_count=50)
    collector.save_batch(comments, platform="douyin")
"""

from __future__ import annotations

import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TZ_SHANGHAI = timezone(timedelta(hours=8))
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class CommentRecord:
    """标准化评论记录，对齐 comment_schema.md V1.0。"""

    # ── 核心标识 ──
    comment_id: str = ""
    platform: str = ""          # douyin | xiaohongshu | kuaishou | wechat_video

    # ── 内容 ──
    content: str = ""
    author: str = ""            # 用户昵称（脱敏）

    # ── 来源 ──
    source_account: str = ""    # 竞品账号名称
    source_account_id: str = ""
    source_video_id: str = ""
    source_video_title: str = ""
    source_url: str = ""

    # ── 时间 ──
    create_time: str = ""       # ISO 8601 或 "YYYY-MM-DD HH:MM:SS"
    collected_time: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"))

    # ── 位置 ──
    ip_location: str = ""       # 用户 IP 属地

    # ── 评论用户 ──
    user_id: str = ""              # 平台用户唯一ID (COMMENT_SCHEMA.md §四)
    user_profile_url: str = ""     # 用户主页链接 (人工触达入口)

    # ── 视频发布者 ──
    video_author_id: str = ""      # 视频发布者平台ID
    video_author_name: str = ""    # 视频发布者昵称

    # ── 互动 ──
    like_count: int = 0
    comment_like_count: int = 0    # 评论点赞数
    reply_count: int = 0           # 回复数

    # ── 账号归属 ──
    is_own_account: bool = False   # 是否来自自有账号视频 (Inbound闭环)

    # ── 元数据 ──
    batch_id: str = ""
    processing_status: str = "collected"  # collected → cleaned → analyzed

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommentRecord":
        """从字典创建，兼容多种字段命名。"""
        return cls(
            comment_id=data.get("comment_id", data.get("id", "")),
            platform=data.get("platform", ""),
            content=data.get("content", data.get("comment_text", "")),
            author=data.get("author", data.get("nickname", "")),
            source_account=data.get("source_account", ""),
            source_account_id=data.get("source_account_id", ""),
            source_video_id=data.get("source_video_id", ""),
            source_video_title=data.get("source_video_title", data.get("video_title", "")),
            source_url=data.get("source_url", ""),
            create_time=data.get("create_time", data.get("comment_time", "")),
            collected_time=data.get("collected_time", datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")),
            ip_location=data.get("ip_location", ""),
            like_count=data.get("like_count", 0),
            user_id=data.get("user_id", ""),
            user_profile_url=data.get("user_profile_url", ""),
            video_author_id=data.get("video_author_id", ""),
            video_author_name=data.get("video_author_name", ""),
            comment_like_count=data.get("comment_like_count", 0),
            reply_count=data.get("reply_count", 0),
            is_own_account=data.get("is_own_account", False),
            batch_id=data.get("batch_id", ""),
            processing_status=data.get("processing_status", "collected"),
        )

    def to_pipeline_event(self) -> dict[str, Any]:
        """转换为 Pipeline 兼容的事件 payload 格式。"""
        return {
            "id": self.comment_id,
            "platform": self.platform,
            "content": self.content,
            "author": self.author,
            "create_time": self.create_time,
            "source_url": self.source_url,
            "ip_location": self.ip_location,
            "video_title": self.source_video_title,
            "keyword": "",
            "user_id": self.user_id,
            "user_profile_url": self.user_profile_url,
            "is_own_account": self.is_own_account,
        }


class BaseCollector(ABC):
    """平台连接器抽象基类。

    子类必须实现 collect() 方法。
    """

    def __init__(self, credentials: dict[str, Any] | None = None) -> None:
        self.credentials = credentials or {}
        self.platform_name: str = self.__class__.__name__.replace("Connector", "").lower()

    @abstractmethod
    def collect(
        self,
        account_id: str,
        max_count: int = 50,
        **kwargs: Any,
    ) -> list[CommentRecord]:
        """从指定竞品账号采集评论。

        Args:
            account_id: 竞品账号 ID
            max_count: 最大采集评论数
            **kwargs: 平台特定参数

        Returns:
            标准化 CommentRecord 列表
        """
        ...

    def validate(self, record: CommentRecord) -> bool:
        """采集阶段基础校验。

        仅过滤明显无效数据，不做价值判断。
        """
        # 空内容
        if not record.content or not record.content.strip():
            return False

        # 纯 emoji / 非文字（无中英文数字字符）
        stripped = record.content.strip()
        has_text = bool(re.search(r'[一-鿿\w]', stripped))
        if not has_text:
            return False

        return True

    def save_batch(
        self,
        records: list[CommentRecord],
        platform: str = "",
        output_root: Path | None = None,
    ) -> Path:
        """保存一批标准化评论到 02_DATA/raw/。

        Returns:
            输出文件路径
        """
        platform = platform or self.platform_name
        if output_root is None:
            output_root = PROJECT_ROOT / "02_DATA" / "raw"

        # 生成批次目录：02_DATA/raw/{platform}/YYYY-MM-DD/
        today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
        batch_dir = output_root / platform / today
        batch_dir.mkdir(parents=True, exist_ok=True)

        # 批次文件名：batch_HHh_序号.json
        hour = datetime.now(TZ_SHANGHAI).strftime("%Hh")
        existing = sorted(batch_dir.glob(f"batch_{hour}_*.json"))
        seq = len(existing) + 1
        batch_file = batch_dir / f"batch_{hour}_{seq:03d}.json"

        # 写入
        output = [r.to_dict() for r in records]
        batch_file.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("保存 %d 条评论 → %s", len(records), batch_file)
        return batch_file

    def deduplicate(self, records: list[CommentRecord]) -> list[CommentRecord]:
        """按 comment_id 去重，保留最新。"""
        seen: dict[str, CommentRecord] = {}
        for r in records:
            if r.comment_id and r.comment_id in seen:
                # 保留新时间
                if r.create_time > seen[r.comment_id].create_time:
                    seen[r.comment_id] = r
            else:
                seen[r.comment_id] = r
        return list(seen.values())

    def collect_and_save(
        self,
        account_id: str,
        account_name: str = "",
        max_count: int = 50,
        output_root: Path | None = None,
        **kwargs: Any,
    ) -> Path | None:
        """一站式：采集 → 校验 → 去重 → 保存。

        Returns:
            输出文件路径，无有效数据时返回 None
        """
        records = self.collect(account_id, max_count=max_count, **kwargs)

        # 注入来源信息
        for r in records:
            r.source_account_id = account_id
            r.source_account = account_name or r.source_account
            r.batch_id = uuid.uuid4().hex[:8]

        # 校验
        valid = [r for r in records if self.validate(r)]
        logger.info(
            "%s 采集: %d 条, 有效 %d 条",
            self.platform_name, len(records), len(valid),
        )

        if not valid:
            return None

        # 去重 + 保存
        unique = self.deduplicate(valid)
        return self.save_batch(unique, platform=self.platform_name, output_root=output_root)


# ── 工厂函数 ──

def create_collector(platform: str, credentials: dict[str, Any] | None = None) -> BaseCollector | None:
    """根据平台名创建对应的连接器实例。

    Args:
        platform: douyin | xiaohongshu | kuaishou | wechat_video
        credentials: 平台凭证
    """
    if platform == "douyin":
        from douyin_connector import DouyinConnector  # noqa: PLC0415
        return DouyinConnector(credentials)
    elif platform == "xiaohongshu":
        from xiaohongshu_connector import XiaohongshuConnector  # noqa: PLC0415
        return XiaohongshuConnector(credentials)
    elif platform == "kuaishou":
        from kuaishou_connector import KuaishouConnector  # noqa: PLC0415
        return KuaishouConnector(credentials)
    elif platform == "wechat_video":
        from wechat_video_connector import WechatVideoConnector  # noqa: PLC0415
        return WechatVideoConnector(credentials)
    else:
        logger.warning("未知平台: %s", platform)
        return None
