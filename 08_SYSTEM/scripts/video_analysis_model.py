"""PV_OS 视频分析模型 V1.0。

实现 PV_OS_CONTENT_INTELLIGENCE_MODEL_V1.md §二 九维爆款拆解:
    输入: VideoAsset → 分析 → VideoAnalysisResult

Usage::

    from video_analysis_model import VideoAnalysisResult, VideoAnalysisStore
    result = VideoAnalysisResult(video_id="dy_v001", hook_3_seconds="...")
    store = VideoAnalysisStore()
    store.save(result)
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
ANALYSIS_CSV = PROJECT_ROOT / "04_CONTENT" / "analytics" / "video_analysis_results.csv"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))

ANALYSIS_CSV_FIELDS = [
    "analysis_id", "video_id", "video_title",
    "hook_3_seconds", "pain_point", "customer_type",
    "video_structure", "title_pattern", "comment_trigger",
    "viral_reason", "turning_point", "closing_factor",
    "viral_score", "reusability_score",
    "analyzed_at", "source_video_id",
]


@dataclass
class ReusableElements:
    """可复用内容元素。"""
    hook_template: str = ""          # 钩子模板
    structure_template: str = ""     # 结构模板
    key_phrases: list[str] = field(default_factory=list)  # 关键短语
    angle_suggestions: list[str] = field(default_factory=list)  # PV_OS差异化角度

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReusableElements":
        return cls(
            hook_template=data.get("hook_template", ""),
            structure_template=data.get("structure_template", ""),
            key_phrases=data.get("key_phrases", []),
            angle_suggestions=data.get("angle_suggestions", []),
        )


@dataclass
class VideoAnalysisResult:
    """视频爆款拆解结果 — 对标 PV_OS_CONTENT_INTELLIGENCE_MODEL_V1.md §二.2。"""

    # ── 标识 ──
    analysis_id: str = ""
    video_id: str = ""
    video_title: str = ""

    # ── 九维分析 ──
    hook_3_seconds: str = ""        # 黄金三秒
    pain_point: str = ""            # 用户痛点
    customer_type: str = ""         # 目标客群 (别墅业主/小商家/普通家庭)
    video_structure: str = ""       # 结构拆解
    title_pattern: str = ""         # 标题模式
    comment_trigger: str = ""       # 评论触发点
    viral_reason: str = ""          # 爆款原因
    turning_point: str = ""         # 转折点
    closing_factor: str = ""        # 成交因素

    # ── 评分 ──
    viral_score: int = 0            # 爆款指数 0-100
    reusability_score: int = 0      # 可复用度 0-100 (对PV_OS差异化价值)

    # ── 可复用元素 ──
    reusable: ReusableElements = field(default_factory=ReusableElements)

    # ── 时间 ──
    analyzed_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).isoformat())
    source_video_id: str = ""       # 参考的竞品视频ID

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["reusable"] = self.reusable.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoAnalysisResult":
        reusable = data.pop("reusable", {})
        valid: dict[str, Any] = {}
        for k, v in data.items():
            if k in cls.__dataclass_fields__:
                # 类型转换
                field_type = cls.__dataclass_fields__[k].type
                if str(field_type) == 'int' and isinstance(v, str):
                    try:
                        valid[k] = int(v)
                    except (ValueError, TypeError):
                        valid[k] = 0
                else:
                    valid[k] = v
        result = cls(**valid)
        if isinstance(reusable, dict):
            result.reusable = ReusableElements.from_dict(reusable)
        return result

    def to_csv_row(self) -> list[str]:
        """转换为 CSV 行 (不含 reusable，reusable 存单独 JSON)。"""
        return [str(getattr(self, f, "")) for f in ANALYSIS_CSV_FIELDS]

    @classmethod
    def from_csv_row(cls, row: list[str]) -> "VideoAnalysisResult":
        d = dict(zip(ANALYSIS_CSV_FIELDS, row))
        return cls.from_dict(d)


class VideoAnalysisStore:
    """视频分析结果持久化。

    存储: 04_CONTENT/analytics/video_analysis_results.csv
          04_CONTENT/analytics/video_analysis_{id}.json (含 reusable)
    """

    def __init__(self, csv_path: Path | None = None) -> None:
        self.csv_path = csv_path or ANALYSIS_CSV
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._json_dir = self.csv_path.parent

    def save(self, result: VideoAnalysisResult) -> None:
        """保存分析结果 (CSV + JSON)。"""
        # Generate ID if not set
        if not result.analysis_id:
            result.analysis_id = f"VA_{result.video_id}_{datetime.now(TZ_SHANGHAI).strftime('%Y%m%d%H%M%S%f')}"

        # CSV
        existing = self._read_csv()
        existing_dict: dict[str, list[str]] = {
            r[0]: r for r in existing[1:] if len(r) > 0
        }
        existing_dict[result.analysis_id] = result.to_csv_row()
        self._write_csv([ANALYSIS_CSV_FIELDS] + list(existing_dict.values()))

        # JSON (含 reusable)
        json_path = self._json_dir / f"video_analysis_{result.analysis_id}.json"
        json_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("VideoAnalysisStore: 保存 %s → %s", result.analysis_id, json_path)

    def get(self, analysis_id: str) -> VideoAnalysisResult | None:
        """获取分析结果。"""
        rows = self._read_csv()
        for row in rows[1:]:
            if row and row[0] == analysis_id:
                return VideoAnalysisResult.from_csv_row(row)
        return None

    def list_by_video(self, video_id: str) -> list[VideoAnalysisResult]:
        """按视频ID列出分析结果。"""
        results: list[VideoAnalysisResult] = []
        rows = self._read_csv()
        for row in rows[1:]:
            if row and len(row) > 1 and row[1] == video_id:
                results.append(VideoAnalysisResult.from_csv_row(row))
        return results

    def list_all(self) -> list[VideoAnalysisResult]:
        """列出所有分析结果。"""
        rows = self._read_csv()
        return [VideoAnalysisResult.from_csv_row(r) for r in rows[1:] if r]

    def get_top_viral(self, limit: int = 10) -> list[VideoAnalysisResult]:
        """获取爆款指数最高的结果。"""
        all_results = self.list_all()
        all_results.sort(key=lambda r: r.viral_score, reverse=True)
        return all_results[:limit]

    # ── 内部 ──

    def _read_csv(self) -> list[list[str]]:
        if not self.csv_path.exists():
            return [ANALYSIS_CSV_FIELDS]
        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.reader(f))

    def _write_csv(self, rows: list[list[str]]) -> None:
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    print("=" * 60)
    print("  VideoAnalysisResult — 自检")
    print("=" * 60)

    # 创建分析结果
    result = VideoAnalysisResult(
        video_id="dy_v001",
        video_title="别墅光伏安装实拍",
        hook_3_seconds="数字对比：电费从3000降到300",
        pain_point="城市别墅业主电费高但不知道光伏能省多少",
        customer_type="别墅业主",
        video_structure="痛点开场 → 方案展示 → 数据对比 → 客户见证 → 引导咨询",
        title_pattern="数字对比型：我家XX平米装了光伏，一年省了X万",
        comment_trigger="评论里很多人问'我家能装吗'",
        viral_reason="强数字对比 + 真实案例 + 本地信任感",
        turning_point="第15秒展示电费账单对比",
        closing_factor="本地案例 + 可上门测量",
        viral_score=85,
        reusability_score=90,
        reusable=ReusableElements(
            hook_template="【数字】从【旧状态】变成【新状态】",
            structure_template="痛点→方案→数据→见证→CTA",
            key_phrases=["我家XX平米", "一年省了X万", "真实案例"],
            angle_suggestions=["成都本地化", "算日照账", "老旧小区改造"],
        ),
    )
    print(f"  分析: {result.video_title}")
    print(f"  爆款指数: {result.viral_score}")
    print(f"  可复用度: {result.reusability_score}")
    print(f"  钩子: {result.hook_3_seconds[:30]}...")
    print(f"  可复用元素: {result.reusable.key_phrases}")

    # 序列化
    d = result.to_dict()
    assert d["viral_score"] == 85
    assert d["reusable"]["key_phrases"] == ["我家XX平米", "一年省了X万", "真实案例"]
    print("  ✓ to_dict 正常")

    # 反序列化
    r2 = VideoAnalysisResult.from_dict(d)
    assert r2.viral_score == 85
    assert r2.reusable.key_phrases == ["我家XX平米", "一年省了X万", "真实案例"]
    print("  ✓ from_dict 正常")

    # Store
    tmp = Path(tempfile.mkdtemp()) / "test_analysis.csv"
    store = VideoAnalysisStore(csv_path=tmp)
    store.save(result)
    loaded = store.get(result.analysis_id)
    assert loaded is not None
    assert loaded.viral_score == 85
    print(f"  ✓ Store 保存/读取: {loaded.analysis_id}")

    tmp.unlink(missing_ok=True)

    print("\n✓ VideoAnalysisResult 自检完成\n")
