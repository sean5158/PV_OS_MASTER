"""VideoParser 测试 (Phase 3-2.2)。

覆盖: 正常解析 / 字段缺失 / 分页 / 空数据 / 格式异常 / Public/Mock兼容。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_video_parser.py -v
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
    VideoParser,
    PublicExtractionStrategy,
    DouyinPageParser,
)
from public_search_base import VideoCandidate  # noqa: E402
from page_fetcher import MockPageFetcher  # noqa: E402


# ══════════════════════════════════════════════════════════════════════
# VideoParser 独立测试
# ══════════════════════════════════════════════════════════════════════

class TestVideoParser:
    """VideoParser 从 RENDER_DATA 提取视频字段。"""

    @pytest.fixture
    def parser(self) -> VideoParser:
        return VideoParser()

    def _make_html(self, render_data: dict) -> str:
        return f'<html><script id="RENDER_DATA" type="application/json">{json.dumps(render_data)}</script></html>'

    def test_parse_normal(self, parser: VideoParser) -> None:
        render_data = {
            "serverRouter": {
                "UserPageData": {
                    "aweme_list": [
                        {
                            "aweme_id": "v001",
                            "desc": "别墅光伏改造实拍",
                            "create_time": 1700000000,
                            "author_user_id": "author_001",
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
        html = self._make_html(render_data)
        videos = parser.parse(html)
        assert len(videos) == 1
        v = videos[0]
        assert v["video_id"] == "v001"
        assert v["video_title"] == "别墅光伏改造实拍"
        assert v["author_id"] == "author_001"
        assert v["like_count"] == 1500
        assert v["comment_count"] == 85
        assert v["collect_count"] == 320
        assert "2023" in v["publish_time"]
        assert "v001" in v["video_url"]

    def test_parse_multiple_videos(self, parser: VideoParser) -> None:
        render_data = {
            "aweme_list": [
                {"aweme_id": "v1", "desc": "视频1", "statistics": {"comment_count": 10}},
                {"aweme_id": "v2", "desc": "视频2", "statistics": {"comment_count": 20}},
                {"aweme_id": "v3", "desc": "视频3", "statistics": {"comment_count": 30}},
            ]
        }
        html = self._make_html(render_data)
        videos = parser.parse(html)
        assert len(videos) == 3
        assert videos[0]["comment_count"] == 10
        assert videos[2]["comment_count"] == 30

    def test_parse_empty_aweme_list(self, parser: VideoParser) -> None:
        render_data = {"serverRouter": {"UserPageData": {"aweme_list": []}}}
        html = self._make_html(render_data)
        assert parser.parse(html) == []

    def test_parse_no_aweme_list(self, parser: VideoParser) -> None:
        html = self._make_html({"serverRouter": {"OtherPage": {}}})
        assert parser.parse(html) == []

    def test_parse_empty_render_data(self, parser: VideoParser) -> None:
        html = '<script id="RENDER_DATA" type="application/json">{}</script>'
        assert parser.parse(html) == []

    def test_parse_no_render_data(self, parser: VideoParser) -> None:
        assert parser.parse("<html>no data</html>") == []

    def test_parse_empty_html(self, parser: VideoParser) -> None:
        assert parser.parse("") == []

    def test_parse_missing_fields(self, parser: VideoParser) -> None:
        """视频字段缺失时应使用默认值。"""
        render_data = {
            "aweme_list": [
                {"aweme_id": "v_min", "desc": ""},
            ]
        }
        html = self._make_html(render_data)
        videos = parser.parse(html)
        assert len(videos) == 1
        v = videos[0]
        assert v["video_id"] == "v_min"
        assert v["video_title"] == ""
        assert v["like_count"] == 0
        assert v["comment_count"] == 0
        assert v["collect_count"] == 0

    def test_parse_non_list_aweme(self, parser: VideoParser) -> None:
        """aweme_list 不是列表时应返回空。"""
        render_data = {"serverRouter": {"UserPageData": {"aweme_list": "bad"}}}
        html = self._make_html(render_data)
        assert parser.parse(html) == []


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser Public 模式 — 视频解析
# ══════════════════════════════════════════════════════════════════════

class TestDouyinPageParserVideoPublic:
    """DouyinPageParser mode=public 视频解析。"""

    @pytest.fixture
    def parser(self) -> DouyinPageParser:
        return DouyinPageParser(mode="public")

    def _make_html(self, render_data: dict) -> str:
        return f'<html><script id="RENDER_DATA" type="application/json">{json.dumps(render_data)}</script></html>'

    def test_parse_videos_public(self, parser: DouyinPageParser) -> None:
        render_data = {
            "serverRouter": {
                "UserPageData": {
                    "aweme_list": [
                        {
                            "aweme_id": "v001",
                            "desc": "别墅光伏改造实拍",
                            "create_time": 1700000000,
                            "author_user_id": "author_001",
                            "statistics": {
                                "digg_count": 1500,
                                "comment_count": 85,
                                "collect_count": 320,
                            },
                        },
                        {
                            "aweme_id": "v002",
                            "desc": "阳光房光伏顶设计",
                            "create_time": 1700100000,
                            "author_user_id": "author_001",
                            "statistics": {
                                "digg_count": 800,
                                "comment_count": 45,
                                "collect_count": 120,
                            },
                        },
                    ]
                }
            }
        }
        html = self._make_html(render_data)
        videos = parser.parse_video_list(html, default_topic="光伏安装")
        assert len(videos) == 2
        assert all(isinstance(v, VideoCandidate) for v in videos)
        # 检查 housing_signal 和 relevance_score 计算
        villa_video = [v for v in videos if "别墅" in v.title]
        assert len(villa_video) == 1
        assert villa_video[0].housing_signal == "别墅"
        assert villa_video[0].relevance_score == 9
        # 阳光房也是高端
        sunroom_video = [v for v in videos if "阳光房" in v.title]
        assert len(sunroom_video) == 1
        assert sunroom_video[0].relevance_score == 9

    def test_parse_videos_public_no_title_skipped(self, parser: DouyinPageParser) -> None:
        """无标题的视频应被跳过。"""
        render_data = {
            "aweme_list": [
                {"aweme_id": "v1", "desc": "", "statistics": {"comment_count": 5}},
                {"aweme_id": "v2", "desc": "有效视频", "statistics": {"comment_count": 10}},
            ]
        }
        html = self._make_html(render_data)
        videos = parser.parse_video_list(html)
        assert len(videos) == 1
        assert videos[0].title == "有效视频"

    def test_parse_videos_public_fallback_to_mock(self, parser: DouyinPageParser) -> None:
        """无 RENDER_DATA 降级到 Mock 策略。"""
        fetcher = MockPageFetcher()
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        videos = parser.parse_video_list(html, default_topic="成都光伏安装")
        assert len(videos) == 3
        assert videos[0].title == "别墅光伏安装实拍"

    def test_parse_videos_public_empty(self, parser: DouyinPageParser) -> None:
        assert parser.parse_video_list("") == []


# ══════════════════════════════════════════════════════════════════════
# DouyinPageParser Mock 模式 — 视频解析回归
# ══════════════════════════════════════════════════════════════════════

class TestDouyinPageParserVideoMock:
    """Mock 模式视频解析回归测试。"""

    @pytest.fixture
    def parser(self) -> DouyinPageParser:
        return DouyinPageParser(mode="mock")

    @pytest.fixture
    def fetcher(self) -> MockPageFetcher:
        return MockPageFetcher()

    def test_parse_videos_mock(self, parser: DouyinPageParser, fetcher: MockPageFetcher) -> None:
        html = fetcher.fetch_video_list_page("reg_install_001", "douyin")
        videos = parser.parse_video_list(html, default_topic="成都光伏安装")
        assert len(videos) == 3
        assert videos[0].platform == "douyin"
        assert videos[0].housing_signal == "别墅"

    def test_parse_videos_mock_empty(self, parser: DouyinPageParser) -> None:
        assert parser.parse_video_list("") == []


# ══════════════════════════════════════════════════════════════════════
# 输出字段完整性
# ══════════════════════════════════════════════════════════════════════

class TestOutputFields:
    """验证视频输出字段完整性。"""

    def test_video_candidate_all_fields(self) -> None:
        vc = VideoCandidate(
            platform="douyin",
            video_id="v001",
            video_url="https://douyin.com/video/v001",
            title="测试视频",
            topic="光伏",
            publish_time="2024-01-01",
            comment_count=50,
            housing_signal="别墅",
            relevance_score=9,
        )
        d = vc.to_dict()
        assert d["video_id"] == "v001"
        assert d["title"] == "测试视频"
        assert d["video_url"] == "https://douyin.com/video/v001"
        assert d["publish_time"] == "2024-01-01"
        assert d["comment_count"] == 50
        assert d["housing_signal"] == "别墅"
        assert d["relevance_score"] == 9
