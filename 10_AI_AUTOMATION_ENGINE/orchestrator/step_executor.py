"""Workflow step executors for PV_OS automation engine.

Each function maps to a step name in comment_to_lead_pipeline.yml.
Executors read business rules from existing .md / .yml files.
No business logic is duplicated — rules are referenced, not redefined.
"""

from __future__ import annotations

import csv
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from region_engine import match_region as region_matcher

# Intent model integration (P1-2)
_ANALYZER = None

def _get_analyzer():
    global _ANALYZER
    if _ANALYZER is None:
        try:
            import sys
            from pathlib import Path as _Path
            _strat_dir = _Path(__file__).resolve().parent.parent.parent / "03_AI_AGENT" / "strategies"
            sys.path.insert(0, str(_strat_dir))
            from comment_intent_model import IntentAnalyzer
            _ANALYZER = IntentAnalyzer()
        except ImportError:
            pass
    return _ANALYZER

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CRM_ROOT = PROJECT_ROOT / "05_CUSTOMER_CRM"
LEADS_RAW = CRM_ROOT / "leads" / "raw"
LEADS_HOT = CRM_ROOT / "leads" / "hot"
LEADS_QUALIFIED = CRM_ROOT / "leads" / "qualified"
LEADS_MASTER_CSV = CRM_ROOT / "leads" / "leads_master.csv"
NURTURE_POOL_CSV = CRM_ROOT / "leads" / "nurture_pool.csv"
ASSET_LIBRARY_CSV = CRM_ROOT / "leads" / "comment_asset_library.csv"
FOLLOW_UPS_DIR = CRM_ROOT / "follow_ups"

TZ_SHANGHAI = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# step: collect_comment
# ---------------------------------------------------------------------------

def collect_comment(ctx: dict[str, Any], event: Any) -> dict[str, Any]:
    """Step 1: pull comment data from the trigger event.

    The trigger (event_bus) already provides the comment as event payload.
    This step normalises it into the standard workflow context.
    """
    comment = dict(event.payload) if hasattr(event, "payload") else {}

    # Apply defaults from comment_schema.md
    ctx["comment"] = {
        "id": comment.get("id", f"douyin_{uuid.uuid4().hex[:8]}"),
        "platform": comment.get("platform", "douyin"),
        "content": comment.get("content", comment.get("comment_text", "")),
        "author": comment.get("author", ""),
        "create_time": comment.get("create_time", _now()),
        "source_url": comment.get("source_url", ""),
        "source_account": comment.get("source_account", ""),
        "source_account_id": comment.get("source_account_id", ""),
        "ip_location": comment.get("ip_location", ""),
        "video_title": comment.get("video_title", ""),
        "keyword": comment.get("keyword", ""),
        "collected_time": _now(),
        "processing_status": "collected",
    }
    return ctx


# ---------------------------------------------------------------------------
# step: save_comment_asset
# ---------------------------------------------------------------------------

def save_comment_asset(ctx: dict[str, Any]) -> dict[str, Any]:
    """Step 2: persist comment to asset library (full history, never discard)."""
    comment = ctx["comment"]
    _ensure_dir(ASSET_LIBRARY_CSV.parent)

    fieldnames = [
        "id", "platform", "content", "author", "create_time",
        "source_url", "ip_location", "collected_time", "processing_status",
    ]
    write_header = not ASSET_LIBRARY_CSV.exists()
    with open(ASSET_LIBRARY_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow({k: comment.get(k, "") for k in fieldnames})

    ctx["comment"]["processing_status"] = "saved"
    return ctx


# ---------------------------------------------------------------------------
# step: evaluate_comment_time
# ---------------------------------------------------------------------------

def evaluate_comment_time(ctx: dict[str, Any]) -> dict[str, Any]:
    """Step 3: apply 7-day sales window rule from COMMENT_TIME_AND_MATCH_RULE.md."""
    comment = ctx["comment"]
    raw_time = comment.get("create_time", "")

    try:
        if "T" in raw_time:
            ts = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        else:
            ts = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=TZ_SHANGHAI)
    except (ValueError, TypeError):
        ts = datetime.now(TZ_SHANGHAI)

    now = datetime.now(TZ_SHANGHAI)
    age_days = (now - ts).days

    comment["comment_age_days"] = age_days
    comment["is_recent"] = age_days <= 7
    comment["time_bucket"] = "recent" if age_days <= 7 else "historical"
    comment["sales_priority"] = age_days <= 7

    return ctx


# ---------------------------------------------------------------------------
# step: analyze_comment (comment_analyzer agent — mock / rule-based)
# ---------------------------------------------------------------------------

def analyze_comment(ctx: dict[str, Any]) -> dict[str, Any]:
    """Step 4: AI comment analysis — 意图语义引擎。

    使用 comment_intent_model (P1-2) 进行模式匹配语义分析，
    替代原有的简单关键词匹配。

    设计依据：PV_OS_COMMENT_INTENT_MODEL.md V1.0
    """
    comment = ctx.get("comment", {})
    content = comment.get("content", "")
    platform = comment.get("platform", "")
    video_title = comment.get("video_title", "")
    ip_location = comment.get("ip_location", "")

    # 优先使用语义意图模型
    analyzer = _get_analyzer()
    if analyzer:
        result = analyzer.analyze(
            content=content,
            platform=platform,
            video_title=video_title,
            ip_location=ip_location,
        )
        intent_level = result.intent_level
        customer_type = result.customer_type
        housing_type = result.housing_type
        demand_signals = result.demand_signals
        tags = demand_signals.copy()
        if customer_type == "别墅用户":
            tags.append("别墅客户")
        if customer_type == "高价值住宅用户":
            tags.append("高价值住宅客户")
        if result.region_hints:
            tags.extend(result.region_hints[:3])  # 最多3个区域标签
        sentiment = "positive" if intent_level >= 2 else "neutral"
        if not result.is_real_person:
            sentiment = "suspicious"

        ctx["analysis"] = {
            "customer_type": customer_type,
            "housing_type": housing_type,
            "intent_level": intent_level,
            "demand_signals": demand_signals,
            "tags": tags,
            "sentiment": sentiment,
            # 新增语义模型字段
            "intent_label": result.intent_label,
            "confidence": result.confidence,
            "is_real_person": result.is_real_person,
            "matched_patterns": result.matched_patterns,
        }
        return ctx

    # ── 回退：关键词匹配（当意图模型不可用时） ──
    text = content.lower()

    # intent detection
    intent_level = 0
    if any(kw in text for kw in ["报价", "价格", "多少钱", "费用", "成本", "预算"]):
        intent_level = 2
    if any(kw in text for kw in ["安装", "联系", "电话", "微信", "怎么装", "能装吗"]):
        intent_level = max(intent_level, 3)
    if any(kw in text for kw in ["光伏", "太阳能", "发电", "储能", "屋顶"]):
        intent_level = max(intent_level, 1)

    # customer type
    customer_type = "家庭用户"
    if any(kw in text for kw in ["别墅", "独栋", "叠拼", "联排", "花园洋房", "阳光房", "露台", "跃层", "大平层"]):
        customer_type = "别墅用户"
    elif any(kw in text for kw in ["民宿", "酒店", "餐厅", "茶楼", "美容院", "工作室", "棋牌室", "饭店", "旅馆", "厂", "公司", "商铺", "商业", "店"]):
        customer_type = "小商业用户"
    elif any(kw in text for kw in ["同行", "代理", "经销商"]):
        customer_type = "同行用户"

    # housing
    housing_type = "普通住宅"
    if any(kw in text for kw in ["别墅", "独栋"]):
        housing_type = "别墅"
    elif any(kw in text for kw in ["叠拼", "联排", "花园洋房", "阳光房", "露台", "跃层", "大平层"]):
        housing_type = "高价值住宅"
    elif any(kw in text for kw in ["农村", "自建房", "老家"]):
        housing_type = "农村自建房"
    elif any(kw in text for kw in ["民宿", "酒店", "餐厅", "茶楼", "美容院", "工作室", "厂", "公司", "商铺", "店"]):
        housing_type = "商业建筑"

    demand_signals: list[str] = []
    if any(kw in text for kw in ["安装", "装"]):
        demand_signals.append("安装需求")
    if any(kw in text for kw in ["报价", "价格", "多少钱", "费用"]):
        demand_signals.append("价格咨询")
    if any(kw in text for kw in ["储能", "电池"]):
        demand_signals.append("储能需求")
    if intent_level >= 3:
        demand_signals.append("高意向")

    tags = list(demand_signals)
    if customer_type == "别墅用户":
        tags.append("别墅客户")
    if housing_type == "农村自建房":
        tags.append("农村客户")

    ctx["analysis"] = {
        "customer_type": customer_type,
        "housing_type": housing_type,
        "intent_level": intent_level,
        "demand_signals": demand_signals,
        "tags": tags,
        "sentiment": "positive" if intent_level >= 2 else "neutral",
    }
    return ctx

# ---------------------------------------------------------------------------
# step: match_customer_region
# ---------------------------------------------------------------------------

def match_customer_region(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Step: customer region detection.

    Calls region_engine.match_region() with comment content + ip_location,
    stores structured result in ctx["region"] for downstream scoring.
    """
    comment = ctx.get("comment", {})
    content = comment.get("content", "")
    ip_location = comment.get("ip_location", "")

    result = region_matcher(content, ip_location)

    ctx["region"] = result
    ctx["region_analysis"] = result  # alias for analysis consumers
    return ctx

# ---------------------------------------------------------------------------
# step: score_customer (lead_scoring_agent — rule-based)
# ---------------------------------------------------------------------------

def score_customer(ctx: dict[str, Any]) -> dict[str, Any]:
    """Step 5: score the customer using the scoring model from
    CUSTOMER_SCORE_MODEL.md and lead_scoring_agent/agent.yml.

    100-point system:
      - demand_score   (max 40)
      - region_score   (max 20)
      - housing_score  (max 20)
      - time_score     (max 10)
      - authenticity   (max 10)
    """
    analysis = ctx.get("analysis", {})
    comment = ctx.get("comment", {})

    intent = analysis.get("intent_level", 0)
    customer_type = analysis.get("customer_type", "")
    housing_type = analysis.get("housing_type", "")
    is_recent = comment.get("is_recent", False)

    # demand_score (0-40)
    demand_map = {0: 0, 1: 10, 2: 25, 3: 40}
    demand_score = demand_map.get(intent, 0)

    # housing_score (0-20)
    housing_score = 10  # default family
    if housing_type == "别墅" or customer_type == "别墅用户":
        housing_score = 20
    elif housing_type == "高价值住宅":
        housing_score = 20
    elif customer_type == "小商业用户":
        housing_score = 18
    elif housing_type == "农村自建房":
        housing_score = 12

    # region_score from match_customer_region

    region = ctx.get("region", {})

    region_score = region.get(
        "region_score",
        5
)
    # time_score (0-10)
    time_score = 10 if is_recent else 5

    # authenticity (0-10) — simplified
    authenticity_score = 10 if comment.get("content", "") else 5

    total_score = demand_score + housing_score + region_score + time_score + authenticity_score

    # grade from CUSTOMER_SCORE_MODEL.md: S>=80, A=60-79, B=35-59, C<35
    if total_score >= 80:
        lead_grade = "S"
    elif total_score >= 60:
        lead_grade = "A"
    elif total_score >= 35:
        lead_grade = "B"
    else:
        lead_grade = "C"

    # urgency
    if lead_grade == "S":
        urgency = "high"
    elif lead_grade == "A":
        urgency = "medium"
    else:
        urgency = "low"

    ctx["scoring"] = {
        "demand_score": demand_score,
        "region_score": region_score,
        "housing_score": housing_score,
        "time_score": time_score,
        "authenticity_score": authenticity_score,
        "total_score": total_score,
        "lead_grade": lead_grade,
        "contact_intent": intent >= 2,
        "urgency": urgency,
    }
    return ctx


# ---------------------------------------------------------------------------
# step: route_customer
# ---------------------------------------------------------------------------

def route_customer(ctx: dict[str, Any]) -> dict[str, Any]:
    """Step 6: route leads by grade (S/A → master, B → nurture, C → asset)."""
    grade = ctx["scoring"]["lead_grade"]
    ctx["routing"] = {"grade": grade}
    return ctx


# ---------------------------------------------------------------------------
# step: create_crm_lead
# ---------------------------------------------------------------------------

def create_crm_lead(ctx: dict[str, Any]) -> dict[str, Any]:
    """Step 7: persist CRM lead to the appropriate directory/CSV."""
    comment = ctx["comment"]
    analysis = ctx["analysis"]
    scoring = ctx["scoring"]
    grade = scoring["lead_grade"]
    lead_id = f"PV_LEAD_{uuid.uuid4().hex[:8].upper()}"

    lead_record = {
        "lead_id": lead_id,
        "platform": comment.get("platform", ""),
        "comment_text": comment.get("content", ""),
        "city": comment.get("ip_location", ""),
        "district": "",
        "province": comment.get("ip_location", ""),
        "customer_type": analysis.get("customer_type", ""),
        "housing_type": analysis.get("housing_type", ""),
        "demand_signals": "|".join(analysis.get("demand_signals", [])),
        "lead_score": str(scoring["total_score"]),
        "lead_grade": grade,
        "contact_intent": str(scoring["contact_intent"]),
        "urgency": scoring["urgency"],
        "status": "new",
        "created_at": _now(),
    }

    # Write to grade-specific CSV (follows agent.yml routing)
    if grade == "S":
        _write_lead_csv(LEADS_HOT / "hot_leads.csv", lead_record)
    elif grade == "A":
        _write_lead_csv(LEADS_QUALIFIED / "qualified_leads.csv", lead_record)
    elif grade == "B":
        _write_lead_csv(NURTURE_POOL_CSV, lead_record)
    # C goes to asset library (step 2 already saves it)

    # Also write to leads_master.csv for S/A
    if grade in ("S", "A"):
        _write_lead_csv(LEADS_MASTER_CSV, lead_record)

    ctx["lead"] = lead_record
    return ctx


def _write_lead_csv(csv_path: Path, record: dict[str, str]) -> None:
    _ensure_dir(csv_path.parent)
    fieldnames = list(record.keys())
    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(record)



# ---------------------------------------------------------------------------
# step: analyze_source_account (competitor_account_agent — P1-3)
# ---------------------------------------------------------------------------

# Cache for competitor accounts CSV
_COMPETITOR_CACHE: dict[str, dict[str, str]] | None = None
_COMPETITOR_CACHE_TIME: str = ""

def _load_competitor_cache() -> dict[str, dict[str, str]]:
    """Lazy-load competitor_accounts.csv into a lookup cache."""
    global _COMPETITOR_CACHE, _COMPETITOR_CACHE_TIME
    now = datetime.now(TZ_SHANGHAI).strftime("%Y%m%d_%H")
    if _COMPETITOR_CACHE is not None and _COMPETITOR_CACHE_TIME == now:
        return _COMPETITOR_CACHE

    csv_path = PROJECT_ROOT / "02_DATA" / "02_COMPETITOR_DATABASE" / "competitor_accounts.csv"
    cache: dict[str, dict[str, str]] = {}
    if csv_path.exists():
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row.get('platform', '')}|{row.get('account_id', '')}"
                cache[key] = dict(row)
                # Also index by account_name for fuzzy lookup
                name = row.get("account_name", "").strip()
                if name:
                    cache[f"name|{name}"] = dict(row)

    _COMPETITOR_CACHE = cache
    _COMPETITOR_CACHE_TIME = now
    return cache


def analyze_source_account(ctx: dict[str, Any], event: Any) -> dict[str, Any]:
    """Step 1.5: 竞品来源价值分析。

    判断评论来源账号的类型、权威度和客户来源价值。
    基于 competitor_account_agent/agent.yml V1.1 定义的评分模型。

    输出字段:
        - account_category: 账号分类 (个人博主/企业安装商/行业媒体/无法判断)
        - account_authority_score: 账号权威度 0-100
        - customer_source_score: 客户来源价值 0-100
    """
    comment = ctx.get("comment", {})
    platform = comment.get("platform", "")
    source_account = comment.get("source_account", comment.get("account_name", ""))
    video_title = comment.get("video_title", "")

    # ── 1. 尝试从竞品主表精确匹配 ──
    cache = _load_competitor_cache()
    source_account_id = comment.get("source_account_id", "")

    cache_key = f"{platform}|{source_account_id}"
    if cache_key in cache:
        row = cache[cache_key]
        ctx["account_source"] = {
            "account_category": _map_account_type(row.get("account_type", "")),
            "account_authority_score": int(row.get("account_authority_score", 50)),
            "customer_source_score": int(row.get("customer_source_score", 50)),
            "monitor_level": row.get("monitor_level", "B"),
            "match_type": "exact_csv",
        }
        return ctx

    # 按名称模糊匹配
    if source_account:
        name_key = f"name|{source_account}"
        if name_key in cache:
            row = cache[name_key]
            ctx["account_source"] = {
                "account_category": _map_account_type(row.get("account_type", "")),
                "account_authority_score": int(row.get("account_authority_score", 50)),
                "customer_source_score": int(row.get("customer_source_score", 50)),
                "monitor_level": row.get("monitor_level", "B"),
                "match_type": "name_match",
            }
            return ctx

    # ── 2. 启发式分析（无 CSV 匹配时） ──
    # 基于评论的视频标题 + 账号名推断

    account_info = f"{source_account} {video_title}".lower()
    content_text = comment.get("content", "").lower()

    # 2a. 账号分类
    account_category = _classify_account(source_account, video_title)

    # 2b. 账号权威度 (0-100)
    authority_score = _score_authority(source_account, video_title, content_text)

    # 2c. 客户来源价值 (0-100) — 核心指标
    customer_source_score = _score_customer_source(
        source_account, video_title, content_text, platform
    )

    ctx["account_source"] = {
        "account_category": account_category,
        "account_authority_score": authority_score,
        "customer_source_score": customer_source_score,
        "monitor_level": _to_monitor_level(customer_source_score),
        "match_type": "heuristic",
    }
    return ctx


def _map_account_type(atype: str) -> str:
    """将 CSV account_type 映射到标准分类。"""
    mapping = {
        "个人IP账号": "个人光伏内容博主",
        "企业账号": "光伏企业/品牌/安装公司",
        "媒体账号": "行业媒体/科普账号",
    }
    return mapping.get(atype, atype or "无法判断")


def _classify_account(account_name: str, video_title: str) -> str:
    """启发式账号分类。

    基于 competitor_account_agent/agent.yml §account_category。
    优先级: 个人博主 > 企业 > 媒体 > 默认。
    """
    combined = f"{account_name} {video_title}".lower()
    aname = account_name.lower()

    # Type A: 个人光伏内容博主 — 最高优先级
    personal_signals = ["光伏", "太阳能", "发电", "新能源", "储能", "发电玻璃", "装修日记", "改造", "分享"]
    personal_name_hints = ["哥", "姐", "先生", "老师", "叔", "姨", "同学", "博主", "日记", "记录",
                          "老王", "老李", "老张", "老陈", "老刘", "老赵", "小", "阿"]
    has_pv_signal = any(kw in combined for kw in personal_signals)
    has_personal = any(kw in aname for kw in personal_name_hints)

    if has_pv_signal and has_personal:
        return "个人光伏内容博主"

    # Type B: 光伏企业/品牌/安装公司 — 明确企业信号
    enterprise_signals = ["公司", "安装公司", "品牌", "厂家", "集团", "官方", "团队", "服务"]
    enterprise_strong = ["公司", "品牌", "厂家", "集团", "官方"]
    if any(kw in combined for kw in enterprise_strong):
        return "光伏企业/品牌/安装公司"
    if any(kw in combined for kw in enterprise_signals) and not has_personal:
        return "光伏企业/品牌/安装公司"

    # Type C: 行业媒体/科普
    media_signals = ["知识", "科普", "讲解", "资讯", "新闻", "课堂", "学堂", "百科", "技术"]
    if any(kw in combined for kw in media_signals):
        return "行业媒体/科普账号"

    # Default: 光伏相关 → 个人博主
    if has_pv_signal:
        return "个人光伏内容博主"

    return "无法判断"


def _score_authority(account_name: str, video_title: str, content: str) -> int:
    """估算账号权威度 0-100。

    因素: 内容相关度 + 专业术语密度 + 信息量
    基于 agent.yml §scoring_model.account_authority_score。
    """
    combined = f"{account_name} {video_title} {content}".lower()
    score = 0

    # 内容光伏相关度 (0-40)
    pv_terms = ["光伏", "太阳能", "发电", "储能", "并网", "逆变器", "组件", "电池"]
    pv_count = sum(1 for t in pv_terms if t in combined)
    score += min(40, pv_count * 10)

    # 专业度 (0-30)
    tech_terms = ["kw", "千瓦", "装机", "效率", "转化", "单晶", "多晶", "薄膜", "perc", "hjt"]
    tech_count = sum(1 for t in tech_terms if t in combined)
    score += min(30, tech_count * 10)

    # 信息丰富度 (0-20)
    if len(video_title) > 10:
        score += 10
    if len(content) > 30:
        score += 10

    # 品牌/公司加成 (0-10)
    brand_signals = ["官方", "品牌", "公司", "集团", "认证", "资质"]
    if any(kw in combined for kw in brand_signals):
        score += 10

    return min(100, max(0, score))


def _score_customer_source(
    account_name: str, video_title: str, content: str, platform: str
) -> int:
    """估算客户来源价值 0-100。

    核心判断: 这个账号的评论区能否产生川渝黔家庭光伏客户？
    基于 agent.yml §scoring_model.customer_source_score。

    权重: 区域评论 40% + 客户意向 30% + 房屋场景 20% + 账号活跃 10%
    """
    combined = f"{account_name} {video_title} {content}".lower()
    score = 0

    # 1. 区域评论信号 (0-40)
    region_terms = [
        "四川", "成都", "绵阳", "德阳", "宜宾", "南充", "川",
        "重庆", "渝", "渝北", "江北", "贵阳", "遵义", "贵州", "黔",
    ]
    region_count = sum(1 for t in region_terms if t in combined)
    score += min(40, region_count * 15)

    # 2. 客户意向信号 (0-30)
    intent_terms = [
        "想安装", "准备安装", "多少钱", "报价", "联系", "可以装吗",
        "有没有安装", "怎么联系", "推荐", "价格", "安装公司",
    ]
    intent_count = sum(1 for t in intent_terms if t in combined)
    score += min(30, intent_count * 10)

    # 3. 房屋场景信号 (0-20)
    housing_terms = [
        "别墅", "独栋", "叠拼", "阳光房", "露台", "花园洋房",
        "大平层", "屋顶", "楼顶", "顶楼", "跃层",
    ]
    housing_count = sum(1 for t in housing_terms if t in combined)
    score += min(20, housing_count * 8)

    # 4. 账号活跃度/内容匹配 (0-10)
    activity_signals = ["安装", "实拍", "案例", "改造", "施工"]
    if any(kw in combined for kw in activity_signals):
        score += 5
    if platform == "douyin":
        score += 3  # 抖音是最高价值来源平台
    if video_title and len(video_title) > 5:
        score += 2

    return min(100, max(0, score))


def _to_monitor_level(customer_source_score: int) -> str:
    """客户来源分 → 监控等级。"""
    if customer_source_score >= 80:
        return "S"
    elif customer_source_score >= 60:
        return "A"
    elif customer_source_score >= 40:
        return "B"
    return "C"

# ---------------------------------------------------------------------------
# step: generate_follow_up
# ---------------------------------------------------------------------------

def generate_follow_up(ctx: dict[str, Any]) -> dict[str, Any]:
    """Step 8: create follow-up task for S/A leads."""
    grade = ctx["scoring"]["lead_grade"]
    if grade not in ("S", "A"):
        return ctx

    lead = ctx.get("lead", {})
    task = {
        "task_id": f"FU_{uuid.uuid4().hex[:8].upper()}",
        "lead_id": lead.get("lead_id", ""),
        "lead_grade": grade,
        "urgency": ctx["scoring"]["urgency"],
        "action": "电话联系" if grade == "S" else "发送方案",
        "created_at": _now(),
        "due_by": (datetime.now(TZ_SHANGHAI) + timedelta(days=1)).strftime("%Y-%m-%d"),
        "status": "pending",
    }

    _ensure_dir(FOLLOW_UPS_DIR)
    task_file = FOLLOW_UPS_DIR / f"{task['task_id']}.json"
    task_file.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")

    ctx["follow_up"] = task
    return ctx


# ---------------------------------------------------------------------------
# step registry — maps YAML step names → handler functions
# ---------------------------------------------------------------------------

STEP_REGISTRY = {
    "collect_comment": collect_comment,
    "save_comment_asset": save_comment_asset,
    "evaluate_comment_time": evaluate_comment_time,
    "match_customer_region": match_customer_region,
    "analyze_comment": analyze_comment,
    "score_customer": score_customer,
    "route_customer": route_customer,
    "create_crm_lead": create_crm_lead,
    "analyze_source_account": analyze_source_account,
    "generate_follow_up": generate_follow_up,
}
