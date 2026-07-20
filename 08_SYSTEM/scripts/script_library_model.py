"""PV_OS Script Library Model V1.0。

实现 PV_OS_CONTENT_INTELLIGENCE_MODEL_V1.md §三 AI二创脚本:
    从 ContentInsight / VideoAnalysisResult → 生成二创脚本 → 脚本库

存储: 04_CONTENT/scripts_ai/ (Markdown 脚本文件)
索引: 04_CONTENT/scripts_ai/script_index.csv

Usage::

    from script_library_model import ScriptEntry, ScriptLibrary
    lib = ScriptLibrary()
    lib.add(ScriptEntry(topic="别墅光伏避坑指南", platform="douyin", ...))
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
SCRIPTS_AI_DIR = PROJECT_ROOT / "04_CONTENT" / "scripts_ai"
SCRIPT_INDEX_CSV = SCRIPTS_AI_DIR / "script_index.csv"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))

SCRIPT_INDEX_FIELDS = [
    "script_id", "topic", "platform", "content_type",
    "target_audience", "source_analysis_id", "source_video_id",
    "angle", "status", "created_at", "published_at",
]


@dataclass
class ScriptScene:
    """脚本分镜。"""
    scene_number: int = 0
    duration_seconds: int = 0
    type: str = ""              # hook / pain_point / solution / data / cta
    text: str = ""              # 台词/旁白
    visuals: str = ""           # 画面描述
    notes: str = ""             # 备注

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScriptEntry:
    """二创脚本条目 — 对标 PV_OS_CONTENT_INTELLIGENCE_MODEL_V1.md §三.3。"""

    # ── 标识 ──
    script_id: str = ""
    topic: str = ""                 # 选题
    platform: str = "douyin"        # 目标平台
    content_type: str = "video"     # video / image_text

    # ── 定位 ──
    target_audience: str = ""       # 目标客群 (别墅业主/小商业/城市家庭)
    angle: str = ""                 # PV_OS 差异化角度

    # ── 来源 ──
    source_analysis_id: str = ""    # 参考的 VideoAnalysisResult
    source_video_id: str = ""       # 参考的竞品视频

    # ── 脚本内容 ──
    title: str = ""                 # 最终标题
    hook: str = ""                  # 开头钩子
    scenes: list[ScriptScene] = field(default_factory=list)
    closing_cta: str = ""           # 结尾引导

    # ── 元数据 ──
    ai_model: str = "mock"          # 生成模型
    reviewer: str = ""              # 审核人
    status: str = "draft"           # draft / reviewed / approved / published
    created_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).isoformat())
    published_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["scenes"] = [s.to_dict() for s in self.scenes]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScriptEntry":
        scenes_raw = data.pop("scenes", [])
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        entry = cls(**valid)
        entry.scenes = [ScriptScene(**s) if isinstance(s, dict) else s for s in scenes_raw]
        return entry

    def to_markdown(self) -> str:
        """生成 Markdown 格式脚本文件。"""
        lines = [
            f"# {self.title or self.topic}",
            "",
            f"**脚本ID**: {self.script_id}",
            f"**平台**: {self.platform}",
            f"**目标客群**: {self.target_audience}",
            f"**差异化角度**: {self.angle}",
            f"**来源分析**: {self.source_analysis_id}",
            f"**生成模型**: {self.ai_model}",
            f"**状态**: {self.status}",
            "",
            "---",
            "",
            f"## 开头钩子",
            f"> {self.hook}",
            "",
        ]

        if self.scenes:
            lines.append("## 分镜脚本")
            lines.append("")
            for scene in self.scenes:
                lines.append(f"### 第{scene.scene_number}镜 ({scene.duration_seconds}s) [{scene.type}]")
                lines.append(f"**台词**: {scene.text}")
                if scene.visuals:
                    lines.append(f"**画面**: {scene.visuals}")
                if scene.notes:
                    lines.append(f"**备注**: {scene.notes}")
                lines.append("")

        lines.extend([
            "## 结尾引导 (CTA)",
            f"> {self.closing_cta}",
            "",
            "---",
            f"*生成时间: {self.created_at}*",
        ])
        return "\n".join(lines)


class ScriptLibrary:
    """二创脚本库。

    存储:
    - 索引: 04_CONTENT/scripts_ai/script_index.csv
    - 脚本: 04_CONTENT/scripts_ai/{script_id}.md
    """

    def __init__(self) -> None:
        SCRIPTS_AI_DIR.mkdir(parents=True, exist_ok=True)

    def add(self, entry: ScriptEntry) -> ScriptEntry:
        """添加脚本到库。"""
        if not entry.script_id:
            date_str = datetime.now(TZ_SHANGHAI).strftime("%Y%m%d")
            seq = len(self.list_all()) + 1
            entry.script_id = f"SCRIPT_{date_str}_{seq:03d}"

        # 保存 Markdown
        md_path = SCRIPTS_AI_DIR / f"{entry.script_id}.md"
        md_path.write_text(entry.to_markdown(), encoding="utf-8")
        logger.info("ScriptLibrary: 保存脚本 %s → %s", entry.script_id, md_path)

        # 更新索引
        self._update_index(entry)
        return entry

    def get(self, script_id: str) -> ScriptEntry | None:
        """获取脚本。"""
        md_path = SCRIPTS_AI_DIR / f"{script_id}.md"
        if not md_path.exists():
            return None
        # 从索引读取元数据
        for row in self._read_index():
            if row and row[0] == script_id:
                d = dict(zip(SCRIPT_INDEX_FIELDS, row))
                entry = ScriptEntry(**{k: v for k, v in d.items()
                         if k in ScriptEntry.__dataclass_fields__})
                return entry
        return None

    def list_all(self) -> list[ScriptEntry]:
        """列出所有脚本。"""
        results: list[ScriptEntry] = []
        rows = self._read_index()
        if len(rows) <= 1:
            return results
        for row in rows[1:]:  # skip header
            if row and len(row) >= len(SCRIPT_INDEX_FIELDS):
                d = dict(zip(SCRIPT_INDEX_FIELDS, row))
                entry = ScriptEntry(**{k: v for k, v in d.items()
                         if k in ScriptEntry.__dataclass_fields__})
                results.append(entry)
        return results

    def list_by_status(self, status: str) -> list[ScriptEntry]:
        """按状态筛选。"""
        return [e for e in self.list_all() if e.status == status]

    def list_by_platform(self, platform: str) -> list[ScriptEntry]:
        """按平台筛选。"""
        return [e for e in self.list_all() if e.platform == platform]

    def update_status(self, script_id: str, status: str) -> bool:
        """更新脚本状态。"""
        entry = self.get(script_id)
        if entry is None:
            return False
        entry.status = status
        if status == "published":
            entry.published_at = datetime.now(TZ_SHANGHAI).isoformat()
        self._update_index(entry)
        return True

    # ── 内部 ──

    def _read_index(self) -> list[list[str]]:
        if not SCRIPT_INDEX_CSV.exists():
            return [SCRIPT_INDEX_FIELDS]
        with open(SCRIPT_INDEX_CSV, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.reader(f))

    def _update_index(self, entry: ScriptEntry) -> None:
        existing = self._read_index()
        existing_dict: dict[str, list[str]] = {
            r[0]: r for r in existing[1:] if r
        }
        row = [str(getattr(entry, f, "")) for f in SCRIPT_INDEX_FIELDS]
        existing_dict[entry.script_id] = row
        with open(SCRIPT_INDEX_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(SCRIPT_INDEX_FIELDS)
            w.writerows(existing_dict.values())


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile, shutil

    print("=" * 60)
    print("  ScriptLibrary — 自检")
    print("=" * 60)

    # 创建脚本
    entry = ScriptEntry(
        topic="成都别墅光伏避坑指南",
        platform="douyin",
        target_audience="别墅业主",
        angle="成都本地化：成都日照条件+本地安装案例",
        source_analysis_id="VA_dy_v001_20260720",
        title="成都别墅装光伏，这3个坑千万别踩！",
        hook="你家别墅想装光伏，但担心被坑？看完这条视频省5万！",
        scenes=[
            ScriptScene(scene_number=1, duration_seconds=5, type="hook",
                       text="你家别墅想装光伏，但担心被坑？", visuals="别墅外观画面"),
            ScriptScene(scene_number=2, duration_seconds=15, type="pain_point",
                       text="成都别墅业主最常见的3个坑", visuals="对比画面"),
            ScriptScene(scene_number=3, duration_seconds=20, type="solution",
                       text="正确的安装流程应该是这样", visuals="施工流程图"),
        ],
        closing_cta="想知道你家别墅装光伏要多少钱？评论区告诉我面积，免费算！",
    )

    print(f"  脚本: {entry.title}")
    print(f"  平台: {entry.platform}")
    print(f"  分镜: {len(entry.scenes)} 镜")

    # Markdown
    md = entry.to_markdown()
    assert "成都别墅装光伏" in md
    assert "第1镜" in md
    print(f"  ✓ Markdown 生成: {len(md)} 字符")

    # 序列化
    d = entry.to_dict()
    e2 = ScriptEntry.from_dict(d)
    assert e2.topic == entry.topic
    assert len(e2.scenes) == 3
    print("  ✓ to_dict/from_dict 正常")

    # Library
    old_dir = SCRIPTS_AI_DIR
    tmp_dir = Path(tempfile.mkdtemp())
    # 临时替换 SCRIPTS_AI_DIR
    import script_library_model
    original = script_library_model.SCRIPTS_AI_DIR
    script_library_model.SCRIPTS_AI_DIR = tmp_dir
    script_library_model.SCRIPT_INDEX_CSV = tmp_dir / "script_index.csv"

    lib = ScriptLibrary()
    lib.add(entry)
    assert entry.script_id != ""
    loaded = lib.get(entry.script_id)
    assert loaded is not None
    assert loaded.topic == "成都别墅光伏避坑指南"
    print(f"  ✓ Library 保存/读取: {entry.script_id}")

    # 状态更新
    lib.update_status(entry.script_id, "reviewed")
    updated = lib.get(entry.script_id)
    assert updated is not None and updated.status == "reviewed"
    print(f"  ✓ 状态更新: {updated.status}")

    # 恢复
    script_library_model.SCRIPTS_AI_DIR = original
    script_library_model.SCRIPT_INDEX_CSV = SCRIPT_INDEX_CSV
    shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n✓ ScriptLibrary 自检完成\n")
