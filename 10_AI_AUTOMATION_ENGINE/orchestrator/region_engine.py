"""Region matching engine for PV_OS comment pipeline.

Matches comment content and IP location against the Sichuan / Chongqing /
Guizhou region knowledge base.  Outputs structured province / city / district
with a confidence score and match type.

Rules reference (do not redefine here):
  - 00_SYSTEM/PV_OS_CUSTOMER_SCOPE_RULES.md
  - 02_DATA/03_REGION_LIBRARY/REGION_MASTER.md
  - 02_DATA/03_REGION_LIBRARY/REGION_MATCH_RULE.md
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Region knowledge base — authoritative list of target regions
# ---------------------------------------------------------------------------

REGION_DB: dict[str, dict[str, list[str]]] = {
    "四川": {
        "成都": ["锦江区", "武侯区", "双流区", "郫都区", "温江区", "青羊区",
                 "高新区", "成华区", "金牛区", "龙泉驿区", "新都区"],
        "绵阳": ["涪城区", "游仙区"],
        "宜宾": ["翠屏区", "叙州区"],
        "德阳": ["旌阳区", "广汉"],
        "南充": ["顺庆区", "高坪区", "嘉陵区"],
        "泸州": ["龙马潭区", "江阳区"],
    },
    "重庆": {
        "重庆": ["渝北区", "渝中区", "南岸区", "江北区", "沙坪坝区",
                 "九龙坡区", "大渡口区", "巴南区", "江津"],
    },
    "贵州": {
        "贵阳": ["花溪区", "观山湖区", "南明区", "云岩区"],
        "遵义": ["红花岗区", "汇川区"],
        "安顺": ["西秀区"],
    },
}

# Province aliases (e.g. "川" → "四川")
PROVINCE_ALIASES: dict[str, str] = {
    "川": "四川", "蜀": "四川",
    "渝": "重庆",
    "黔": "贵州", "贵": "贵州",
}


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def match_customer_region(ctx: dict[str, Any]) -> dict[str, Any]:
    """Pipeline step: extract region info from comment context.

    Reads ctx["comment"]["content"] and ctx["comment"]["ip_location"],
    writes structured result into ctx["region_analysis"].
    """
    comment = ctx.get("comment", {})
    content = comment.get("content", "")
    ip_location = comment.get("ip_location", "")

    result = match_region(content, ip_location)

    ctx["region_analysis"] = result
    return ctx


def match_region(content: str, ip_location: str) -> dict[str, Any]:
    """Match a single comment against the region DB.

    Returns a dict with:
      province, city, district, region_score, match_type
    """
    # Combine all text sources for matching
    combined = f"{ip_location} {content}"

    province = _match_province(combined)
    city = _match_city(province, combined) if province else ""
    district = _match_district(province, city, combined) if province and city else ""

    # Determine match_type and score
    if district:
        match_type = "administrative_hierarchy"
        region_score = 20
    elif city:
        match_type = "natural_language"
        region_score = 16
    elif province:
        match_type = "fuzzy_match"
        region_score = 12
    else:
        match_type = "unknown"
        region_score = 0

    # Region priority (P0/P1/P2 from agent.yml)
    region_priority = _calc_priority(province, city)

    return {
        "province": province,
        "city": city,
        "district": district,
        "region_score": region_score,
        "match_type": match_type,
        "region_priority": region_priority,
    }


# ---------------------------------------------------------------------------
# internal matchers
# ---------------------------------------------------------------------------

def _match_province(text: str) -> str:
    """Detect province from text (exact name or alias)."""
    scored: list[tuple[str, int]] = []

    for province, cities in REGION_DB.items():
        score = 0
        if province in text:
            score += 10
        # Check city names as secondary province signals
        for city in cities:
            if city in text:
                score += 5
        if score:
            scored.append((province, score))

    if not scored:
        return ""

    scored.sort(key=lambda x: -x[1])
    return scored[0][0]


def _match_city(province: str, text: str) -> str:
    """Find best-matching city within the given province."""
    if not province or province not in REGION_DB:
        return ""

    cities = REGION_DB[province]
    best_city = ""
    best_len = 0
    for city_name in cities:
        if city_name in text and len(city_name) > best_len:
            best_city = city_name
            best_len = len(city_name)
    return best_city


def _match_district(province: str, city: str, text: str) -> str:
    """Find best-matching district within province.city."""
    if not province or not city:
        return ""
    if province not in REGION_DB or city not in REGION_DB[province]:
        return ""

    districts = REGION_DB[province][city]
    best_district = ""
    best_len = 0
    for d in districts:
        if d in text and len(d) > best_len:
            best_district = d
            best_len = len(d)
    return best_district


def _calc_priority(province: str, city: str) -> str:
    """Map province+city to P0/P1/P2 priority tier (agent.yml rules)."""
    p0_cities = {"成都"}
    p1_cities = {"绵阳", "宜宾", "德阳", "南充", "泸州", "重庆"}
    p2_cities = {"贵阳", "遵义", "安顺"}

    if city in p0_cities:
        return "P0"
    if city in p1_cities or province == "重庆":
        return "P1"
    if city in p2_cities or province == "贵州":
        return "P2"
    return "P2"
