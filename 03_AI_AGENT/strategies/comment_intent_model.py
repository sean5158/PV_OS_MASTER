"""PV_OS 评论意图识别模型 — 语义引擎。

从原始评论文本中通过模式匹配识别用户意图、客户类型、房屋场景和需求信号。
替代原先的关键词匹配，增加：否定检测、上下文感知、权重评分。

设计依据：PV_OS_COMMENT_INTENT_MODEL.md V1.0
业务边界：城市家庭光伏 / 别墅 / 叠拼 / 高价值住宅 / 小商业
禁止：农村光伏 / 大型工商业

Usage::

    from comment_intent_model import IntentAnalyzer, IntentResult

    analyzer = IntentAnalyzer()
    result = analyzer.analyze(
        content="我在成都武侯区别墅，想装一套光伏，能报个价吗？",
        platform="douyin",
        video_title="别墅光伏安装实拍",
        ip_location="四川成都",
    )
    print(result.intent_level)  # 3
    print(result.customer_type)  # 别墅用户
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ══════════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════════

@dataclass
class IntentResult:
    """意图分析完整输出。

    对齐 comment_analyzer/agent.yml 的 analysis 字段和
    PV_OS_COMMENT_INTENT_MODEL.md §八 输出字段。
    """

    # ── 意图分级 ──
    intent_level: int = 0            # 0=无需求 1=潜在兴趣 2=咨询阶段 3=明确购买
    intent_label: str = "无需求"     # 人类可读标签

    # ── 客户分类 ──
    customer_type: str = "家庭用户"  # 别墅用户 | 高价值住宅用户 | 小商业用户 | 家庭用户 | 同行用户
    housing_type: str = "普通住宅"   # 别墅 | 高价值住宅 | 普通住宅 | 商业建筑

    # ── 需求信号 ──
    demand_signals: list[str] = field(default_factory=list)
    # e.g. ["价格咨询", "安装需求", "联系方式请求", "收益关注", "可行性咨询"]

    # ── 区域提示 ──
    region_hints: list[str] = field(default_factory=list)
    # 从评论中提取的区域关键词 e.g. ["成都", "武侯区"]

    # ── 真实性 ──
    is_real_person: bool = True      # 是否疑似机器人/广告
    confidence: float = 0.0          # 意图判断置信度 0.0-1.0

    # ── 元数据 ──
    matched_patterns: list[str] = field(default_factory=list)
    # 命中的模式名称，用于调试和审计

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_level": self.intent_level,
            "intent_label": self.intent_label,
            "customer_type": self.customer_type,
            "housing_type": self.housing_type,
            "demand_signals": self.demand_signals,
            "region_hints": self.region_hints,
            "is_real_person": self.is_real_person,
            "confidence": round(self.confidence, 2),
            "matched_patterns": self.matched_patterns,
        }


# ══════════════════════════════════════════════════════════════════════
# 模式定义
# ══════════════════════════════════════════════════════════════════════

# ── 否定词（降低/取消意图） ──
NEGATION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("negation_骗人",    re.compile(r"(光伏|太阳能).{0,5}(骗人|骗局|假的|没用|坑)")),
    ("negation_装了没用", re.compile(r"装了.{0,5}(没用|没效果|后悔|浪费)")),
    ("negation_乡下",    re.compile(r"(乡下|农村).{0,3}不.{0,3}(装|弄|搞)")),
    ("negation_租的房",  re.compile(r"租的.{0,3}(房|房子)")),  # 租户无决策权
    ("negation_物业不让", re.compile(r"物业.{0,5}(不让|不同意|禁止)")),
    ("negation_免费等",  re.compile(r"(免费|政府|补贴).{0,3}(什么时候|多久|等)")),
    ("negation_不做光伏", re.compile(r"(不.{0,2}(做|干|装|买)|没有.{0,2}(需求|兴趣|想法))")),
]


def _has_negation(content: str) -> list[str]:
    """检测否定/低意向模式。返回命中的模式名列表。"""
    return [name for name, pat in NEGATION_PATTERNS if pat.search(content)]


# ── 明确购买意向（L3） ──
PURCHASE_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    # 联系方式请求（最强信号）
    ("purchase_联系方式", re.compile(r"(怎么|如何|给个|发个|私信|加).{0,5}(联系|电话|微信|V信|方式)"), 3),
    ("purchase_电话",     re.compile(r"(电话|手机).{0,3}(联系|多少|发|给|留)"), 3),
    ("purchase_报价请求",  re.compile(r"(报个|给个|发个|要个).{0,3}(价|报价|价格|预算)"), 3),
    ("purchase_能上门",    re.compile(r"(能|可以|方便).{0,5}(上门|看看|来.{0,2}(家|房子))"), 3),
    ("purchase_想装",     re.compile(r"(想|打算|准备|计划|考虑|决定).{0,3}(装|安|做|弄|搞).{0,3}(光伏|太阳能|发电|一套|个)"), 3),
    ("purchase_多少钱装",  re.compile(r"(装|安|做|搞).{0,5}(多少钱|要多少|大概多少|价格)"), 3),
]


def _detect_purchase(content: str) -> tuple[int, list[str]]:
    """检测明确购买意向。返回 (最高分数, 匹配模式列表)。"""
    max_score = 0
    matched: list[str] = []
    for name, pat, score in PURCHASE_PATTERNS:
        if pat.search(content):
            matched.append(name)
            max_score = max(max_score, score)
    return max_score, matched


# ── 咨询阶段（L2） ──
INQUIRY_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    ("inquiry_报价",     re.compile(r"(报价|多少钱|什么价|多少费用|大概.{0,3}(钱|预算|成本))"), 2),
    ("inquiry_能装吗",   re.compile(r"(能|可以|能不能|可不可以).{0,5}(装|安).{0,5}(吗|光伏|太阳能)"), 2),
    ("inquiry_收益",    re.compile(r"(收益|省.{0,2}(钱|电费)|回本|划算|赚|能省)"), 2),
    ("inquiry_效果",    re.compile(r"(效果|发电量|能发|多少(电|度)|功率|瓦|千瓦)"), 2),
    ("inquiry_怎么收费", re.compile(r"(怎么|如何).{0,3}(收费|算|计费|合作|加盟)"), 2),
    ("inquiry_靠谱吗",  re.compile(r"(靠谱|可信|真的|安全|质量|服务|售后)"), 2),
    ("inquiry_案例",    re.compile(r"(有没有|看看|想看|参考).{0,5}(案例|照片|视频|实拍)"), 2),
    ("inquiry_对比",    re.compile(r"(和|跟|比).{0,5}(比|哪个|怎么样)"), 2),
    ("inquiry_安装条件", re.compile(r"(屋顶|楼顶|房顶|顶楼|露台).{0,5}(能|可以|适合|够.{0,3}装)"), 2),
    ("inquiry_怎么装",  re.compile(r"(怎么|如何|什么流程).{0,5}(装|安|施工|流程|步骤)"), 2),
]


def _detect_inquiry(content: str) -> tuple[int, list[str]]:
    """检测咨询阶段意向。返回 (最高分数, 匹配模式列表)。"""
    max_score = 0
    matched: list[str] = []
    for name, pat, score in INQUIRY_PATTERNS:
        if pat.search(content):
            matched.append(name)
            max_score = max(max_score, score)
    return max_score, matched


# ── 潜在兴趣（L1） ──
INTEREST_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    ("interest_光伏相关", re.compile(r"(光伏|太阳能|发电玻璃|新能源|储能|光伏板)"), 1),
    ("interest_家庭能源", re.compile(r"(家庭.{0,3}(发电|光伏|能源|用电)|省电|电费|屋顶发电)"), 1),
    ("interest_装修关联", re.compile(r"(装修|阳光房|花园|露台|改造).{0,8}(光伏|太阳能|发电)"), 1),
    ("interest_政策",     re.compile(r"(补贴|政策|国家.{0,2}(鼓励|支持|推广)|并网)"), 1),
    ("interest_了解",    re.compile(r"(了解|关注|看看|学习|收藏).{0,5}(光伏|太阳能|发电)"), 1),
    ("interest_我家在",  re.compile(r"(我在|我是|我家|我这).{0,5}(成都|重庆|贵阳|绵阳|德阳|宜宾|南充|遵义)"), 1),  # 川渝黔 + 自我位置
    ("interest_房子类型", re.compile(r"(我.{0,2}(家|房子|屋顶|房).{0,5}(别墅|独栋|叠拼|花园洋房|大平层|阳光房|露台|跃层))"), 1),
]


def _detect_interest(content: str) -> tuple[int, list[str]]:
    """检测潜在兴趣。返回 (最高分数, 匹配模式列表)。"""
    max_score = 0
    matched: list[str] = []
    for name, pat, score in INTEREST_PATTERNS:
        if pat.search(content):
            matched.append(name)
            max_score = max(max_score, score)
    return max_score, matched


# ── 房屋场景识别 ──
HOUSING_PATTERNS: dict[str, tuple[str, re.Pattern[str]]] = {
    "别墅":     ("housing_别墅",     re.compile(r"(别墅|独栋|联排|townhouse)")),
    "高价值住宅": ("housing_高价值",   re.compile(r"(叠拼|叠墅|花园洋房|阳光房|露台|跃层|大平层|复式|顶跃|洋房)")),
    "小商业":   ("housing_小商业",   re.compile(r"(民宿|酒店|餐厅|茶楼|美容院|工作室|棋牌室|饭店|旅馆|商铺|门店|农家乐)")),
}


def _detect_housing(content: str) -> tuple[str, str, list[str]]:
    """检测房屋场景。返回 (customer_type, housing_type, 模式列表)。

    优先级: 别墅 > 高价值住宅 > 小商业 > 家庭用户默认
    """
    matched: list[str] = []
    customer_type = "家庭用户"
    housing_type = "普通住宅"

    for label, (pname, pat) in HOUSING_PATTERNS.items():
        if pat.search(content):
            matched.append(pname)
            if label == "别墅":
                customer_type = "别墅用户"
                housing_type = "别墅"
                return customer_type, housing_type, matched  # 最高优先级
            elif label == "高价值住宅" and housing_type != "别墅":
                customer_type = "高价值住宅用户"
                housing_type = "高价值住宅"
            elif label == "小商业" and housing_type not in ("别墅", "高价值住宅"):
                customer_type = "小商业用户"
                housing_type = "商业建筑"

    return customer_type, housing_type, matched


# ── 区域提示提取 ──
REGION_HINT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("成都", re.compile(r"(成都|武侯|锦江|青羊|金牛|成华|高新|天府|龙泉|双流|温江|郫都|新都)")),
    ("绵阳", re.compile(r"(绵阳|涪城|游仙)")),
    ("德阳", re.compile(r"(德阳|旌阳)")),
    ("宜宾", re.compile(r"(宜宾|翠屏)")),
    ("南充", re.compile(r"(南充|顺庆)")),
    ("重庆", re.compile(r"(重庆|渝北|渝中|江北|沙坪坝|南岸|九龙坡|巴南|北碚|大渡口|万州|涪陵)")),
    ("贵阳", re.compile(r"(贵阳|观山湖|云岩|南明|花溪|乌当|白云|清镇)")),
    ("遵义", re.compile(r"(遵义|红花岗|汇川|播州)")),
    ("四川", re.compile(r"(四川|川)")),
    ("贵州", re.compile(r"(贵州|黔|贵)")),
]


def _detect_region_hints(content: str) -> list[str]:
    """提取评论中的区域关键词。"""
    hints: list[str] = []
    seen: set[str] = set()
    for label, pat in REGION_HINT_PATTERNS:
        if pat.search(content) and label not in seen:
            hints.append(label)
            seen.add(label)
    return hints


# ── 真实性检测 ──
BOT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("bot_微信号",      re.compile(r"(加.{0,2}微|[Vv][Xx信]|[Vv]\s*[:：])")),
    ("bot_兼职广告",     re.compile(r"(兼职|招.{0,2}(聘|工|人|代理)|日结|手赚)")),
    ("bot_Q群",         re.compile(r"([QqQq]{2}群|扣扣群|进群)")),
    ("bot_纯数字",      re.compile(r"^\d{6,}$")),
    ("bot_链接",        re.compile(r"https?://")),
    ("bot_重复评论",     re.compile(r"(前排|沙发|打卡|路过|留名|第一)")),
    ("bot_刷粉",        re.compile(r"(互粉|互赞|回关|关注.{0,2}我|涨粉)")),
]


def _detect_real_person(content: str) -> tuple[bool, list[str]]:
    """检测是否为真实用户评论。

    返回 (is_real_person, 命中的噪声模式列表)。
    """
    noise_matched: list[str] = []
    for name, pat in BOT_PATTERNS:
        if pat.search(content):
            noise_matched.append(name)

    # 满足以下条件判为疑似非真实用户：
    # 1. 命中 ≥ 2 个 bot 模式，或
    # 2. 命中 bot_微信号（强信号），或
    # 3. 纯数字/链接

    if len(noise_matched) >= 2:
        return False, noise_matched
    if "bot_微信号" in noise_matched:
        return False, noise_matched
    if "bot_纯数字" in noise_matched and len(noise_matched) >= 1:
        return False, noise_matched
    if "bot_链接" in noise_matched and len(content.strip()) < 20:
        return False, noise_matched

    return True, noise_matched


# ── 需求信号提取 ──
SIGNAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("价格咨询",     re.compile(r"(报价|个价|多少钱|什么价|价格|预算|费用|成本|收费|划算)")),
    ("安装需求",     re.compile(r"(安装|装.{0,2}(光伏|太阳能|一套|个)|施工|并网)")),
    ("联系方式请求",  re.compile(r"(联系|电话|微信|私信|怎么.{0,2}(找|联系|加))")),
    ("收益关注",     re.compile(r"(收益|省.{0,2}(钱|电)|回本|赚|划算|发电量|能发|多少.{0,2}(电|度))")),
    ("可行性咨询",   re.compile(r"(能装|可以装|能不能|可以吗|适合|条件)")),
    ("案例查看",     re.compile(r"(案例|照片|视频|实拍|看看.{0,2}(装|效果|做完))")),
    ("政策了解",     re.compile(r"(补贴|政策|国家.{0,2}(鼓励|支持|推广)|电网)")),
]


def _detect_demand_signals(content: str) -> list[str]:
    """提取需求信号。"""
    return [name for name, pat in SIGNAL_PATTERNS if pat.search(content)]


# ══════════════════════════════════════════════════════════════════════
# 意图分析器
# ══════════════════════════════════════════════════════════════════════

INTENT_LABELS = {0: "无需求", 1: "潜在兴趣", 2: "咨询阶段", 3: "明确购买"}


class IntentAnalyzer:
    """评论意图分析引擎。

    通过分层模式匹配识别用户意图级别、客户类型、房屋场景和需求信号。
    支持否定检测、上下文感知和真实性判断。
    """

    def analyze(
        self,
        content: str,
        platform: str = "",
        video_title: str = "",
        ip_location: str = "",
    ) -> IntentResult:
        """分析单条评论的意图。

        Args:
            content: 评论文本
            platform: 来源平台
            video_title: 视频标题（上下文）
            ip_location: IP 属地
        """
        content = content.strip()
        text = content.lower()

        # ── 1. 否定检测（最先执行） ──
        negations = _has_negation(content)

        # ── 2. 分层意图识别 ──
        purchase_score, purchase_patterns = _detect_purchase(content)
        inquiry_score, inquiry_patterns = _detect_inquiry(content)
        interest_score, interest_patterns = _detect_interest(content)

        all_patterns = purchase_patterns + inquiry_patterns + interest_patterns

        # 计算原始意图分
        raw_intent = max(purchase_score, inquiry_score, interest_score)

        # ── 3. 否定修正 ──
        if negations:
            # 否定词将意图降级
            if raw_intent >= 2:
                raw_intent = max(0, raw_intent - 2)
            elif raw_intent == 1:
                raw_intent = 0
            all_patterns = [f"↓{p}" for p in all_patterns] + negations

        # ── 4. 上下文增强（视频标题提供额外信号） ──
        if video_title and raw_intent >= 1:
            title_lower = video_title.lower()
            if any(kw in title_lower for kw in ["安装", "报价", "案例", "实拍", "多少钱"]):
                # 视频本身是安装类内容，评论在安装视频下更可能是咨询
                if raw_intent == 1:
                    raw_intent = 2  # 提升一级
                    all_patterns.append("context_video_match")

        intent_level = min(3, max(0, raw_intent))

        # ── 5. 客户类型 & 房屋场景 ──
        customer_type, housing_type, housing_patterns = _detect_housing(content)

        # ── 6. 区域提示 ──
        region_hints = _detect_region_hints(content)

        # ── 7. 真实性 ──
        is_real, bot_patterns = _detect_real_person(content)
        if bot_patterns:
            all_patterns = all_patterns + [f"⚠{p}" for p in bot_patterns]

        # ── 8. 需求信号 ──
        demand_signals = _detect_demand_signals(content)

        # ── 9. 置信度 ──
        signal_count = len(purchase_patterns) + len(inquiry_patterns) + len(demand_signals)
        confidence = min(0.95, 0.3 + signal_count * 0.15)
        if negations:
            confidence = max(0.1, confidence - 0.3)

        # ── 10. 业务边界：仅允许城市家庭光伏场景 ──
        # 如果 housing_type 明确是农村场景，降级处理
        # （当前 CUSTOMER_SCORE_MODEL §8 规则是：不预设农村=低价值，所以这里不降级）
        # 只标记不作为主要目标但保留数据

        return IntentResult(
            intent_level=intent_level,
            intent_label=INTENT_LABELS.get(intent_level, "未知"),
            customer_type=customer_type,
            housing_type=housing_type,
            demand_signals=demand_signals,
            region_hints=region_hints,
            is_real_person=is_real,
            confidence=confidence,
            matched_patterns=all_patterns + housing_patterns,
        )


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    analyzer = IntentAnalyzer()

    test_cases = [
        # (评论, 平台, 视频标题, IP属地, 预期level)
        ("我在成都武侯区别墅，想装一套光伏，能报个价吗？电话联系138xxxx",
         "douyin", "别墅光伏安装实拍", "四川成都", 3, "明确购买"),
        ("重庆江北的叠拼能装光伏吗？大概多少钱？",
         "douyin", "叠拼别墅光伏案例", "重庆", 3, "明确购买"),
        ("贵阳观山湖区阳光房想做光伏，给个报价",
         "xiaohongshu", "阳光房光伏改造", "贵州贵阳", 3, "明确购买"),
        ("绵阳涪城区，我家大平层200平屋顶，能装多少千瓦？",
         "douyin", "大平层光伏方案", "四川绵阳", 2, "咨询阶段"),
        ("这个装了真的省电吗？一年能省多少？",
         "xiaohongshu", "光伏发电省钱吗", "", 2, "咨询阶段"),
        ("现在装光伏还有没有补贴？",
         "douyin", "光伏政策解读", "", 1, "潜在兴趣"),
        ("这个做得真好👍",
         "douyin", "光伏安装", "", 0, "无需求"),
        ("光伏就是骗人的，装了没用",
         "douyin", "", "", 0, "无需求(否定)"),
        ("我在农村自建房想装光伏，有联系方式吗",
         "douyin", "农村光伏", "四川德阳", 3, "明确购买(农村不降级)"),
        ("免费安装什么时候有？等政府项目",
         "douyin", "", "", 0, "无需求(免费期待)"),
    ]

    print("=" * 70)
    print(f"{'评论':<40s} {'预期':>5s} {'实际':>5s} {'客户类型':>12s} {'房屋':>10s}")
    print("-" * 70)

    for content, platform, title, ip, exp_level, exp_label in test_cases:
        r = analyzer.analyze(content, platform=platform, video_title=title, ip_location=ip)
        status = "✓" if r.intent_level == exp_level else "✗"
        short = content[:38] + "…" if len(content) > 38 else content
        print(f"{status} {short:<38s} {exp_level:>5d} {r.intent_level:>5d} {r.customer_type:>12s} {r.housing_type:>10s}  {r.intent_label}")

    print("-" * 70)
    print(f"  需求信号示例: {r.demand_signals}")
    print(f"  命中模式: {r.matched_patterns}")
    print(f"  置信度: {r.confidence:.2f}")
