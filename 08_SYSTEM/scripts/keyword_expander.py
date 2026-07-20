"""PV_OS 关键词扩展引擎 V1.0。

实现 KEYWORD_STRATEGY.md 关键词生命周期:
    词根 → 平台联想词 → 区域组合 → 场景组合 → AI评分 → 搜索投放矩阵

Mock 模式: 使用预置扩展规则，无需真实平台 Suggest API。
Public 模式: 待 P2-2 实现平台搜索框联想词获取。

Usage::

    python keyword_expander.py                          # 自检
    python keyword_expander.py --seed "别墅光伏,家庭光伏"  # 指定词根扩展
"""

from __future__ import annotations

import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KEYWORD_DIR = PROJECT_ROOT / "02_DATA" / "01_KEYWORD_LIBRARY"
SEED_KEYWORDS_FILE = KEYWORD_DIR / "seed_keywords.yml"

sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════════

@dataclass
class KeywordEntry:
    """单条关键词。"""
    keyword: str = ""
    category: str = ""           # 行业词/场景词/需求词/竞品词/区域词/长尾词
    sub_category: str = ""
    source: str = "人工"          # 人工/platform_suggest/ai_expand/tag_extract
    initial_score: int = 0
    grade: str = ""
    region: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def is_active(self) -> bool:
        return self.grade in ("S", "A", "B")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KeywordEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExpandResult:
    """扩展结果。"""
    seed_keyword: str = ""        # 原始词根
    expanded_keywords: list[str] = field(default_factory=list)  # 扩展后搜索词
    platform_hints: list[str] = field(default_factory=list)     # 联想词模拟
    region_combos: list[str] = field(default_factory=list)      # 区域组合
    scenario_combos: list[str] = field(default_factory=list)    # 场景组合
    total_count: int = 0

    def all_keywords(self) -> list[str]:
        """返回所有去重后的搜索关键词。"""
        all_kw = [self.seed_keyword] + self.platform_hints + self.region_combos + self.scenario_combos
        seen: set[str] = set()
        result: list[str] = []
        for k in all_kw:
            if k and k not in seen:
                seen.add(k)
                result.append(k)
        self.total_count = len(result)
        return result


@dataclass
class DiscoveryTaskDef:
    """发现任务定义。

    必须包含 region_scope 和 customer_scope，禁止全国无区域任务。
    """
    task_id: str = ""
    keywords: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=lambda: ["douyin", "xiaohongshu"])
    priority: str = "P0"
    created_at: str = ""
    region_scope: list[str] = field(default_factory=lambda: ["四川", "重庆", "贵州"])
    customer_scope: list[str] = field(default_factory=lambda: [
        "城市家庭光伏", "别墅/叠拼/高价值住宅", "小商业"
    ])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def is_valid_scope(self) -> bool:
        """校验 region_scope 和 customer_scope 是否在业务边界内。"""
        valid_regions = {"四川", "重庆", "贵州"}
        valid_customers = {"城市家庭光伏", "别墅/叠拼/高价值住宅", "小商业"}

        if not self.region_scope:
            return False
        if any(r not in valid_regions for r in self.region_scope):
            return False
        if any(c not in valid_customers for c in self.customer_scope):
            return False
        return True


# ══════════════════════════════════════════════════════════════════════
# Mock 扩展数据
# ══════════════════════════════════════════════════════════════════════

# 平台联想词模拟 (KEYWORD_STRATEGY.md §3.3)
MOCK_SUGGEST: dict[str, list[str]] = {
    "别墅光伏": [
        "别墅光伏多少钱", "别墅光伏划算吗", "别墅光伏安装实拍",
        "别墅光伏设计", "别墅光伏案例", "别墅光伏避坑",
        "别墅装光伏", "别墅光伏发电", "别墅光伏全套",
    ],
    "家庭光伏": [
        "家庭光伏安装", "家庭光伏多少钱", "家庭光伏发电",
        "家庭光伏靠谱吗", "家庭光伏补贴", "家庭光伏案例",
    ],
    "阳光房光伏": [
        "阳光房光伏改造", "阳光房光伏多少钱", "阳光房光伏顶",
        "阳光房光伏设计", "阳光房光伏案例", "露台光伏阳光房",
    ],
    "光伏安装": [
        "光伏安装多少钱", "光伏安装公司", "光伏安装流程",
        "光伏安装案例", "光伏安装报价", "光伏安装师傅",
    ],
    "光伏多少钱": [
        "光伏多少钱一平方", "光伏多少钱一套", "光伏安装多少钱",
        "家庭光伏多少钱", "别墅光伏多少钱",
    ],
    "屋顶光伏": [
        "屋顶光伏安装", "屋顶光伏多少钱", "屋顶光伏发电",
        "屋顶光伏改造", "平屋顶光伏", "斜屋顶光伏",
    ],
    "民宿光伏": [
        "民宿光伏安装", "民宿光伏省钱", "民宿光伏案例",
        "酒店光伏", "茶楼光伏", "客栈光伏",
    ],
    "光伏发电": [
        "光伏发电原理", "光伏发电划算吗", "光伏发电家用",
        "光伏发电收益", "光伏发电安装",
    ],
}

# 区域组合 (KEYWORD_STRATEGY.md §9.3)
REGIONS = {
    "四川": ["成都", "绵阳", "德阳", "宜宾", "南充", "泸州"],
    "重庆": ["重庆", "渝北", "万州"],
    "贵州": ["贵阳", "遵义", "毕节"],
}

# 场景组合 (KEYWORD_STRATEGY.md §一 + COMPETITOR_DISCOVERY_ALGORITHM.md)
SCENARIOS = [
    "别墅", "叠拼", "阳光房", "露台", "花园洋房",
    "民宿", "酒店", "茶楼", "美容院",
]


# ══════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════
# 业务边界校验
# ══════════════════════════════════════════════════════════════════════

# 禁止关键词 (农村/大型工商业/全国无区域)
FORBIDDEN_KEYWORDS: list[str] = [
    "农村光伏", "农村", "扶贫光伏", "村村通", "惠农",
    "大型工商业", "工商业光伏", "工厂光伏",
    "全国光伏", "全国安装", "全国各地",
    "光伏扶贫",
    "地面电站", "集中式",
]

# 有效区域范围
VALID_REGION_SCOPE: set[str] = {"四川", "重庆", "贵州"}

# 有效客户范围
VALID_CUSTOMER_SCOPE: set[str] = {
    "城市家庭光伏", "别墅/叠拼/高价值住宅", "小商业",
}

# ══════════════════════════════════════════════════════════════════════
# 关键词扩展引擎
# ══════════════════════════════════════════════════════════════════════

def is_keyword_allowed(keyword: str) -> bool:
    """检查关键词是否在业务边界内。"""
    for forbidden in FORBIDDEN_KEYWORDS:
        if forbidden in keyword:
            return False
    return True


class KeywordExpander:
    """关键词扩展引擎。

    输入: 2-3 个词根
    输出: 搜索关键词矩阵 (词根 + 联想词 + 区域组合 + 场景组合)
    """

    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode

    def load_seed_keywords(self, file_path: str = "") -> list[KeywordEntry]:
        """从 seed_keywords.yml 加载词根。"""
        path = Path(file_path) if file_path else SEED_KEYWORDS_FILE
        if not path.exists():
            logger.warning("词根文件不存在: %s", path)
            return []

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        entries: list[KeywordEntry] = []
        for item in data.get("keywords", []):
            entries.append(KeywordEntry.from_dict(item))

        logger.info("加载 %d 个词根", len(entries))
        return entries

    def get_active_seeds(self, entries: list[KeywordEntry], grade_filter: str = "S") -> list[KeywordEntry]:
        """获取活跃词根 (S/A级)。"""
        if grade_filter == "S":
            return [e for e in entries if e.grade == "S"]
        elif grade_filter == "A":
            return [e for e in entries if e.grade in ("S", "A")]
        return [e for e in entries if e.is_active]

    def expand_single(self, seed: KeywordEntry) -> ExpandResult:
        """对单个词根进行扩展。

        扩展维度:
        1. 平台联想词 (Mock: 预置规则)
        2. 区域组合 (词根 × 川渝黔城市)
        3. 场景组合 (词根 × 高端场景)
        """
        result = ExpandResult(seed_keyword=seed.keyword)

        # 1. 平台联想词
        result.platform_hints = MOCK_SUGGEST.get(seed.keyword, [])
        if not result.platform_hints:
            # 自动生成联想词
            result.platform_hints = [
                f"{seed.keyword}多少钱",
                f"{seed.keyword}安装",
                f"{seed.keyword}案例",
                f"{seed.keyword}靠谱吗",
            ]

        # 2. 区域组合 (词根 × 核心城市)
        core_cities = ["成都", "重庆", "贵阳"]
        for city in core_cities:
            result.region_combos.append(f"{city} {seed.keyword}")
            result.region_combos.append(f"{seed.keyword} {city}")

        # 3. 场景组合 (仅 S/A 级词根做场景扩展)
        if seed.grade in ("S", "A"):
            for scene in SCENARIOS[:5]:  # 前5个场景
                result.scenario_combos.append(f"{scene} {seed.keyword}")

        return result

    def expand_all(self, seeds: list[KeywordEntry]) -> dict[str, ExpandResult]:
        """批量扩展词根。"""
        results: dict[str, ExpandResult] = {}
        for seed in seeds:
            results[seed.keyword] = self.expand_single(seed)
        return results

    def build_search_matrix(self, seeds: list[KeywordEntry]) -> list[str]:
        """构建搜索关键词矩阵（去重，按优先级排序）。

        顺序: S级词根 → S级联想词 → S级区域组合 → A级词根 → ...
        """
        s_seeds = [s for s in seeds if s.grade == "S"]
        a_seeds = [s for s in seeds if s.grade == "A"]
        b_seeds = [s for s in seeds if s.grade == "B"]

        matrix: list[str] = []

        for grade_seeds in [s_seeds, a_seeds, b_seeds]:
            for seed in grade_seeds:
                result = self.expand_single(seed)
                keywords = result.all_keywords()
                for kw in keywords:
                    if kw not in matrix:
                        matrix.append(kw)

        logger.info("搜索矩阵: %d 关键词 (S:%d A:%d B:%d)",
                     len(matrix), len(s_seeds), len(a_seeds), len(b_seeds))
        return matrix

    def generate_discovery_tasks(
        self, seeds: list[KeywordEntry], task_count: int = 3
    ) -> list[DiscoveryTaskDef]:
        """生成发现任务。

        策略: 按优先级分组生成任务:
        - P0 任务: S级词根 + 区域组合 (抖音)
        - P1 任务: S+A级词根 + 场景组合 (抖音+小红书)
        - P2 任务: A+B级词根 (抖音)
        """
        s_seeds = [s for s in seeds if s.grade == "S"]
        a_seeds = [s for s in seeds if s.grade == "A"]

        tasks: list[DiscoveryTaskDef] = []
        idx = 1

        # P0: S级 + 核心区域 (四川/重庆/贵州)
        s_matrix = self.build_search_matrix(s_seeds[:3])
        s_matrix_clean = [k for k in s_matrix[:15] if is_keyword_allowed(k)]
        tasks.append(DiscoveryTaskDef(
            task_id=f"DSC_P0_{idx:03d}",
            keywords=s_matrix_clean,
            platforms=["douyin"],
            priority="P0",
            created_at=datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"),
            region_scope=["四川", "重庆", "贵州"],
            customer_scope=["城市家庭光伏", "别墅/叠拼/高价值住宅", "小商业"],
        ))
        idx += 1

        # P1: S+A级 + 场景扩展 (四川/重庆/贵州)
        combined = s_seeds[:3] + a_seeds[:3]
        a_matrix = self.build_search_matrix(combined)
        a_matrix_clean = [k for k in a_matrix[:20] if is_keyword_allowed(k)]
        tasks.append(DiscoveryTaskDef(
            task_id=f"DSC_P1_{idx:03d}",
            keywords=a_matrix_clean,
            platforms=["douyin", "xiaohongshu"],
            priority="P1",
            created_at=datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"),
            region_scope=["四川", "重庆", "贵州"],
            customer_scope=["城市家庭光伏", "别墅/叠拼/高价值住宅", "小商业"],
        ))

        return tasks[:task_count]


# ══════════════════════════════════════════════════════════════════════
# CLI 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PV_OS 关键词扩展引擎")
    parser.add_argument("--seed", type=str, default="别墅光伏,家庭光伏,阳光房光伏", help="词根(逗号分隔)")
    parser.add_argument("--tasks", action="store_true", help="生成发现任务")
    args = parser.parse_args()

    print("=" * 60)
    print("  PV_OS 关键词扩展引擎 V1.0 (Mock)")
    print("=" * 60)

    expander = KeywordExpander(mode="mock")

    # 加载词根
    entries = expander.load_seed_keywords()
    active = expander.get_active_seeds(entries, grade_filter="A")

    print(f"\n  词根库: {len(entries)} 个")
    print(f"  活跃(S+A): {len(active)} 个")

    # 指定词根扩展
    seeds_input = [s.strip() for s in args.seed.split(",")]
    target_seeds = [e for e in entries if e.keyword in seeds_input]

    print(f"\n── 词根扩展 ({len(target_seeds)} 个) ──")
    for seed in target_seeds:
        result = expander.expand_single(seed)
        all_kw = result.all_keywords()
        print(f"\n  [{seed.grade}] {seed.keyword} ({seed.category})")
        print(f"    联想词: {len(result.platform_hints)}")
        for h in result.platform_hints[:3]:
            print(f"      → {h}")
        print(f"    区域组合: {len(result.region_combos)}")
        for r in result.region_combos[:3]:
            print(f"      → {r}")
        print(f"    场景组合: {len(result.scenario_combos)}")
        print(f"    总计: {all_kw[-1] if False else result.total_count} 搜索词")

    # 搜索矩阵
    print(f"\n── 搜索矩阵 ──")
    matrix = expander.build_search_matrix(entries)
    print(f"  总计 {len(matrix)} 个搜索关键词")
    print(f"  前10个: {matrix[:10]}")

    # 发现任务
    if args.tasks:
        print(f"\n── 发现任务 ──")
        tasks = expander.generate_discovery_tasks(entries, task_count=2)
        for t in tasks:
            print(f"  [{t.priority}] {t.task_id}: {len(t.keywords)} 关键词")
            print(f"    平台={t.platforms}")
            print(f"    区域={t.region_scope}")
            print(f"    客群={t.customer_scope}")
            print(f"    校验={'✓' if t.is_valid_scope() else '✗ INVALID'}")

    print()
