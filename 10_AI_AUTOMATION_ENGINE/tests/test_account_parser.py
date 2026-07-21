"""AccountParser 测试 (Phase 3-2.2)。

覆盖: 正常解析 / 字段缺失 / 非用户页 / 空数据 / Public模式 / Mock兼容。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_account_parser.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from douyin_page_parser import (  # noqa: E402
    AccountParser,
    PublicExtractionStrategy,
    DouyinPageParser,
)
from public_search_base import AccountDetail  # noqa: E402
from page_fetcher import MockPageFetcher  # noqa: E402


# ══════════════════════════════════════════════════════════════════════
# AccountParser 独立测试
# ══════════════════════════════════════════════════════════════════════

class TestAccountParser:
    """AccountParser 从 RENDER_DATA 提取账号字段。"""

    @pytest.fixture
    def parser(self) -> AccountParser:
        return AccountParser()

    def _make_html(self, render_data: dict) -> str:
        return f'<html><script id="RENDER_DATA" type="application/json">{json.dumps(render_data)}</script></html>'

    def test_parse_normal(self, parser: AccountParser) -> None:
        render_data = {
            "serverRouter": {
                "UserModule": {
                    "user_info": {
                        "uid": "12345",
                        "sec_uid": "sec_12345",
                        "nickname": "成都光伏老王",
                        "signature": "专注家庭光伏10年",
                        "follower_count": 35000,
                        "aweme_count": 156,
                        "ip_location": "四川成都",
                    }
                }
            }
        }
        html = self._make_html(render_data)
        result = parser.parse(html)
        assert result is not None
        assert result["account_id"] == "12345"
        assert result["account_name"] == "成都光伏老王"
        assert result["platform"] == "douyin"
        assert result["follower_count"] == 35000
        assert result["content_count"] == 156
        assert "sec_12345" in result["account_url"]

    def test_parse_missing_fields(self, parser: AccountParser) -> None:
        """字段缺失时应返回默认值。"""
        render_data = {
            "serverRouter": {
                "UserModule": {
                    "user_info": {
                        "uid": "min001",
                        "nickname": "最小账号",
                    }
                }
            }
        }
        html = self._make_html(render_data)
        result = parser.parse(html)
        assert result is not None
        assert result["account_id"] == "min001"
        assert result["account_name"] == "最小账号"
        assert result["follower_count"] == 0
        assert result["bio"] == ""

    def test_parse_non_account_page(self, parser: AccountParser) -> None:
        """非账号页面应返回 None。"""
        html = self._make_html({"serverRouter": {"OtherPage": {}}})
        result = parser.parse(html)
        assert result is None

    def test_parse_empty_render_data(self, parser: AccountParser) -> None:
        """空 RENDER_DATA 应返回 None。"""
        html = '<script id="RENDER_DATA" type="application/json">{}</script>'
        result = parser.parse(html)
        assert result is None

    def test_parse_no_render_data(self, parser: AccountParser) -> None:
        """无 RENDER_DATA 标签应返回 None。"""
        result = parser.parse("<html><body>no data</body></html>")
        assert result is None

    def test_parse_empty_html(self, parser: AccountParser) -> None:
        assert parser.parse("") is None

    def test_parse_with_verified(self, parser: AccountParser) -> None:
        render_data = {
            "userInfo": {
                "user": {
                    "uid": "v001",
                    "nickname": "认证账号",
                    "custom_verify": "光伏行业认证",
                }
            }
        }
        html = self._make_html(render_data)
        result = parser.parse(html)
        assert result is not None
        assert result["verified"] is True

    def test_parse_alt_path_user_page_data(self, parser: AccountParser) -> None:
        """测试备选 JSON 路径。"""
        render_data = {
            "serverRouter": {
                "UserPageData": {
                    "user": {
                        "uid": "alt001",
                        "sec_uid": "sec_alt001",
                        "nickname": "备选路径账号",
                        "signature": "测试",
                    }
                }
            }
        }
        html = self._make_html(render_data)
        result = parser.parse(html)
        assert result is not None
        assert result["account_id"] == "alt001"


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser Public 模式 — 账号解析
# ══════════════════════════════════════════════════════════════════════

class TestDouyinPageParserAccountPublic:
    """DouyinPageParser mode=public 账号解析。"""

    @pytest.fixture
    def parser(self) -> DouyinPageParser:
        return DouyinPageParser(mode="public")

    def _make_html(self, render_data: dict) -> str:
        return f'<html><script id="RENDER_DATA" type="application/json">{json.dumps(render_data)}</script></html>'

    def test_parse_account_public(self, parser: DouyinPageParser) -> None:
        render_data = {
            "serverRouter": {
                "UserModule": {
                    "user_info": {
                        "uid": "uid001",
                        "sec_uid": "sec_001",
                        "nickname": "别墅光伏改造日记",
                        "signature": "专注高端别墅光伏改造，实拍案例分享",
                        "follower_count": 50000,
                        "aweme_count": 89,
                        "ip_location": "四川成都",
                    }
                }
            }
        }
        html = self._make_html(render_data)
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert isinstance(detail, AccountDetail)
        assert detail.account_name == "别墅光伏改造日记"
        assert detail.follower_count == 50000
        assert detail.platform == "douyin"
        assert "别墅" in detail.premium_signals
        assert "成都" in detail.region_signals
        assert detail.content_count == 89

    def test_parse_account_public_no_render_data_fallback(self, parser: DouyinPageParser) -> None:
        """无 RENDER_DATA 时降级到 Mock 策略。"""
        # 使用 Mock HTML 结构
        fetcher = MockPageFetcher()
        html = fetcher.fetch_account_page("reg_install_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert detail.account_name == "成都光伏老王"

    def test_parse_account_public_empty(self, parser: DouyinPageParser) -> None:
        assert parser.parse_account_page("") is None


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser Mock 模式 — 账号解析回归
# ══════════════════════════════════════════════════════════════════════

class TestDouyinPageParserAccountMock:
    """Mock 模式账号解析回归测试。"""

    @pytest.fixture
    def parser(self) -> DouyinPageParser:
        return DouyinPageParser(mode="mock")

    @pytest.fixture
    def fetcher(self) -> MockPageFetcher:
        return MockPageFetcher()

    def test_parse_reg_install(self, parser: DouyinPageParser, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_account_page("reg_install_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert detail.account_name == "成都光伏老王"
        assert detail.follower_count == 35000
        assert detail.verified is True
        assert "别墅" in detail.premium_signals

    def test_parse_city_case(self, parser: DouyinPageParser, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_account_page("city_case_001", "douyin")
        detail = parser.parse_account_page(html)
        assert detail is not None
        assert detail.account_name == "别墅光伏改造日记"
        high_value = {"别墅", "花园洋房", "阳光房"}
        assert bool(set(detail.premium_signals) & high_value)

    def test_parse_invalid(self, parser: DouyinPageParser) -> None:
        assert parser.parse_account_page("") is None


# ══════════════════════════════════════════════════════════════════════
# 输出字段完整性
# ══════════════════════════════════════════════════════════════════════

class TestOutputFields:
    """验证账号解析输出字段完整。"""

    def test_account_detail_required_fields(self) -> None:
        """AccountDetail 必须包含 account_id/account_name/account_url/platform/follower_count。"""
        detail = AccountDetail(
            platform="douyin",
            account_id="test001",
            account_name="测试",
            account_url="https://douyin.com/user/test001",
            follower_count=1000,
        )
        d = detail.to_dict()
        assert d["account_id"] == "test001"
        assert d["account_name"] == "测试"
        assert d["account_url"] == "https://douyin.com/user/test001"
        assert d["platform"] == "douyin"
        assert d["follower_count"] == 1000
        # account_category 来自 account_type_ai
        assert "account_type_ai" in d
