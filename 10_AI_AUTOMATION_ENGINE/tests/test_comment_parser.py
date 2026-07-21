"""CommentParser 测试 (Phase 3-2.2)。

覆盖: 正常解析 / 字段缺失 / 分页 / 空数据 / 无评论 /
       Public/Mock兼容 / 用户信息提取。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_comment_parser.py -v
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
    CommentParser,
    PublicExtractionStrategy,
    DouyinPageParser,
)
from page_fetcher import MockPageFetcher  # noqa: E402


# ══════════════════════════════════════════════════════════════════════
# CommentParser 独立测试
# ══════════════════════════════════════════════════════════════════════

class TestCommentParser:
    """CommentParser 从 RENDER_DATA 提取评论字段。"""

    @pytest.fixture
    def parser(self) -> CommentParser:
        return CommentParser()

    def _make_html(self, render_data: dict) -> str:
        return f'<html><script id="RENDER_DATA" type="application/json">{json.dumps(render_data)}</script></html>'

    def test_parse_normal(self, parser: CommentParser) -> None:
        render_data = {
            "serverRouter": {
                "CommentData": {
                    "comments": [
                        {
                            "cid": "c001",
                            "text": "安装费用大概多少？",
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
        html = self._make_html(render_data)
        comments = parser.parse(html)
        assert len(comments) == 1
        c = comments[0]
        assert c["comment_id"] == "c001"
        assert c["comment_text"] == "安装费用大概多少？"
        assert "2023" in c["comment_time"]
        assert c["user_id"] == "u001"
        assert c["user_name"] == "光伏爱好者"
        assert "avatar.jpg" in c["user_profile_url"]

    def test_parse_multiple_comments(self, parser: CommentParser) -> None:
        render_data = {
            "comments": [
                {"cid": "c1", "text": "评论1", "user": {"uid": "u1", "nickname": "用户1"}},
                {"cid": "c2", "text": "评论2", "user": {"uid": "u2", "nickname": "用户2"}},
                {"cid": "c3", "text": "评论3", "user": {"uid": "u3", "nickname": "用户3"}},
            ]
        }
        html = self._make_html(render_data)
        comments = parser.parse(html)
        assert len(comments) == 3
        assert comments[0]["comment_id"] == "c1"
        assert comments[2]["comment_id"] == "c3"

    def test_parse_empty_comments(self, parser: CommentParser) -> None:
        render_data = {"serverRouter": {"CommentData": {"comments": []}}}
        html = self._make_html(render_data)
        assert parser.parse(html) == []

    def test_parse_no_comments(self, parser: CommentParser) -> None:
        html = self._make_html({"serverRouter": {"OtherPage": {}}})
        assert parser.parse(html) == []

    def test_parse_empty_render_data(self, parser: CommentParser) -> None:
        html = '<script id="RENDER_DATA" type="application/json">{}</script>'
        assert parser.parse(html) == []

    def test_parse_no_render_data(self, parser: CommentParser) -> None:
        assert parser.parse("<html>no data</html>") == []

    def test_parse_empty_html(self, parser: CommentParser) -> None:
        assert parser.parse("") == []

    def test_parse_missing_user(self, parser: CommentParser) -> None:
        """评论缺少 user 字段时应返回空 user 信息。"""
        render_data = {
            "comments": [
                {"cid": "c_anon", "text": "匿名评论"},
            ]
        }
        html = self._make_html(render_data)
        comments = parser.parse(html)
        assert len(comments) == 1
        assert comments[0]["user_id"] == ""
        assert comments[0]["user_name"] == ""
        assert comments[0]["user_profile_url"] == ""

    def test_parse_missing_avatar(self, parser: CommentParser) -> None:
        """用户缺少头像时应返回空 URL。"""
        render_data = {
            "comments": [
                {
                    "cid": "c_no_avatar",
                    "text": "无头像评论",
                    "user": {"uid": "u1", "nickname": "用户1"},
                }
            ]
        }
        html = self._make_html(render_data)
        comments = parser.parse(html)
        assert len(comments) == 1
        assert comments[0]["user_profile_url"] == ""

    def test_parse_non_list_comments(self, parser: CommentParser) -> None:
        """comments 不是列表时应返回空。"""
        render_data = {"serverRouter": {"CommentData": {"comments": "bad"}}}
        html = self._make_html(render_data)
        assert parser.parse(html) == []

    def test_parse_alt_path(self, parser: CommentParser) -> None:
        """测试备选路径: comments 直接在顶层。"""
        render_data = {
            "comments": [
                {"cid": "c_top", "text": "顶层评论", "user": {"uid": "u1", "nickname": "用户1"}},
            ]
        }
        html = self._make_html(render_data)
        comments = parser.parse(html)
        assert len(comments) == 1
        assert comments[0]["comment_id"] == "c_top"


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser Public 模式 — 评论解析
# ══════════════════════════════════════════════════════════════════════

class TestDouyinPageParserCommentPublic:
    """DouyinPageParser mode=public 评论解析。"""

    @pytest.fixture
    def parser(self) -> DouyinPageParser:
        return DouyinPageParser(mode="public")

    def _make_html(self, render_data: dict) -> str:
        return f'<html><script id="RENDER_DATA" type="application/json">{json.dumps(render_data)}</script></html>'

    def test_parse_comments_public(self, parser: DouyinPageParser) -> None:
        render_data = {
            "serverRouter": {
                "CommentData": {
                    "comments": [
                        {
                            "cid": "c001",
                            "text": "别墅光伏安装效果好吗？",
                            "create_time": 1700000000,
                            "user": {
                                "uid": "u001",
                                "nickname": "成都业主",
                                "avatar_thumb": {"url_list": ["https://img.example.com/av1.jpg"]},
                            },
                        },
                        {
                            "cid": "c002",
                            "text": "多少钱一平方？",
                            "create_time": 1700010000,
                            "user": {
                                "uid": "u002",
                                "nickname": "装修达人",
                            },
                        },
                    ]
                }
            }
        }
        html = self._make_html(render_data)
        comments = parser.parse_comments(html)
        assert len(comments) == 2
        assert comments[0]["comment_id"] == "c001"
        assert comments[0]["comment_text"] == "别墅光伏安装效果好吗？"
        assert comments[0]["user_name"] == "成都业主"
        assert comments[1]["user_name"] == "装修达人"
        # 所有字段都应存在
        for c in comments:
            assert "comment_id" in c
            assert "comment_text" in c
            assert "comment_time" in c
            assert "user_id" in c
            assert "user_name" in c
            assert "user_profile_url" in c

    def test_parse_comments_public_fallback_to_mock(self, parser: DouyinPageParser) -> None:
        """无 RENDER_DATA 降级到 Mock 策略。"""
        fetcher = MockPageFetcher()
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        comments = parser.parse_comments(html)
        assert len(comments) >= 1
        for c in comments:
            assert "comment_id" in c
            assert "comment_text" in c

    def test_parse_comments_public_empty(self, parser: DouyinPageParser) -> None:
        assert parser.parse_comments("") == []


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser Mock 模式 — 评论解析回归
# ══════════════════════════════════════════════════════════════════════

class TestDouyinPageParserCommentMock:
    """Mock 模式评论解析回归测试。"""

    @pytest.fixture
    def parser(self) -> DouyinPageParser:
        return DouyinPageParser(mode="mock")

    @pytest.fixture
    def fetcher(self) -> MockPageFetcher:
        return MockPageFetcher()

    def test_parse_comments_mock(self, parser: DouyinPageParser, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        comments = parser.parse_comments(html)
        assert len(comments) == 3
        for c in comments:
            assert "comment_id" in c
            assert c["comment_id"].startswith("mock_c")
            assert "comment_text" in c
            assert "user_name" in c
            assert "user_id" in c

    def test_parse_comments_mock_empty(self, parser: DouyinPageParser) -> None:
        assert parser.parse_comments("") == []

    def test_parse_comments_mock_no_video_cards(self, parser: DouyinPageParser) -> None:
        html = '<html><body>no video cards here</body></html>'
        assert parser.parse_comments(html) == []


# ══════════════════════════════════════════════════════════════════════
# 输出字段完整性
# ══════════════════════════════════════════════════════════════════════

class TestOutputFields:
    """验证评论输出字段完整性。"""

    REQUIRED_KEYS = [
        "comment_id",
        "comment_text",
        "comment_time",
        "user_id",
        "user_name",
        "user_profile_url",
    ]

    def test_comment_public_output_keys(self) -> None:
        """Public 模式输出应包含所有必需字段。"""
        parser = DouyinPageParser(mode="public")
        render_data = {
            "comments": [
                {
                    "cid": "c1",
                    "text": "测试评论",
                    "create_time": 1700000000,
                    "user": {"uid": "u1", "nickname": "用户1"},
                }
            ]
        }
        html = f'<html><script id="RENDER_DATA" type="application/json">{json.dumps(render_data)}</script></html>'
        comments = parser.parse_comments(html)
        assert len(comments) == 1
        for key in self.REQUIRED_KEYS:
            assert key in comments[0], f"缺少字段: {key}"

    def test_comment_mock_output_keys(self) -> None:
        """Mock 模式输出应包含所有必需字段。"""
        parser = DouyinPageParser(mode="mock")
        fetcher = MockPageFetcher()
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        comments = parser.parse_comments(html)
        assert len(comments) >= 1
        for key in self.REQUIRED_KEYS:
            assert key in comments[0], f"缺少字段: {key}"
