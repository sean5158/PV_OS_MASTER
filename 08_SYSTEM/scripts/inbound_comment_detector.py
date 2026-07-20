"""PV_OS Inbound Comment Detector — 自有账号评论检测与分类 V1.0。

实现 PV_OS_BUSINESS_FLOW_MODEL_V3.md §三 Inbound闭环 Step 5-6:
    检测自有账号视频评论，标记 is_own_account，路由到 Inbound Pipeline。

与 Outbound 共享 Pipeline: region_engine / intent_model / comment_analyzer / lead_scoring。

Usage::

    from inbound_comment_detector import InboundCommentDetector, InboundDetectionResult
    from collector_base import CommentRecord

    detector = InboundCommentDetector()
    result = detector.detect(comment_record)
    if result.is_inbound:
        # 路由到 Inbound Pipeline + Alert Engine
        pass
"""

from __future__ import annotations

import csv
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
INBOUND_LOG_CSV = PROJECT_ROOT / "02_DATA" / "04_COMMENT_DATABASE" / "inbound_comment_log.csv"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))

INBOUND_LOG_FIELDS = [
    "detection_id", "comment_id", "platform",
    "video_author_id", "video_author_name",
    "comment_user_id", "comment_user_name", "comment_content",
    "source_url", "is_inbound", "detected_at",
    "own_account_id", "inbound_type",
]


@dataclass
class InboundDetectionResult:
    """Inbound 评论检测结果。"""

    # ── 来源 ──
    comment_id: str = ""
    platform: str = ""

    # ── 视频发布者 ──
    video_author_id: str = ""
    video_author_name: str = ""

    # ── 评论用户 ──
    comment_user_id: str = ""
    comment_user_name: str = ""
    comment_content: str = ""

    # ── 判定 ──
    is_inbound: bool = False               # 是否属于 Inbound 评论
    inbound_type: str = ""                  # own_comment | competitor_comment
    own_account_id: str = ""                # 匹配的自有账号ID

    # ── 链接 ──
    source_url: str = ""
    user_profile_url: str = ""

    # ── 时间 ──
    detected_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InboundDetectionResult":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


class InboundCommentDetector:
    """Inbound 评论检测器。

    功能:
    1. 检测 CommentRecord 是否来自自有账号视频
    2. 分类: own_comment (自有账号评论) / competitor_comment (竞品账号评论)
    3. 记录检测日志到 inbound_comment_log.csv
    """

    def __init__(self, registry: Any | None = None, log_csv: Path | None = None) -> None:
        """
        Args:
            registry: OwnAccountRegistry 实例
            log_csv: 检测日志CSV路径
        """
        self._own_account_ids: set[str] = set()
        self._own_account_urls: set[str] = set()
        self._account_id_map: dict[str, str] = {}  # platform_account_id → own_account_id

        if registry is not None:
            self._load_from_registry(registry)
        else:
            from own_account_registry import OwnAccountRegistry
            reg = OwnAccountRegistry()
            self._load_from_registry(reg)

        self.log_csv = log_csv or INBOUND_LOG_CSV
        self.log_csv.parent.mkdir(parents=True, exist_ok=True)

    def _load_from_registry(self, registry: Any) -> None:
        """从自有账号注册表加载匹配数据。"""
        for a in registry.list_active():
            if a.monitor_comments:
                self._own_account_ids.add(a.platform_account_id)
                if a.account_url:
                    self._own_account_urls.add(a.account_url)
                self._account_id_map[a.platform_account_id] = a.account_id
                if a.account_url:
                    self._account_id_map[a.account_url] = a.account_id
                logger.debug("InboundDetector: 监听自有账号 %s (%s)", a.account_name, a.platform_account_id)

    def detect(self, record: Any) -> InboundDetectionResult:
        """检测评论是否属于 Inbound 自有账号评论。

        通过 video_author_id 与自有账号匹配。
        同时检查 CommentRecord.is_own_account 标记。

        Args:
            record: CommentRecord 实例

        Returns:
            InboundDetectionResult
        """
        result = InboundDetectionResult(
            comment_id=record.comment_id,
            platform=record.platform,
            video_author_id=record.video_author_id,
            video_author_name=record.video_author_name,
            comment_user_id=record.user_id,
            comment_user_name=record.author,
            comment_content=record.content,
            source_url=record.source_url,
            user_profile_url=record.user_profile_url,
        )

        # 判断来源
        is_own = record.is_own_account
        author_id = record.video_author_id
        author_match = (
            author_id in self._own_account_ids
            or record.source_url in self._own_account_urls
        )

        if is_own or author_match:
            result.is_inbound = True
            result.inbound_type = "own_comment"
            # 查找匹配的自有账号
            result.own_account_id = (
                self._account_id_map.get(author_id, "")
                or self._account_id_map.get(record.source_url, "")
            )
        else:
            result.is_inbound = False
            result.inbound_type = "competitor_comment"

        # 记录日志
        self._log_detection(result)

        return result

    def detect_batch(self, records: list[Any]) -> list[InboundDetectionResult]:
        """批量检测评论。"""
        results: list[InboundDetectionResult] = []
        for r in records:
            results.append(self.detect(r))
        return results

    def filter_inbound(self, records: list[Any]) -> list[Any]:
        """从评论列表中筛选 Inbound 评论。"""
        return [r for r in records if self.detect(r).is_inbound]

    def filter_outbound(self, records: list[Any]) -> list[Any]:
        """从评论列表中筛选 Outbound (竞品) 评论。"""
        return [r for r in records if not self.detect(r).is_inbound]

    def mark_own_accounts(self, records: list[Any]) -> list[Any]:
        """批量标记 CommentRecord.is_own_account 字段。

        Args:
            records: CommentRecord 列表

        Returns:
            标记后的列表 (原位修改)
        """
        for r in records:
            if r.video_author_id in self._own_account_ids:
                r.is_own_account = True
            elif r.source_url in self._own_account_urls:
                r.is_own_account = True
        return records

    def get_stats(self) -> dict[str, int]:
        """获取检测统计。"""
        owned = len(self._own_account_ids)
        return {
            "monitored_own_accounts": owned,
            "total_detections": self._count_log_rows(),
        }

    # ── 日志内部方法 ──

    def _log_detection(self, result: InboundDetectionResult) -> None:
        """记录检测结果到 CSV 日志。"""
        row = [
            f"DET_{result.comment_id}_{datetime.now(TZ_SHANGHAI).strftime('%H%M%S')}",
            result.comment_id, result.platform,
            result.video_author_id, result.video_author_name,
            result.comment_user_id, result.comment_user_name,
            result.comment_content[:200],  # 截断长评论
            result.source_url, str(result.is_inbound),
            result.detected_at, result.own_account_id,
            result.inbound_type,
        ]
        file_exists = self.log_csv.exists()
        with open(self.log_csv, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(INBOUND_LOG_FIELDS)
            w.writerow(row)

    def _count_log_rows(self) -> int:
        if not self.log_csv.exists():
            return 0
        with open(self.log_csv, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1  # exclude header


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile, os
    from collector_base import CommentRecord
    from own_account_registry import OwnAccountRegistry, create_default_own_accounts

    print("=" * 60)
    print("  Inbound Comment Detector — 自检")
    print("=" * 60)

    # 准备
    tmp_reg = Path(tempfile.mkdtemp()) / "test_own_reg.csv"
    registry = OwnAccountRegistry(csv_path=tmp_reg)
    for acct in create_default_own_accounts():
        registry.register(acct)

    tmp_log = Path(tempfile.mkdtemp()) / "test_inbound_log.csv"
    detector = InboundCommentDetector(registry=registry, log_csv=tmp_log)

    # 自有账号评论
    own_comment = CommentRecord(
        comment_id="cmt_own_001", platform="douyin",
        content="我家在成都锦江区，别墅想装光伏，能报个价吗？",
        author="成都业主刘先生",
        video_author_id="dy_own_chengdu_solar",
        video_author_name="成都光伏小马哥",
        source_url="https://douyin.com/video/own_v001",
        user_id="user_001",
        user_profile_url="https://douyin.com/user/user_001",
    )

    result = detector.detect(own_comment)
    assert result.is_inbound, "自有账号评论应被检测为 Inbound"
    assert result.inbound_type == "own_comment"
    assert result.own_account_id == "own_douyin_001"
    print(f"  自有账号评论: inbound={result.is_inbound}, type={result.inbound_type}")

    # 竞品账号评论
    competitor_comment = CommentRecord(
        comment_id="cmt_comp_001", platform="douyin",
        content="光伏安装需要多久？",
        author="重庆业主",
        video_author_id="reg_install_001",
        video_author_name="成都光伏老王",
    )
    result2 = detector.detect(competitor_comment)
    assert not result2.is_inbound, "竞品账号评论不应被检测为 Inbound"
    assert result2.inbound_type == "competitor_comment"
    print(f"  竞品账号评论: inbound={result2.is_inbound}")

    # 批量检测
    all_comments = [own_comment, competitor_comment]
    inbounds = detector.filter_inbound(all_comments)
    outbounds = detector.filter_outbound(all_comments)
    assert len(inbounds) == 1
    assert len(outbounds) == 1
    print(f"  filter: inbound={len(inbounds)}, outbound={len(outbounds)}")

    # mark_own_accounts
    unmarked = [
        CommentRecord(comment_id="cmt_x1", video_author_id="dy_own_chengdu_solar"),
        CommentRecord(comment_id="cmt_x2", video_author_id="unknown_competitor"),
    ]
    detector.mark_own_accounts(unmarked)
    assert unmarked[0].is_own_account == True
    assert unmarked[1].is_own_account == False
    print(f"  mark_own_accounts: ✓")

    # is_own_account 字段检测
    pre_marked = CommentRecord(
        comment_id="cmt_own_002",
        video_author_id="some_id",
        is_own_account=True,
    )
    result3 = detector.detect(pre_marked)
    assert result3.is_inbound
    print(f"  is_own_account=True 字段检测: inbound={result3.is_inbound}")

    # 统计
    stats = detector.get_stats()
    assert stats["monitored_own_accounts"] >= 2
    print(f"  统计: 监听 {stats['monitored_own_accounts']} 个自有账号")

    # 清理
    tmp_reg.unlink(missing_ok=True)
    tmp_log.unlink(missing_ok=True)

    print("\n✓ Inbound Comment Detector 自检完成\n")
