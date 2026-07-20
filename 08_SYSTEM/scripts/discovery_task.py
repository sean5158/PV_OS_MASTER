"""PV_OS Discovery Task — 关键词扩展 → 竞品发现 工作流编排。

连接 KeywordExpander → CompetitorDiscovery，实现一键发现流程:
    词根输入 → 关键词扩展 → 搜索矩阵 → 竞品发现 → 入库

Usage::

    python discovery_task.py                     # 自检
    python discovery_task.py --run               # 执行完整发现流程

架构:
    seed_keywords.yml → KeywordExpander → DiscoveryTaskDef
                              ↓
    competitor_discovery.py ← search matrix
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from dataclasses import asdict, dataclass, field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from keyword_expander import (  # noqa: E402
    KeywordExpander, DiscoveryTaskDef, is_keyword_allowed,
)
from competitor_discovery import CompetitorDiscovery, DiscoveryReport  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

TZ_SHANGHAI = timezone(timedelta(hours=8))


@dataclass
class DiscoveryRunResult:
    """单次发现运行结果。"""
    run_id: str = ""
    mode: str = "mock"
    seed_keywords: list[str] = field(default_factory=list)
    expanded_count: int = 0
    tasks: list[dict[str, Any]] = field(default_factory=list)
    reports: list[dict[str, Any]] = field(default_factory=list)
    total_candidates: int = 0
    total_discovered: int = 0
    grade_s: int = 0
    grade_a: int = 0
    grade_b: int = 0
    duration_seconds: float = 0.0
    region_scope: list[str] = field(default_factory=list)
    customer_scope: list[str] = field(default_factory=list)
    forbidden_filtered: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DiscoveryTaskRunner:
    """发现任务执行器。

    流程:
        1. 加载词根 (seed_keywords.yml)
        2. 关键词扩展 (KeywordExpander)
        3. 生成发现任务 (DiscoveryTaskDef)
        4. 执行竞品发现 (CompetitorDiscovery)
        5. 汇总结果
    """

    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode
        self.expander = KeywordExpander(mode=mode)
        self.discovery = CompetitorDiscovery(mode=mode)

    def run_from_seeds(
        self,
        seed_inputs: list[str],
        grade_filter: str = "A",
    ) -> DiscoveryRunResult:
        """从指定词根执行发现。

        Args:
            seed_inputs: 词根关键词列表，如 ["别墅光伏", "家庭光伏"]
            grade_filter: 词根等级过滤 (S/A/B)

        Returns:
            DiscoveryRunResult
        """
        start = datetime.now(TZ_SHANGHAI)

        run_id = start.strftime("RUN_%Y%m%d_%H%M%S")
        result = DiscoveryRunResult(
            run_id=run_id,
            mode=self.mode,
            seed_keywords=list(seed_inputs),
            region_scope=["四川", "重庆", "贵州"],
            customer_scope=["城市家庭光伏", "别墅/叠拼/高价值住宅", "小商业"],
        )

        # Step 1: 加载词根
        entries = self.expander.load_seed_keywords()
        target = [e for e in entries if e.keyword in seed_inputs]
        if not target:
            # 不在库中 → 用输入创建临时词根
            from keyword_expander import KeywordEntry
            target = [KeywordEntry(keyword=k, grade="A", category="场景词") for k in seed_inputs]

        logger.info("目标词根: %d 个 → %s", len(target), [t.keyword for t in target])

        # Step 2: 关键词扩展
        expanded = self.expander.expand_all(target)
        for seed, er in expanded.items():
            result.expanded_count += er.total_count

        # Step 3: 生成发现任务
        tasks = self.expander.generate_discovery_tasks(entries, task_count=2)
        result.tasks = [t.to_dict() for t in tasks]

        # Step 4: 执行竞品发现
        all_keywords: set[str] = set()
        for er in expanded.values():
            all_keywords.update(er.all_keywords())

        # 范围校验: 禁止关键词过滤
        keyword_list_raw = list(all_keywords)[:30]
        keyword_list = [k for k in keyword_list_raw if is_keyword_allowed(k)]
        filtered_count = len(keyword_list_raw) - len(keyword_list)
        if filtered_count > 0:
            logger.warning("范围校验: 过滤 %d 个禁止关键词", filtered_count)
            for k in keyword_list_raw:
                if k not in keyword_list:
                    logger.warning("  已排除: %s", k)
        logger.info("搜索矩阵: %d 关键词 (去重后, %d 通过范围校验)", len(keyword_list), len(keyword_list))

        result.forbidden_filtered = filtered_count if 'filtered_count' in dir() else 0

        report = self.discovery.run(keyword_list)
        result.reports.append(report.to_dict())
        result.total_candidates = report.candidates_total
        result.total_discovered = report.grade_s + report.grade_a + report.grade_b
        result.grade_s = report.grade_s
        result.grade_a = report.grade_a
        result.grade_b = report.grade_b

        result.duration_seconds = (datetime.now(TZ_SHANGHAI) - start).total_seconds()

        logger.info(
            "发现运行完成: %s — %d候选 → %d入库 (S:%d A:%d B:%d) — %.1fs",
            run_id, result.total_candidates, result.total_discovered,
            result.grade_s, result.grade_a, result.grade_b,
            result.duration_seconds,
        )
        return result

    def get_master_summary(self) -> dict[str, Any]:
        """获取 competitor_master.csv 概览。"""
        accounts = self.discovery.get_master_accounts()
        grades: dict[str, int] = {}
        platforms: dict[str, int] = {}
        for a in accounts:
            g = a.get("grade", "?")
            grades[g] = grades.get(g, 0) + 1
            p = a.get("platform", "?")
            platforms[p] = platforms.get(p, 0) + 1
        return {
            "total": len(accounts),
            "by_grade": grades,
            "by_platform": platforms,
        }


# ══════════════════════════════════════════════════════════════════════
# CLI 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PV_OS Discovery Task Runner")
    parser.add_argument("--run", action="store_true", help="执行完整发现流程")
    parser.add_argument("--seeds", type=str, default="别墅光伏,家庭光伏,阳光房光伏", help="词根(逗号分隔)")
    parser.add_argument("--summary", action="store_true", help="显示 master 概览")
    args = parser.parse_args()

    print("=" * 60)
    print("  PV_OS Discovery Task Runner V1.0")
    print("=" * 60)

    runner = DiscoveryTaskRunner(mode="mock")

    if args.summary:
        s = runner.get_master_summary()
        print(f"\n  competitor_master.csv: {s['total']} 账号")
        print(f"  按等级: {s['by_grade']}")
        print(f"  按平台: {s['by_platform']}")
    elif args.run:
        seeds = [s.strip() for s in args.seeds.split(",")]
        result = runner.run_from_seeds(seeds)

        print(f"\n── 运行结果 {result.run_id} ──")
        print(f"  模式: {result.mode}")
        print(f"  词根: {result.seed_keywords}")
        print(f"  扩展关键词: {result.expanded_count}")
        print(f"  任务数: {len(result.tasks)}")
        print(f"  候选: {result.total_candidates}")
        print(f"  发现入库: {result.total_discovered}")
        print(f"    S:{result.grade_s}  A:{result.grade_a}  B:{result.grade_b}")
        print(f"  耗时: {result.duration_seconds:.1f}s")
    else:
        print("\n  使用 --run 执行完整发现流程")
        print("  使用 --summary 查看当前 master 表")
        print(f"  示例: python discovery_task.py --run --seeds \"别墅光伏,家庭光伏\"")

    print()
