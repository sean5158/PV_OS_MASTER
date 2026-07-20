"""PV_OS Video Asset Store — 竞品视频资产持久化 V1.0。

实现 PV_OS_DATA_ASSET_ARCHITECTURE_V3.md §三 Video Asset:
    一次采集，长期保存。支持后续爆款拆解、内容策略分析、二创脚本生成。

存储: 02_DATA/04_COMMENT_DATABASE/video_asset_store.csv

Usage::

    from video_asset import VideoAsset, VideoAssetStore

    store = VideoAssetStore()
    store.save(VideoAsset(video_id="dy_001", title="别墅光伏安装实拍", ...))
    all_videos = store.list_all()
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
VIDEO_ASSET_CSV = PROJECT_ROOT / "02_DATA" / "04_COMMENT_DATABASE" / "video_asset_store.csv"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))

# CSV 字段顺序
VIDEO_CSV_FIELDS = [
    "video_id", "video_url", "platform",
    "author_id", "author_name", "author_url",
    "title", "description", "publish_time", "duration_seconds",
    "like_count", "comment_count", "collect_count", "share_count",
    "housing_signal", "relevance_score",
    # AI 分析字段 (PV_OS_CONTENT_INTELLIGENCE_MODEL_V1.md §二)
    "hook_3_seconds", "pain_point", "customer_type",
    "video_structure", "title_pattern", "comment_trigger",
    "viral_reason", "turning_point", "closing_factor",
    "collected_at", "analyzed_at",
]


@dataclass
class VideoAsset:
    """视频资产 — 对标 PV_OS_DATA_ASSET_ARCHITECTURE_V3.md §三.2。"""

    # ── 核心标识 ──
    video_id: str = ""
    video_url: str = ""
    platform: str = ""              # douyin | xiaohongshu | kuaishou | shipinhao

    # ── 发布者 ──
    author_id: str = ""             # 视频发布者平台ID
    author_name: str = ""           # 视频发布者昵称
    author_url: str = ""            # 视频发布者主页链接

    # ── 内容 ──
    title: str = ""
    description: str = ""
    publish_time: str = ""
    duration_seconds: int = 0

    # ── 互动指标 ──
    like_count: int = 0
    comment_count: int = 0
    collect_count: int = 0
    share_count: int = 0

    # ── PV_OS 分类 ──
    housing_signal: str = ""        # 别墅/叠拼/阳光房/普通住宅
    relevance_score: int = 0        # 0-10

    # ── AI 内容分析 (Content Intelligence) ──
    hook_3_seconds: str = ""        # 黄金三秒钩子
    pain_point: str = ""            # 用户痛点
    customer_type: str = ""         # 目标客群
    video_structure: str = ""       # 结构拆解
    title_pattern: str = ""         # 标题模式
    comment_trigger: str = ""       # 评论触发点
    viral_reason: str = ""          # 爆款原因
    turning_point: str = ""         # 转折点
    closing_factor: str = ""        # 成交因素

    # ── 时间 ──
    collected_at: str = ""
    analyzed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoAsset":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    @classmethod
    def from_video_candidate(cls, vc: Any, platform: str = "douyin") -> "VideoAsset":
        """从 VideoCandidate (public_search_base) 创建 VideoAsset。"""
        return cls(
            video_id=vc.video_id,
            video_url=vc.video_url,
            platform=vc.platform or platform,
            title=vc.title,
            publish_time=vc.publish_time,
            comment_count=vc.comment_count,
            housing_signal=vc.housing_signal,
            relevance_score=vc.relevance_score,
            collected_at=datetime.now(TZ_SHANGHAI).isoformat(),
        )


class VideoAssetStore:
    """视频资产持久化存储。

    存储: 02_DATA/04_COMMENT_DATABASE/video_asset_store.csv
    """

    def __init__(self, csv_path: Path | None = None) -> None:
        self.csv_path = csv_path or VIDEO_ASSET_CSV
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, asset: VideoAsset) -> None:
        """保存或更新视频资产 (按 video_id 去重)。"""
        existing = self._read_all()
        data_rows = existing[1:] if len(existing) > 1 else []  # skip header
        existing_dict: dict[str, list[str]] = {r[0]: r for r in data_rows}

        row = [str(asset.to_dict().get(f, "")) for f in VIDEO_CSV_FIELDS]
        existing_dict[asset.video_id] = row

        self._write_all(list(existing_dict.values()))
        logger.info("VideoAssetStore: 保存 %s (%s)", asset.video_id, asset.title[:30])

    def save_batch(self, assets: list[VideoAsset]) -> int:
        """批量保存。"""
        for a in assets:
            self.save(a)
        return len(assets)

    def get(self, video_id: str) -> VideoAsset | None:
        """获取单个视频资产。"""
        rows = self._read_all()
        if len(rows) <= 1:
            return None
        for row in rows[1:]:  # skip header
            if row[0] == video_id:
                d = dict(zip(VIDEO_CSV_FIELDS, row))
                return VideoAsset.from_dict(d)
        return None

    def list_all(self) -> list[VideoAsset]:
        """列出所有视频资产。"""
        results: list[VideoAsset] = []
        rows = self._read_all()
        if len(rows) <= 1:
            return results
        for row in rows[1:]:  # skip header
            d = dict(zip(VIDEO_CSV_FIELDS, row))
            results.append(VideoAsset.from_dict(d))
        return results

    def list_by_platform(self, platform: str) -> list[VideoAsset]:
        """按平台筛选。"""
        return [a for a in self.list_all() if a.platform == platform]

    def list_by_author(self, author_id: str) -> list[VideoAsset]:
        """按作者筛选。"""
        return [a for a in self.list_all() if a.author_id == author_id]

    def count(self) -> int:
        rows = self._read_all()
        return len(rows) - 1 if len(rows) > 0 else 0  # exclude header

    # ── 内部 ──

    def _read_all(self) -> list[list[str]]:
        if not self.csv_path.exists():
            return [VIDEO_CSV_FIELDS]  # header only
        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.reader(f))

    def _write_all(self, rows: list[list[str]]) -> None:
        rows.sort(key=lambda r: r[0])  # sort by video_id
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(VIDEO_CSV_FIELDS)
            w.writerows(rows)


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile, os

    print("=" * 60)
    print("  VideoAsset + VideoAssetStore — 自检")
    print("=" * 60)

    tmp = Path(tempfile.mkdtemp()) / "test_video_asset.csv"
    store = VideoAssetStore(csv_path=tmp)

    # 创建
    va = VideoAsset(
        video_id="dy_v001",
        video_url="https://douyin.com/video/dy_v001",
        platform="douyin",
        author_id="reg_install_001",
        author_name="成都光伏老王",
        author_url="https://douyin.com/user/reg_install_001",
        title="别墅光伏安装实拍",
        publish_time="2026-07-18",
        like_count=1520,
        comment_count=85,
        collect_count=320,
        share_count=45,
        housing_signal="别墅",
        relevance_score=9,
        collected_at=datetime.now(TZ_SHANGHAI).isoformat(),
    )
    store.save(va)
    print(f"  保存: {va.video_id}")

    # 读取
    loaded = store.get("dy_v001")
    assert loaded is not None
    assert loaded.title == "别墅光伏安装实拍"
    assert loaded.author_name == "成都光伏老王"
    assert loaded.housing_signal == "别墅"
    print(f"  读取: {loaded.title}")

    # 批量
    va2 = VideoAsset(video_id="dy_v002", platform="douyin", title="光伏报价案例",
                     author_id="reg_install_001", author_name="成都光伏老王",
                     publish_time="2026-07-15", comment_count=120)
    store.save_batch([va2])
    assert store.count() == 2
    print(f"  总计: {store.count()} 条")

    # 按作者筛选
    by_author = store.list_by_author("reg_install_001")
    assert len(by_author) == 2
    print(f"  reg_install_001 的视频: {len(by_author)}")

    # from_video_candidate
    from public_search_base import VideoCandidate
    vc = VideoCandidate(
        platform="douyin", video_id="dy_v003",
        title="阳光房光伏顶", housing_signal="阳光房",
        publish_time="2026-07-19", comment_count=45, relevance_score=8,
    )
    va3 = VideoAsset.from_video_candidate(vc)
    assert va3.housing_signal == "阳光房"
    print(f"  from_video_candidate: {va3.video_id} ({va3.housing_signal})")

    # 清理
    tmp.unlink(missing_ok=True)

    print("\n✓ VideoAsset + VideoAssetStore 自检完成\n")
