"""PublicExtractionStrategy 测试 (Phase 3-2.2)。

覆盖: RENDER_DATA 提取 / JSON 解析 / 字段标准化 /
       异常HTML / 降级 / AccountParser/VideoParser/CommentParser 集成。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_public_extraction_strategy.py -v
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
    PublicExtractionStrategy,
    _extract_render_data_json,
    _safe_get,
    _normalize_count,
    _normalize_timestamp,
)


# ══════════════════════════════════════════════════════════════════════
# RENDER_DATA 提取
# ══════════════════════════════════════════════════════════════════════

class TestRenderDataExtraction:
    """RENDER_DATA 从 HTML 中提取和解析。"""

    def test_extract_valid_json(self) -> None:
        html = '<html><script id="RENDER_DATA" type="application/json">{"a":1}</script></html>'
        result = _extract_render_data_json(html)
        assert result == {"a": 1}

    def test_extract_nested_json(self) -> None:
        data = {"serverRouter": {"/search/user": {"user_list": []}}}
        html = f'<script id="RENDER_DATA" type="application/json">{json.dumps(data)}</script>'
        result = _extract_render_data_json(html)
        assert "serverRouter" in result

    def test_no_render_data_tag(self) -> None:
        result = _extract_render_data_json("<html><body>no data</body></html>")
        assert result == {}

    def test_empty_html(self) -> None:
        assert _extract_render_data_json("") == {}

    def test_empty_render_data(self) -> None:
        html = '<script id="RENDER_DATA" type="application/json"></script>'
        result = _extract_render_data_json(html)
        assert result == {}

    def test_invalid_json(self) -> None:
        html = '<script id="RENDER_DATA" type="application/json">{invalid}</script>'
        result = _extract_render_data_json(html)
        assert result == {}

    def test_truncated_json(self) -> None:
        html = '<script id="RENDER_DATA" type="application/json">{"a":</script>'
        result = _extract_render_data_json(html)
        assert result == {}


# ══════════════════════════════════════════════════════════════════════
# 字段标准化
# ══════════════════════════════════════════════════════════════════════

class TestFieldNormalization:
    """_normalize_count / _normalize_timestamp / _safe_get。"""

    def test_normalize_count_int(self) -> None:
        assert _normalize_count(12345) == 12345

    def test_normalize_count_float(self) -> None:
        assert _normalize_count(12345.0) == 12345

    def test_normalize_count_string(self) -> None:
        assert _normalize_count("35000") == 35000

    def test_normalize_count_with_wan(self) -> None:
        assert _normalize_count("3.5w") == 35000

    def test_normalize_count_empty(self) -> None:
        assert _normalize_count("") == 0

    def test_normalize_count_none(self) -> None:
        assert _normalize_count(None) == 0  # type: ignore[arg-type]

    def test_normalize_count_zero(self) -> None:
        assert _normalize_count(0) == 0

    def test_normalize_timestamp_int(self) -> None:
        result = _normalize_timestamp(1700000000)
        assert "2023" in result

    def test_normalize_timestamp_millis(self) -> None:
        # 毫秒时间戳 (> 1e12)
        result = _normalize_timestamp(1700000000000)
        assert "2023" in result

    def test_normalize_timestamp_string(self) -> None:
        assert _normalize_timestamp("2024-01-01") == "2024-01-01"

    def test_normalize_timestamp_zero(self) -> None:
        assert _normalize_timestamp(0) == ""

    def test_safe_get_nested(self) -> None:
        d = {"a": {"b": {"c": 42}}}
        assert _safe_get(d, "a", "b", "c") == 42

    def test_safe_get_missing(self) -> None:
        d = {"a": {"b": 1}}
        assert _safe_get(d, "a", "c") == ""

    def test_safe_get_default(self) -> None:
        d = {}
        assert _safe_get(d, "x", default=99) == 99

    def test_safe_get_not_dict(self) -> None:
        assert _safe_get("not_a_dict", "key") == ""  # type: ignore[arg-type]


# ══════════════════════════════════════════════════════════════════════
# PublicExtractionStrategy
# ══════════════════════════════════════════════════════════════════════

class TestPublicExtractionStrategy:
    """策略核心功能: extract_render_data / extract_account_fields /
       extract_video_fields / extract_comment_fields。"""

    @pytest.fixture
    def strategy(self) -> PublicExtractionStrategy:
        return PublicExtractionStrategy()

    def test_extract_render_data_delegates(self, strategy: PublicExtractionStrategy) -> None:
        html = '<script id="RENDER_DATA" type="application/json">{"key":"val"}</script>'
        result = strategy.extract_render_data(html)
        assert result == {"key": "val"}

    def test_extract_account_fields_basic(self, strategy: PublicExtractionStrategy) -> None:
        render_data = {
            "serverRouter": {
                "UserModule": {
                    "user_info": {
                        "uid": "12345",
                        "sec_uid": "sec_12345",
                        "nickname": "测试账号",
                        "signature": "测试简介",
                        "follower_count": 50000,
                        "aweme_count": 200,
                        "ip_location": "四川成都",
                    }
                }
            }
        }
        fields = strategy.extract_account_fields(render_data)
        assert fields["account_id"] == "12345"
        assert fields["account_name"] == "测试账号"
        assert fields["platform"] == "douyin"
        assert fields["follower_count"] == 50000
        assert fields["content_count"] == 200
        assert "sec_12345" in fields["account_url"]

    def test_extract_account_fields_alt_path(self, strategy: PublicExtractionStrategy) -> None:
        """测试备选 JSON 路径: UserPageData.user。"""
        render_data = {
            "serverRouter": {
                "UserPageData": {
                    "user": {
                        "uid": "67890",
                        "sec_uid": "sec_67890",
                        "nickname": "备选账号",
                    }
                }
            }
        }
        fields = strategy.extract_account_fields(render_data)
        assert fields["account_id"] == "67890"
        assert fields["account_name"] == "备选账号"

    def test_extract_account_fields_empty(self, strategy: PublicExtractionStrategy) -> None:
        fields = strategy.extract_account_fields({})
        assert fields["account_id"] == ""
        assert fields["account_name"] == ""

    def test_extract_account_fields_verified(self, strategy: PublicExtractionStrategy) -> None:
        render_data = {
            "userInfo": {
                "user": {
                    "uid": "v001",
                    "nickname": "认证账号",
                    "custom_verify": "光伏行业认证",
                }
            }
        }
        fields = strategy.extract_account_fields(render_data)
        assert fields["verified"] is True

    def test_extract_video_fields_basic(self, strategy: PublicExtractionStrategy) -> None:
        render_data = {
            "serverRouter": {
                "UserPageData": {
                    "aweme_list": [
                        {
                            "aweme_id": "v001",
                            "desc": "别墅光伏实拍",
                            "create_time": 1700000000,
                            "author_user_id": "12345",
                            "statistics": {
                                "digg_count": 1500,
                                "comment_count": 85,
                                "collect_count": 320,
                            },
                        }
                    ]
                }
            }
        }
        videos = strategy.extract_video_fields(render_data)
        assert len(videos) == 1
        v = videos[0]
        assert v["video_id"] == "v001"
        assert v["video_title"] == "别墅光伏实拍"
        assert v["author_id"] == "12345"
        assert v["like_count"] == 1500
        assert v["comment_count"] == 85
        assert v["collect_count"] == 320
        assert "2023" in v["publish_time"]

    def test_extract_video_fields_empty(self, strategy: PublicExtractionStrategy) -> None:
        assert strategy.extract_video_fields({}) == []

    def test_extract_video_fields_no_list(self, strategy: PublicExtractionStrategy) -> None:
        render_data = {"serverRouter": {"UserPageData": {}}}
        assert strategy.extract_video_fields(render_data) == []

    def test_extract_video_fields_alt_path(self, strategy: PublicExtractionStrategy) -> None:
        """测试备选路径: aweme_list 直接在顶层。"""
        render_data = {
            "aweme_list": [
                {
                    "aweme_id": "v002",
                    "desc": "阳光房案例",
                    "statistics": {"comment_count": 10},
                }
            ]
        }
        videos = strategy.extract_video_fields(render_data)
        assert len(videos) == 1
        assert videos[0]["video_id"] == "v002"

    def test_extract_comment_fields_basic(self, strategy: PublicExtractionStrategy) -> None:
        render_data = {
            "serverRouter": {
                "CommentData": {
                    "comments": [
                        {
                            "cid": "c001",
                            "text": "安装费用多少？",
                            "create_time": 1700000000,
                            "user": {
                                "uid": "u001",
                                "nickname": "光伏爱好者",
                                "avatar_thumb": {
                                    "url_list": ["https://example.com/avatar.jpg"]
                                },
                            },
                        }
                    ]
                }
            }
        }
        comments = strategy.extract_comment_fields(render_data)
        assert len(comments) == 1
        c = comments[0]
        assert c["comment_id"] == "c001"
        assert c["comment_text"] == "安装费用多少？"
        assert c["user_id"] == "u001"
        assert c["user_name"] == "光伏爱好者"
        assert "avatar.jpg" in c["user_profile_url"]
        assert "2023" in c["comment_time"]

    def test_extract_comment_fields_multiple(self, strategy: PublicExtractionStrategy) -> None:
        render_data = {
            "comments": [
                {"cid": "c1", "text": "评论1", "user": {"uid": "u1", "nickname": "用户1"}},
                {"cid": "c2", "text": "评论2", "user": {"uid": "u2", "nickname": "用户2"}},
            ]
        }
        comments = strategy.extract_comment_fields(render_data)
        assert len(comments) == 2

    def test_extract_comment_fields_empty(self, strategy: PublicExtractionStrategy) -> None:
        assert strategy.extract_comment_fields({}) == []

    def test_extract_comment_fields_no_user(self, strategy: PublicExtractionStrategy) -> None:
        """测试评论中缺少 user 字段。"""
        render_data = {
            "comments": [
                {"cid": "c1", "text": "匿名评论"},
            ]
        }
        comments = strategy.extract_comment_fields(render_data)
        assert len(comments) == 1
        assert comments[0]["user_id"] == ""
        assert comments[0]["user_name"] == ""


# ══════════════════════════════════════════════════════════════════════
# 降级测试
# ══════════════════════════════════════════════════════════════════════

class TestFallback:
    """Public 失败时的降级行为。"""

    def test_strategy_handles_none_html(self) -> None:
        strategy = PublicExtractionStrategy()
        result = strategy.extract_render_data("")
        assert result == {}

    def test_fields_handle_malformed_data(self) -> None:
        strategy = PublicExtractionStrategy()
        # 传入非预期结构不应崩溃
        fields = strategy.extract_account_fields({"bad": "data"})
        assert fields["account_id"] == ""
        assert fields["platform"] == "douyin"  # platform 应始终存在

    def test_video_fields_handle_non_list(self) -> None:
        strategy = PublicExtractionStrategy()
        videos = strategy.extract_video_fields({"serverRouter": {"UserPageData": {"aweme_list": "not_a_list"}}})
        assert videos == []

    def test_comment_fields_handle_non_list(self) -> None:
        strategy = PublicExtractionStrategy()
        comments = strategy.extract_comment_fields({"serverRouter": {"CommentData": {"comments": "bad"}}})
        assert comments == []


# ══════════════════════════════════════════════════════════════════════
# 三模式兼容
# ══════════════════════════════════════════════════════════════════════

class TestThreeModeCompatibility:
    """Mock/Public/Official 三模式输出格式一致。"""

    def test_output_field_keys_consistent(self) -> None:
        """所有提取函数的输出都使用相同 key 命名。"""
        strategy = PublicExtractionStrategy()

        account_fields = strategy.extract_account_fields({
            "user": {"uid": "1", "nickname": "test"}
        })
        assert "account_id" in account_fields
        assert "account_name" in account_fields
        assert "account_url" in account_fields
        assert "platform" in account_fields
        assert "follower_count" in account_fields
        assert "account_category" in account_fields

        video_fields = strategy.extract_video_fields({
            "aweme_list": [{"aweme_id": "v1", "desc": "test"}]
        })
        if video_fields:
            assert "video_id" in video_fields[0]
            assert "video_title" in video_fields[0]
            assert "video_url" in video_fields[0]
            assert "author_id" in video_fields[0]
            assert "publish_time" in video_fields[0]
            assert "like_count" in video_fields[0]
            assert "comment_count" in video_fields[0]
            assert "collect_count" in video_fields[0]

        comment_fields = strategy.extract_comment_fields({
            "comments": [{"cid": "c1", "text": "test", "user": {"uid": "u1", "nickname": "user"}}]
        })
        if comment_fields:
            assert "comment_id" in comment_fields[0]
            assert "comment_text" in comment_fields[0]
            assert "comment_time" in comment_fields[0]
            assert "user_id" in comment_fields[0]
            assert "user_name" in comment_fields[0]
            assert "user_profile_url" in comment_fields[0]
