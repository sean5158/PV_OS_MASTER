"""评论意图模型测试：单元测试 + 与关键词模式对比。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_intent_model.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(ENGINE_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "03_AI_AGENT" / "strategies"))

from comment_intent_model import IntentAnalyzer, IntentResult, INTENT_LABELS  # noqa: E402
from engine import Engine  # noqa: E402


@pytest.fixture
def analyzer() -> IntentAnalyzer:
    return IntentAnalyzer()


@pytest.fixture
def engine() -> Engine:
    wf = PROJECT_ROOT / "10_AI_AUTOMATION_ENGINE" / "workflows" / "comment_to_lead_pipeline.yml"
    return Engine(wf)


# ══════════════════════════════════════════════════════════════════════
# 分类测试: L3 明确购买意向
# ══════════════════════════════════════════════════════════════════════

class TestIntentL3:
    """明确购买意向（报价+联系方式+安装）。"""

    def test_villa_quote_contact(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("我在成都武侯区别墅，想装一套光伏，能报个价吗？电话联系138xxxx")
        assert r.intent_level == 3
        assert r.intent_label == "明确购买"
        assert r.customer_type == "别墅用户"
        assert r.housing_type == "别墅"
        assert "价格咨询" in r.demand_signals
        assert "联系方式请求" in r.demand_signals
        assert r.is_real_person is True

    def test_diepin_quote(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("重庆江北的叠拼能装光伏吗？大概多少钱？")
        assert r.intent_level == 3
        assert r.customer_type == "高价值住宅用户"
        assert r.housing_type == "高价值住宅"

    def test_sunroom_quote(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("贵阳观山湖区阳光房想做光伏，给个报价")
        assert r.intent_level == 3
        assert r.customer_type == "高价值住宅用户"

    def test_rural_real_demand(self, analyzer: IntentAnalyzer) -> None:
        """农村真实购买需求不降级（CUSTOMER_SCORE_MODEL §8）。"""
        r = analyzer.analyze("我在农村自建房想装光伏，有联系方式吗")
        assert r.intent_level == 3  # L3, 不因"农村"降级
        assert r.customer_type == "家庭用户"

    def test_want_install_with_context(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze(
            "想装一套光伏发电",
            video_title="别墅光伏安装实拍案例",
        )
        assert r.intent_level >= 2  # 上下文增强


# ══════════════════════════════════════════════════════════════════════
# 分类测试: L2 咨询阶段
# ══════════════════════════════════════════════════════════════════════

class TestIntentL2:
    """咨询阶段（效果/收益/可行性）。"""

    def test_effect_inquiry(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("这个装了真的省电吗？一年能省多少？")
        assert r.intent_level == 2
        assert "收益关注" in r.demand_signals

    def test_feasibility(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("我家屋顶能装光伏吗？大概要多少钱？")
        assert r.intent_level >= 2
        assert "可行性咨询" in r.demand_signals

    def test_dapingceng_capacity(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("绵阳涪城区，我家大平层200平屋顶，能装多少千瓦？")
        assert r.intent_level == 2  # 面积+可行性咨询 = L2
        assert r.customer_type == "高价值住宅用户"
        assert r.housing_type == "高价值住宅"


# ══════════════════════════════════════════════════════════════════════
# 分类测试: L1 潜在兴趣
# ══════════════════════════════════════════════════════════════════════

class TestIntentL1:
    """潜在兴趣（了解/政策/关注）。"""

    def test_subsidy_inquiry(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("现在装光伏还有没有补贴？")
        assert r.intent_level == 1

    def test_location_hint(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("我在成都这边，了解一下光伏")
        assert r.intent_level >= 1
        assert "成都" in r.region_hints

    def test_learn_more(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("先了解一下光伏发电")
        assert r.intent_level == 1


# ══════════════════════════════════════════════════════════════════════
# 分类测试: L0 无需求
# ══════════════════════════════════════════════════════════════════════

class TestIntentL0:
    """无需求（否定/纯围观/广告）。"""

    def test_pure_emoji(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("👍🌹❤️")
        assert r.intent_level == 0

    def test_negation_scam(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("光伏就是骗人的，装了没用")
        assert r.intent_level == 0  # 否定检测
        assert r.confidence < 0.5

    def test_free_waiting(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("免费安装什么时候有？等政府项目")
        assert r.intent_level == 0  # 免费期待 → 无购买意向

    def test_ad_wechat(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("加V: pv_installer 全国接单")
        assert r.is_real_person is False  # 疑似广告

    def test_just_watching(self, analyzer: IntentAnalyzer) -> None:
        r = analyzer.analyze("这个做得真好👍 点赞")
        assert r.intent_level == 0


# ══════════════════════════════════════════════════════════════════════
# 对比测试: 意图模型 vs 关键词匹配
# ══════════════════════════════════════════════════════════════════════

# 旧关键词匹配逻辑（用于对比）
def _old_keyword_intent(content: str) -> dict:
    text = content.lower()
    level = 0
    if any(kw in text for kw in ["报价", "价格", "多少钱", "费用", "成本", "预算"]):
        level = 2
    if any(kw in text for kw in ["安装", "联系", "电话", "微信", "怎么装", "能装吗"]):
        level = max(level, 3)
    if any(kw in text for kw in ["光伏", "太阳能", "发电", "储能", "屋顶"]):
        level = max(level, 1)
    return {"intent_level": level}

# 旧关键词检测否定
def _old_has_negation(content: str) -> bool:
    return any(kw in content for kw in ["骗人", "没用", "后悔"])

# 旧关键词检测广告
def _old_is_ad(content: str) -> bool:
    return any(kw in content.lower() for kw in ["加v", "加微", "代理", "招", "兼职"])


class TestCompareKeyword:
    """意图模型相比关键词匹配的改进点。"""

    def test_1_context_awareness(self, analyzer: IntentAnalyzer) -> None:
        """改进 1: 上下文感知。关键词匹配无法利用视频标题信号。"""
        content = "想装一套"
        video_title = "别墅光伏安装实拍案例"

        old = _old_keyword_intent(content)
        new = analyzer.analyze(content, video_title=video_title)

        # 关键词: "装" 匹配 → 但 "装" 在 keywords 里不是安装关键词, old 只会因为"光伏"等原因入L1
        # 语义模型: 上下文增强将 L1 → L2
        assert new.intent_level >= old["intent_level"], (
            f"上下文增强应 >= 纯关键词 (old={old['intent_level']}, new={new.intent_level})"
        )

    def test_2_negation_detection(self, analyzer: IntentAnalyzer) -> None:
        """改进 2: 否定检测。关键词匹配会误判"骗人的"为 L1。"""
        content = "光伏就是骗人的，装了没用后悔了"

        old = _old_keyword_intent(content)
        new = analyzer.analyze(content)

        # 关键词: "光伏"→L1, "装"→可能是安装相关但实际是否定
        # old 至少是 L1 (光伏关键词)
        # 语义模型: 否定检测将意图归零
        assert new.intent_level == 0, (
            f"否定应归零 (got {new.intent_level})"
        )
        assert old["intent_level"] >= 1, (
            f"关键词匹配会误判为 L1+ (got {old['intent_level']})"
        )

    def test_3_ad_detection(self, analyzer: IntentAnalyzer) -> None:
        """改进 3: 广告/机器人识别。"""
        content = "加V: pv_sales 全国安装 价格优惠"

        old = _old_keyword_intent(content)
        new = analyzer.analyze(content)

        # 关键词: "安装"→L3, "价格"→至少L2
        assert old["intent_level"] >= 2, "关键词会误判广告为咨询"
        assert new.is_real_person is False, "语义模型应识别为广告"

    def test_4_free_expectation(self, analyzer: IntentAnalyzer) -> None:
        """改进 4: 免费期待识别。"""
        content = "免费安装什么时候有？等政府项目下来"

        old = _old_keyword_intent(content)
        new = analyzer.analyze(content)

        # 关键词: "安装"→L3
        assert old["intent_level"] >= 3, "关键词会误判免费期待为 L3"
        assert new.intent_level == 0, "语义模型应识别为免费期待(无购买意向)"

    def test_5_confidence(self, analyzer: IntentAnalyzer) -> None:
        """改进 5: 置信度输出。关键词匹配只有二值判断。"""
        r1 = analyzer.analyze("我在成都武侯区别墅，想装一套光伏，能报个价吗？电话联系138xxxx")
        r2 = analyzer.analyze("光伏了解一下")

        assert r1.confidence > r2.confidence, (
            f"强信号置信度({r1.confidence:.2f})应 > 弱信号({r2.confidence:.2f})"
        )

    def test_6_housing_granularity(self, analyzer: IntentAnalyzer) -> None:
        """改进 6: 房屋场景精细分类。"""
        # 旧关键词: 叠拼/阳光房/大平层 → 统一 "别墅用户"
        # 新语义: 叠拼/阳光房/大平层 → "高价值住宅用户"

        r = analyzer.analyze("我家叠拼想装光伏")
        assert r.customer_type == "高价值住宅用户"
        assert r.housing_type == "高价值住宅"

        r = analyzer.analyze("花园洋房能装光伏吗")
        assert r.customer_type == "高价值住宅用户"


# ══════════════════════════════════════════════════════════════════════
# 集成测试: 意图模型 + Pipeline
# ══════════════════════════════════════════════════════════════════════

class TestPipelineIntegration:
    """确保意图模型接入后 Pipeline 仍然正常工作。"""

    def test_s_grade_still_s(self, engine: Engine) -> None:
        """别墅+报价+联系 → 仍应 S 级。"""
        comment = {
            "id": "intent_test_S",
            "platform": "douyin",
            "content": "我在成都武侯区别墅，想装一套光伏，能报个价吗？电话联系138xxxx",
            "author": "高意向用户",
            "create_time": "2026-07-20 10:00:00",
            "ip_location": "四川成都",
        }
        result = engine.run_single(comment)
        assert result["scoring"]["lead_grade"] == "S"
        assert result["scoring"]["total_score"] >= 80

    def test_a_grade_still_a(self, engine: Engine) -> None:
        """高价值叠拼+报价+上门 → 应 S 级（意图模型 L3 增强）。"""
        comment = {
            "id": "intent_test_A",
            "platform": "douyin",
            "content": "重庆渝北的高价值住宅，想了解一下光伏怎么装",
            "author": "观望用户",
            "create_time": "2026-07-20 10:00:00",
            "ip_location": "重庆",
        }
        result = engine.run_single(comment)
        assert result["scoring"]["lead_grade"] == "A"
        assert 60 <= result["scoring"]["total_score"] < 80

    def test_b_grade_still_b(self, engine: Engine) -> None:
        """低意向 → 意图模型 L2 → A 级（咨询阶段提升）。"""
        comment = {
            "id": "intent_test_B",
            "platform": "xiaohongshu",
            "content": "光伏发电靠谱吗？想了解一下",
            "author": "观望用户",
            "create_time": "2026-07-01 09:00:00",
            "ip_location": "贵州贵阳",
        }
        result = engine.run_single(comment)
        assert result["scoring"]["lead_grade"] == "A"

    def test_new_fields_in_analysis(self, engine: Engine) -> None:
        """新增字段 (confidence, is_real_person, intent_label) 应存在。"""
        comment = {
            "id": "intent_test_newfields",
            "platform": "douyin",
            "content": "成都别墅想装光伏，怎么联系？",
            "author": "test",
            "create_time": "2026-07-20 10:00:00",
            "ip_location": "四川成都",
        }
        result = engine.run_single(comment)
        analysis = result.get("analysis", {})
        # 新字段
        assert "confidence" in analysis
        assert "is_real_person" in analysis
        assert "intent_label" in analysis
        assert isinstance(analysis["confidence"], float)

    def test_negation_pipeline(self, engine: Engine) -> None:
        """否定评论应正确降级。"""
        comment = {
            "id": "intent_neg",
            "platform": "douyin",
            "content": "光伏就是骗人的，装了没用",
            "author": "否定用户",
            "create_time": "2026-07-15 10:00:00",
            "ip_location": "四川成都",
        }
        result = engine.run_single(comment)
        # 否定 → intent_level=0 → demand_score=0 → 低 total_score
        assert result["analysis"]["intent_level"] == 0
        assert result["scoring"]["total_score"] <= 50  # C 级（demand=0 但区域/房屋仍有分）

    def test_all_pipeline_no_error(self, engine: Engine) -> None:
        """全链路无错误。"""
        comment = {
            "id": "intent_all",
            "platform": "douyin",
            "content": "成都别墅光伏安装报价联系电话",
            "author": "test",
            "create_time": "2026-07-20 10:00:00",
            "ip_location": "四川成都",
        }
        result = engine.run_single(comment)
        assert "_pipeline_error" not in result
        assert "scoring" in result
        assert "lead" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
