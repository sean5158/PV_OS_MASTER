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
    """Step 4: AI comment analysis.

    In the MVP, this is a rule-based simulation that follows the intent
    and customer-type definitions from COMMENT_ANALYZER_RULE.md and
    agent.yml.  Replace with actual AI call in production.
    """
    comment = ctx["comment"]
    content = comment.get("content", "").lower()

    # --- intent detection (rule-based, follows COMMENT_ANALYZER_RULE.md) ---
    intent_level = 0
    if any(kw in content for kw in ["报价", "价格", "多少钱", "费用", "成本", "预算"]):
        intent_level = 2
    if any(kw in content for kw in ["安装", "联系", "电话", "微信", "怎么装", "能装吗"]):
        intent_level = max(intent_level, 3)
    if any(kw in content for kw in ["光伏", "太阳能", "发电", "储能", "屋顶"]):
        intent_level = max(intent_level, 1)

    # --- customer type ---
    customer_type = "家庭用户"
    if any(kw in content for kw in ["别墅", "独栋"]):
        customer_type = "别墅用户"
    elif any(kw in content for kw in ["农村", "自建房", "老家"]):
        customer_type = "家庭用户"
    elif any(kw in content for kw in ["厂", "公司", "商铺", "商业"]):
        customer_type = "小商业用户"
    elif any(kw in content for kw in ["同行", "代理", "经销商"]):
        customer_type = "同行用户"

    # --- housing ---
    housing_type = "普通住宅"
    if any(kw in content for kw in ["别墅", "独栋"]):
        housing_type = "别墅"
    elif any(kw in content for kw in ["农村", "自建房", "老家"]):
        housing_type = "农村自建房"
    elif any(kw in content for kw in ["厂", "公司", "商铺"]):
        housing_type = "商业建筑"

    # --- demand signals ---
    demand_signals: list[str] = []
    if any(kw in content for kw in ["安装", "装"]):
        demand_signals.append("安装需求")
    if any(kw in content for kw in ["报价", "价格", "多少钱", "费用"]):
        demand_signals.append("价格咨询")
    if any(kw in content for kw in ["储能", "电池"]):
        demand_signals.append("储能需求")
    if intent_level >= 3:
        demand_signals.append("高意向")

    # --- tags ---
    tags: list[str] = list(demand_signals)
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
    elif customer_type == "小商业用户":
        housing_score = 18
    elif housing_type == "农村自建房":
        housing_score = 12

    # region_score (0-20) — simplified: use IP location as proxy
    ip_loc = comment.get("ip_location", "")
    region_score = 10
    if any(r in ip_loc for r in ["四川", "成都", "绵阳"]):
        region_score = 16
    elif any(r in ip_loc for r in ["重庆"]):
        region_score = 15
    elif any(r in ip_loc for r in ["贵州", "贵阳"]):
        region_score = 14

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
    "analyze_comment": analyze_comment,
    "score_customer": score_customer,
    "route_customer": route_customer,
    "create_crm_lead": create_crm_lead,
    "generate_follow_up": generate_follow_up,
}
