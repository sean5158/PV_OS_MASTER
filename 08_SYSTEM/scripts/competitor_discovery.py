"""PV_OS 竞品发现引擎 V1.0。

实现 COMPETITOR_DISCOVERY_ALGORITHM.md 六阶段流程 + COMPETITOR_SCORE_RULE.md 六维评分。

Mock 模式：内置 12 个候选账号覆盖四级竞品分类，无需真实平台搜索。

完整流程:
    关键词输入 → 搜索模拟 → 初筛(7排除) → 六维评分 → S/A/B入库 → 日报

Usage::

    python competitor_discovery.py                           # 自检
    python competitor_discovery.py --keywords "别墅光伏,成都光伏安装"  # 指定关键词
    python competitor_discovery.py --seed                    # 播种首批竞品

架构:
    Layer 2 of P2 Architecture V2.1
    └─ 关键词驱动 → 平台公开搜索 → 发现账号 → 发现视频 → 评论采集
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
COMPETITOR_DIR = PROJECT_ROOT / "02_DATA" / "02_COMPETITOR_DATABASE"
DISCOVERY_LOGS_DIR = COMPETITOR_DIR / "discovery_logs"
COMPETITOR_MASTER = COMPETITOR_DIR / "competitor_master.csv"

sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

TZ_SHANGHAI = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ_SHANGHAI)
NOW_STR = lambda: NOW().strftime("%Y-%m-%d %H:%M:%S")
TODAY = lambda: NOW().strftime("%Y-%m-%d")


# ══════════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ScoreDetail:
    """六维评分明细。"""
    business_match: int = 0         # 业务匹配 0-30
    home_pv_match: int = 0          # 城市家庭光伏 0-20
    premium_scene: int = 0          # 别墅/阳光房/小商业 0-15
    region_match: int = 0           # 川渝黔区域 0-15
    comment_value: int = 0          # 评论区需求 0-10
    activity_7d: int = 0            # 7天活跃度 0-10

    @property
    def total(self) -> int:
        return (self.business_match + self.home_pv_match + self.premium_scene +
                self.region_match + self.comment_value + self.activity_7d)

    @property
    def grade(self) -> str:
        t = self.total
        if t >= 80: return "S"
        if t >= 65: return "A"
        if t >= 45: return "B"
        return "C"

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "total": self.total, "grade": self.grade}


@dataclass
class CompetitorCandidate:
    """竞品候选账号。"""
    platform: str = ""
    account_id: str = ""
    account_name: str = ""
    account_url: str = ""
    account_type: str = ""           # national_brand / regional_installer / city_case / renovation / personal_blogger
    bio: str = ""
    follower_count: int = 0
    ip_location: str = ""
    discovery_keyword: str = ""
    score: ScoreDetail = field(default_factory=ScoreDetail)
    monitor_frequency: str = ""      # 6h / daily / weekly
    status: str = "active"
    # ── V3.0: 账号用途分类 ──
    account_purpose: str = ""        # customer_source / content_learning / both
    learning_priority: int = 0       # 1-10 (仅 content_learning/both 时有效)
    # 初筛
    prescreen_result: str = ""       # passed / noise / supplier / ...
    discovery_date: str = field(default_factory=lambda: TODAY())


@dataclass
class DiscoveryReport:
    """发现日报。"""
    date: str = field(default_factory=lambda: TODAY())
    keywords_used: list[str] = field(default_factory=list)
    candidates_total: int = 0
    prescreen_passed: int = 0
    scored: int = 0
    grade_s: int = 0
    grade_a: int = 0
    grade_b: int = 0
    grade_c: int = 0
    new_accounts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════
# Mock 候选账号库（12个账号，覆盖四级竞品分类）
# ══════════════════════════════════════════════════════════════════════

MOCK_CANDIDATES: list[dict[str, Any]] = [
    # ── 一级：全国光伏品牌 ──
    {
        "platform": "douyin", "account_id": "nat_brand_001", "account_name": "正泰安能",
        "account_url": "https://douyin.com/user/nat_brand_001", "account_type": "national_brand",
        "bio": "正泰集团旗下户用光伏品牌，全国安装服务", "follower_count": 250000, "ip_location": "浙江杭州",
        "discovery_keyword": "光伏安装",
        "content_sample": ["家庭光伏安装案例", "光伏补贴政策解读", "全国安装案例"],
        "region_signals": ["成都", "重庆"], "premium_signals": ["别墅", "阳光房"],
        "comment_signals": 3, "activity_days": 2,
    },
    {
        "platform": "douyin", "account_id": "nat_brand_002", "account_name": "天合富家",
        "account_url": "https://douyin.com/user/nat_brand_002", "account_type": "national_brand",
        "bio": "天合光能旗下分布式光伏品牌", "follower_count": 180000, "ip_location": "江苏常州",
        "discovery_keyword": "家庭光伏",
        "content_sample": ["分布式光伏方案", "户用光伏案例", "工商业光伏"],
        "region_signals": ["贵州"], "premium_signals": [],
        "comment_signals": 2, "activity_days": 5,
    },
    # ── 二级：区域安装商 ──
    {
        "platform": "douyin", "account_id": "reg_install_001", "account_name": "成都光伏老王",
        "account_url": "https://douyin.com/user/reg_install_001", "account_type": "regional_installer",
        "bio": "成都本地光伏安装团队，专注家庭光伏10年", "follower_count": 35000, "ip_location": "四川成都",
        "discovery_keyword": "成都光伏安装",
        "content_sample": ["别墅光伏安装实拍", "成都家庭光伏案例", "光伏报价"],
        "region_signals": ["成都", "绵阳", "德阳"], "premium_signals": ["别墅", "叠拼", "阳光房"],
        "comment_signals": 5, "activity_days": 0,
    },
    {
        "platform": "douyin", "account_id": "reg_install_002", "account_name": "重庆阳光光伏",
        "account_url": "https://douyin.com/user/reg_install_002", "account_type": "regional_installer",
        "bio": "重庆主城光伏安装公司", "follower_count": 12000, "ip_location": "重庆",
        "discovery_keyword": "重庆光伏",
        "content_sample": ["重庆别墅光伏", "光伏储能系统", "安装实拍"],
        "region_signals": ["重庆", "渝北"], "premium_signals": ["别墅"],
        "comment_signals": 4, "activity_days": 1,
    },
    {
        "platform": "douyin", "account_id": "reg_install_003", "account_name": "贵阳光伏安装-老周",
        "account_url": "https://douyin.com/user/reg_install_003", "account_type": "regional_installer",
        "bio": "贵阳本地光伏安装，工商业+家庭都做", "follower_count": 8000, "ip_location": "贵州贵阳",
        "discovery_keyword": "贵阳光伏",
        "content_sample": ["贵阳光伏安装", "工商业光伏项目", "家庭光伏"],
        "region_signals": ["贵阳", "遵义"], "premium_signals": [],
        "comment_signals": 3, "activity_days": 3,
    },
    # ── 三级：城市案例账号 ──
    {
        "platform": "douyin", "account_id": "city_case_001", "account_name": "别墅光伏改造日记",
        "account_url": "https://douyin.com/user/city_case_001", "account_type": "city_case",
        "bio": "专注高端别墅光伏改造，实拍案例分享", "follower_count": 50000, "ip_location": "四川成都",
        "discovery_keyword": "别墅光伏",
        "content_sample": ["独栋别墅光伏改造", "花园洋房光伏", "阳光房光伏顶"],
        "region_signals": ["成都", "重庆"], "premium_signals": ["别墅", "花园洋房", "阳光房"],
        "comment_signals": 5, "activity_days": 0,
    },
    {
        "platform": "xiaohongshu", "account_id": "city_case_002", "account_name": "阳光房改造指南",
        "account_url": "https://xiaohongshu.com/user/city_case_002", "account_type": "city_case",
        "bio": "阳光房设计+光伏一体化，露台改造专家", "follower_count": 28000, "ip_location": "四川成都",
        "discovery_keyword": "阳光房光伏",
        "content_sample": ["阳光房光伏设计", "露台改造案例", "光伏阳光房实拍"],
        "region_signals": ["成都"], "premium_signals": ["阳光房", "露台"],
        "comment_signals": 4, "activity_days": 1,
    },
    # ── 四级：装修/改造账号 ──
    {
        "platform": "xiaohongshu", "account_id": "renovation_001", "account_name": "屋顶改造老王",
        "account_url": "https://xiaohongshu.com/user/renovation_001", "account_type": "renovation",
        "bio": "屋顶翻新+光伏一体化，重庆本地施工", "follower_count": 15000, "ip_location": "重庆",
        "discovery_keyword": "屋顶光伏",
        "content_sample": ["屋顶翻新案例", "光伏屋顶安装", "防水+光伏"],
        "region_signals": ["重庆"], "premium_signals": [],
        "comment_signals": 2, "activity_days": 4,
    },
    {
        "platform": "douyin", "account_id": "renovation_002", "account_name": "民宿改造-张工",
        "account_url": "https://douyin.com/user/renovation_002", "account_type": "renovation",
        "bio": "民宿改造设计，含光伏储能方案", "follower_count": 22000, "ip_location": "贵州贵阳",
        "discovery_keyword": "民宿光伏",
        "content_sample": ["民宿光伏改造", "酒店节能方案", "茶楼光伏"],
        "region_signals": ["贵阳"], "premium_signals": ["民宿", "酒店", "茶楼"],
        "comment_signals": 3, "activity_days": 2,
    },
    # ── 应被排除的账号 ──
    {
        "platform": "douyin", "account_id": "noise_001", "account_name": "光伏资讯日报",
        "account_url": "https://douyin.com/user/noise_001", "account_type": "info_account",
        "bio": "转发光伏行业新闻", "follower_count": 5000, "ip_location": "北京",
        "discovery_keyword": "光伏新闻",
        "content_sample": ["光伏政策转发", "行业新闻", "价格行情"],
        "region_signals": [], "premium_signals": [],
        "comment_signals": 0, "activity_days": 7,
    },
    {
        "platform": "douyin", "account_id": "noise_002", "account_name": "隆基绿能官方",
        "account_url": "https://douyin.com/user/noise_002", "account_type": "supplier",
        "bio": "隆基绿能官方账号，组件产品展示", "follower_count": 500000, "ip_location": "陕西西安",
        "discovery_keyword": "光伏组件",
        "content_sample": ["组件产品发布", "招商加盟", "技术参数"],
        "region_signals": [], "premium_signals": [],
        "comment_signals": 0, "activity_days": 3,
    },
    {
        "platform": "douyin", "account_id": "noise_003", "account_name": "小明的日常",
        "account_url": "https://douyin.com/user/noise_003", "account_type": "casual",
        "bio": "分享日常生活", "follower_count": 1200, "ip_location": "四川成都",
        "discovery_keyword": "光伏",
        "content_sample": ["日常vlog", "美食", "偶发一条光伏内容"],
        "region_signals": ["成都"], "premium_signals": [],
        "comment_signals": 0, "activity_days": 1,
    },
]

# 初筛排除规则
EXCLUDE_TYPES = {
    "info_account": "纯资讯号，无原创内容",
    "supplier": "组件厂商号，以批发/招商为主",
    "education": "纯科普号，无商业行为",
    "noise": "异地无关号",
    "inaccessible": "已注销/私密号",
    "enterprise": "大型能源集团官号",
    "casual": "个人生活号，偶发一条光伏内容",
}

# 六维评分权重
SCORE_MAX = {"business_match": 30, "home_pv_match": 20, "premium_scene": 15,
             "region_match": 15, "comment_value": 10, "activity_7d": 10}

# 监控频率映射
FREQUENCY_MAP = {"S": "6h", "A": "daily", "B": "weekly", "C": ""}


# ══════════════════════════════════════════════════════════════════════
# 竞品发现引擎
# ══════════════════════════════════════════════════════════════════════

class CompetitorDiscovery:
    """竞品发现引擎 — Phase 1-6 完整实现。

    Mock 模式: 使用内置候选账号库。
    Public 模式: 待 P2-2 实现平台搜索。
    """

    def __init__(self, mode: str = "mock") -> None:
        self.mode = mode
        self.candidates: list[CompetitorCandidate] = []
        self.report = DiscoveryReport()

    # ── Phase 1: 关键词投放 ──

    def search_by_keywords(self, keywords: list[str]) -> list[dict[str, Any]]:
        """关键词→搜索模拟。

        Mock: 从候选库中匹配关键词相关账号。
        Public: 委托 DouyinPublicCollector 公开搜索。
        """
        if self.mode == "mock":
            return self._mock_search(keywords)
        elif self.mode == "public":
            return self._public_search(keywords)
        else:
            logger.warning("未知搜索模式: %s", self.mode)
            return []

    def _public_search(self, keywords: list[str]) -> list[dict[str, Any]]:
        """Public 模式: 委托 DouyinPublicCollector 搜索。"""
        try:
            from douyin_public_collector import DouyinPublicCollector  # noqa: PLC0415
            collector = DouyinPublicCollector(mode="mock")  # P2-2: mock桩, P2-3: 真实public
            results: list[dict[str, Any]] = []
            seen: set[str] = set()
            for kw in keywords:
                items = collector.search_by_keywords(kw, depth=30)
                for item in items:
                    if item.account_id not in seen:
                        seen.add(item.account_id)
                        # 转换为兼容 MOCK_CANDIDATES 的 dict 格式
                        results.append({
                            "platform": item.platform,
                            "account_id": item.account_id,
                            "account_name": item.account_name,
                            "account_url": item.account_url,
                            "account_type": item.account_type_hint,
                            "bio": item.bio_snippet,
                            "follower_count": item.follower_count,
                            "ip_location": item.ip_location,
                            "discovery_keyword": item.discovery_keyword,
                            "content_sample": [],
                            "premium_signals": [],
                            "region_signals": [],
                            "comment_signals": 0,
                            "activity_days": 7,
                        })
            logger.info("Public搜索: %d关键词 → %d去重结果", len(keywords), len(results))
            return results
        except ImportError:
            logger.warning("DouyinPublicCollector 不可用，回退 Mock 搜索")
            return self._mock_search(keywords)

    def _mock_search(self, keywords: list[str]) -> list[dict[str, Any]]:
        """Mock: 关键词匹配候选账号。"""
        results: list[dict[str, Any]] = []
        for kw in keywords:
            for c in MOCK_CANDIDATES:
                if kw in c["discovery_keyword"] or any(kw in k for k in c.get("content_sample", [])):
                    if c not in results:
                        results.append(c)
        logger.info("关键词搜索: %s → %d 候选", keywords, len(results))
        return results

    # ── Phase 2: 初筛（7排除规则） ──

    def prescreen(self, candidates: list[dict[str, Any]]) -> list[CompetitorCandidate]:
        """初筛：排除7类不应入库的账号。"""
        passed: list[CompetitorCandidate] = []
        for c in candidates:
            atype = c.get("account_type", "")
            if atype in EXCLUDE_TYPES:
                logger.info("初筛排除: %s (%s) — %s", c["account_name"], atype, EXCLUDE_TYPES[atype])
                continue

            cc = CompetitorCandidate(
                platform=c["platform"],
                account_id=c["account_id"],
                account_name=c["account_name"],
                account_url=c["account_url"],
                account_type=atype,
                bio=c.get("bio", ""),
                follower_count=c.get("follower_count", 0),
                ip_location=c.get("ip_location", ""),
                discovery_keyword=c.get("discovery_keyword", ""),
                prescreen_result="passed",
            )
            passed.append(cc)

        logger.info("初筛: %d候选 → %d通过", len(candidates), len(passed))
        return passed

    # ── Phase 3-4: 六维评分 ──

    def score_candidates(self, candidates: list[CompetitorCandidate]) -> list[CompetitorCandidate]:
        """对通过初筛的候选账号进行六维评分。"""
        scored: list[CompetitorCandidate] = []
        for cc in candidates:
            # 查找原始数据
            raw = next((c for c in MOCK_CANDIDATES if c["account_id"] == cc.account_id), None)
            if raw is None:
                continue

            score = self._score_account(raw)
            cc.score = score

            # 一票否决：业务匹配<10
            if score.business_match < 10:
                logger.info("一票否决: %s — 业务匹配=%d", cc.account_name, score.business_match)
                continue

            cc.monitor_frequency = FREQUENCY_MAP.get(score.grade, "")
            cc.discovery_date = TODAY()
            scored.append(cc)

        logger.info("评分: %d候选 → %d通过评分", len(candidates), len(scored))
        return scored

    def _score_account(self, raw: dict[str, Any]) -> ScoreDetail:
        """单账号六维评分。

        维度                  满分    Mock评分逻辑
        ─────────────────────────────────────────
        业务匹配                30     account_type决定
        城市家庭光伏匹配         20     内容中"家庭/别墅"信号
        别墅/阳光房/小商业        15     premium_signals计数
        川渝黔区域               15     region_signals覆盖
        评论区需求价值           10     comment_signals密度
        7天活跃度               10     距上次更新的天数
        """
        atype = raw.get("account_type", "")
        premium = raw.get("premium_signals", [])
        regions = raw.get("region_signals", [])
        comment_sig = raw.get("comment_signals", 0)
        activity_days = raw.get("activity_days", 7)

        # 1. 业务匹配 (0-30)
        biz_scores = {"national_brand": 28, "regional_installer": 30, "city_case": 27,
                       "renovation": 18, "personal_blogger": 13}
        business_match = biz_scores.get(atype, 8)

        # 2. 城市家庭光伏 (0-20)
        if atype in ("regional_installer", "city_case"):
            home_pv = 18
        elif atype == "national_brand":
            home_pv = 14
        elif atype == "renovation":
            home_pv = 12
        else:
            home_pv = 6

        # 3. 别墅/阳光房/小商业 (0-15)
        premium_score = min(len(premium) * 3, 15)

        # 4. 川渝黔区域 (0-15)
        kw_regions = {"四川": 5, "重庆": 5, "贵州": 5, "成都": 5, "绵阳": 3, "德阳": 3,
                       "贵阳": 5, "遵义": 3, "渝北": 3}
        region_score = 0
        for r in regions:
            region_score += kw_regions.get(r, 2)
        region_score = min(region_score, 15)

        # 5. 评论区需求 (0-10)
        if comment_sig >= 5:
            comment_value = 9
        elif comment_sig >= 3:
            comment_value = 6
        elif comment_sig >= 1:
            comment_value = 3
        else:
            comment_value = 1

        # 6. 7天活跃度 (0-10)
        if activity_days == 0:
            activity = 10
        elif activity_days <= 1:
            activity = 9
        elif activity_days <= 3:
            activity = 6
        elif activity_days <= 7:
            activity = 3
        else:
            activity = 1

        return ScoreDetail(
            business_match=business_match,
            home_pv_match=home_pv,
            premium_scene=premium_score,
            region_match=region_score,
            comment_value=comment_value,
            activity_7d=activity,
        )

    # ── Phase 5: 入库 ──

    def save_to_master(self, candidates: list[CompetitorCandidate]) -> int:
        """将 S/A/B 级竞品写入 competitor_master.csv。

        Returns:
            写入的账号数
        """
        COMPETITOR_DIR.mkdir(parents=True, exist_ok=True)

        # 读取已有记录（去重）
        existing_ids: set[str] = set()
        if COMPETITOR_MASTER.exists():
            with open(COMPETITOR_MASTER, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_ids.add(row.get("account_id", ""))

        fieldnames = [
            "competitor_id", "platform", "account_id", "account_name", "account_url",
            "account_type", "bio", "grade", "total_score", "discovery_keyword",
            "discovery_date", "follower_count", "ip_location",
            "monitor_level", "monitor_frequency", "status",
            "score_business_match", "score_home_pv", "score_premium_scene",
            "score_region", "score_comment_value", "score_activity",
        ]

        file_exists = COMPETITOR_MASTER.exists()
        new_count = 0

        with open(COMPETITOR_MASTER, "a" if file_exists else "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()

            seq = sum(1 for _ in open(COMPETITOR_MASTER, encoding="utf-8-sig")) if file_exists else 0

            for cc in candidates:
                if cc.account_id in existing_ids:
                    continue
                if cc.score.grade == "C":
                    continue

                seq += 1
                writer.writerow({
                    "competitor_id": f"PV_COMP_{seq:06d}",
                    "platform": cc.platform,
                    "account_id": cc.account_id,
                    "account_name": cc.account_name,
                    "account_url": cc.account_url,
                    "account_type": cc.account_type,
                    "bio": cc.bio,
                    "grade": cc.score.grade,
                    "total_score": cc.score.total,
                    "discovery_keyword": cc.discovery_keyword,
                    "discovery_date": cc.discovery_date,
                    "follower_count": cc.follower_count,
                    "ip_location": cc.ip_location,
                    "monitor_level": cc.score.grade,
                    "monitor_frequency": cc.monitor_frequency,
                    "status": cc.status,
                    "score_business_match": cc.score.business_match,
                    "score_home_pv": cc.score.home_pv_match,
                    "score_premium_scene": cc.score.premium_scene,
                    "score_region": cc.score.region_match,
                    "score_comment_value": cc.score.comment_value,
                    "score_activity": cc.score.activity_7d,
                })
                new_count += 1
                existing_ids.add(cc.account_id)

        logger.info("入库: %d 新账号 → %s", new_count, COMPETITOR_MASTER.name)
        return new_count

    # ── Phase 6: 日报 ──

    def generate_report(self, candidates: list[CompetitorCandidate]) -> DiscoveryReport:
        """生成发现日报。"""
        self.report.candidates_total = len(self.candidates) if self.candidates else len(candidates)

        graded = [c for c in candidates if c.score.total > 0]
        self.report.prescreen_passed = len(candidates)
        self.report.scored = len(graded)
        self.report.grade_s = sum(1 for c in graded if c.score.grade == "S")
        self.report.grade_a = sum(1 for c in graded if c.score.grade == "A")
        self.report.grade_b = sum(1 for c in graded if c.score.grade == "B")
        self.report.grade_c = sum(1 for c in graded if c.score.grade == "C")

        self.report.new_accounts = [
            {
                "account_name": c.account_name,
                "platform": c.platform,
                "grade": c.score.grade,
                "total_score": c.score.total,
                "account_type": c.account_type,
            }
            for c in graded if c.score.grade in ("S", "A", "B")
        ]

        return self.report

    def save_report(self, report: DiscoveryReport) -> Path:
        """保存日报到 discovery_logs/。"""
        DISCOVERY_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = DISCOVERY_LOGS_DIR / f"{report.date}.json"

        existing: list[dict] = []
        if log_file.exists():
            try:
                existing = json.loads(log_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = []

        existing.append(report.to_dict())
        log_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("发现日报 → %s", log_file.name)
        return log_file

    # ── 完整流程 ──

    def run(self, keywords: list[str]) -> DiscoveryReport:
        """执行完整竞品发现流程 (Phase 1-6)。"""
        logger.info("竞品发现引擎启动 (模式=%s)", self.mode)
        logger.info("关键词: %s", keywords)

        # Phase 1-2: 搜索 + 初筛
        search_results = self.search_by_keywords(keywords)
        self.candidates = self.prescreen(search_results)

        # Phase 3-4: 评分
        scored = self.score_candidates(self.candidates)

        # Phase 5: 入库
        self.save_to_master(scored)

        # Phase 6: 日报
        report = self.generate_report(scored)
        self.report.keywords_used = keywords
        self.save_report(report)

        logger.info(
            "竞品发现完成: %d候选 → %d初筛通过 → %d入库 (S:%d A:%d B:%d)",
            len(search_results), len(self.candidates), len(scored),
            report.grade_s, report.grade_a, report.grade_b,
        )
        return report

    def get_master_accounts(self) -> list[dict[str, str]]:
        """读取 competitor_master.csv 当前内容。"""
        if not COMPETITOR_MASTER.exists():
            return []
        with open(COMPETITOR_MASTER, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))


# ══════════════════════════════════════════════════════════════════════
# CLI + 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PV_OS 竞品发现引擎")
    parser.add_argument("--keywords", type=str, default="别墅光伏,成都光伏安装,家庭光伏,阳光房光伏,屋顶光伏", help="搜索关键词(逗号分隔)")
    parser.add_argument("--seed", action="store_true", help="播种首批竞品账号")
    parser.add_argument("--show", action="store_true", help="显示当前 master 表内容")
    args = parser.parse_args()

    print("=" * 60)
    print("  PV_OS 竞品发现引擎 V1.0 (Mock)")
    print("=" * 60)

    engine = CompetitorDiscovery(mode="mock")

    if args.show:
        accounts = engine.get_master_accounts()
        print(f"\n  competitor_master.csv: {len(accounts)} 账号")
        for a in accounts:
            print(f"    [{a.get('grade','?')}] {a.get('account_name','?')} ({a.get('platform','?')}) — {a.get('account_type','?')} — {a.get('total_score','?')}分")
    else:
        keywords = [k.strip() for k in args.keywords.split(",")]
        report = engine.run(keywords)

        print(f"\n── 发现日报 {report.date} ──")
        print(f"  关键词: {report.keywords_used}")
        print(f"  候选总数: {report.candidates_total}")
        print(f"  初筛通过: {report.prescreen_passed}")
        print(f"  评分通过: {report.scored}")
        print(f"  S级: {report.grade_s}  A级: {report.grade_a}  B级: {report.grade_b}  C级: {report.grade_c}")
        print(f"\n  入库账号:")
        for a in report.new_accounts:
            print(f"    [{a['grade']}] {a['account_name']} ({a['platform']}) — {a['total_score']}分 — {a['account_type']}")

    print()
