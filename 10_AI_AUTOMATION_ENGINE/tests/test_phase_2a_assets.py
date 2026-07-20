"""Phase 2A 数据资产模型测试 (V3.0)。

覆盖: CommentRecord扩展 / VideoAsset + VideoAssetStore /
       CompetitorCandidate扩展 / CollectionTask扩展 / 时间窗口。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_phase_2a_assets.py -v
"""

from __future__ import annotations

import csv
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
TASKS_DIR = PROJECT_ROOT / "02_DATA" / "01_COLLECTION" / "tasks"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(TASKS_DIR))

# ══════════════════════════════════════════════════════════════════════
# Imports
# ══════════════════════════════════════════════════════════════════════

from collector_base import CommentRecord, BaseCollector  # noqa: E402
from video_asset import VideoAsset, VideoAssetStore, VIDEO_CSV_FIELDS  # noqa: E402
from competitor_discovery import (  # noqa: E402
    CompetitorCandidate, ScoreDetail, CompetitorDiscovery, MOCK_CANDIDATES,
)
from public_search_base import VideoCandidate  # noqa: E402
from task_manager import (  # noqa: E402
    TaskManager, CollectionTask, CommentLimit, VideoFilter,
)

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_csv() -> Path:
    """临时 CSV 用于 VideoAssetStore 测试。"""
    d = Path(tempfile.mkdtemp())
    p = d / "test_video_asset.csv"
    yield p
    p.unlink(missing_ok=True)


@pytest.fixture
def tm() -> TaskManager:
    """使用临时目录的 TaskManager。"""
    import tempfile as _tmp
    d = Path(_tmp.mkdtemp())
    return TaskManager(tasks_dir=d)


# ══════════════════════════════════════════════════════════════════════
# CommentRecord 扩展
# ══════════════════════════════════════════════════════════════════════

class TestCommentRecordV3:

    def test_new_fields_exist(self) -> None:
        cr = CommentRecord()
        assert hasattr(cr, "user_id")
        assert hasattr(cr, "user_profile_url")
        assert hasattr(cr, "video_author_id")
        assert hasattr(cr, "video_author_name")
        assert hasattr(cr, "comment_like_count")
        assert hasattr(cr, "reply_count")
        assert hasattr(cr, "is_own_account")

    def test_new_fields_defaults(self) -> None:
        cr = CommentRecord()
        assert cr.user_id == ""
        assert cr.user_profile_url == ""
        assert cr.comment_like_count == 0
        assert cr.reply_count == 0
        assert cr.is_own_account is False

    def test_to_dict_includes_new_fields(self) -> None:
        cr = CommentRecord(
            comment_id="c001",
            user_id="u123",
            user_profile_url="https://douyin.com/user/u123",
            comment_like_count=5,
            reply_count=3,
            is_own_account=True,
        )
        d = cr.to_dict()
        assert d["user_id"] == "u123"
        assert d["user_profile_url"] == "https://douyin.com/user/u123"
        assert d["comment_like_count"] == 5
        assert d["reply_count"] == 3
        assert d["is_own_account"] is True

    def test_from_dict_new_fields(self) -> None:
        data = {
            "comment_id": "c002",
            "user_id": "u456",
            "user_profile_url": "https://douyin.com/user/u456",
            "video_author_id": "va001",
            "comment_like_count": 10,
            "is_own_account": True,
        }
        cr = CommentRecord.from_dict(data)
        assert cr.user_id == "u456"
        assert cr.user_profile_url == "https://douyin.com/user/u456"
        assert cr.video_author_id == "va001"
        assert cr.comment_like_count == 10
        assert cr.is_own_account is True

    def test_pipeline_event_includes_new_fields(self) -> None:
        cr = CommentRecord(
            comment_id="c003",
            user_id="u789",
            user_profile_url="https://douyin.com/user/u789",
            is_own_account=True,
        )
        ev = cr.to_pipeline_event()
        assert ev["user_id"] == "u789"
        assert ev["user_profile_url"] == "https://douyin.com/user/u789"
        assert ev["is_own_account"] is True

    def test_old_fields_still_work(self) -> None:
        """回归: 旧字段不受影响。"""
        cr = CommentRecord(
            comment_id="c004",
            platform="douyin",
            content="测试评论",
            author="用户A",
            source_account_id="acc001",
            ip_location="四川成都",
        )
        assert cr.platform == "douyin"
        assert cr.content == "测试评论"
        assert cr.author == "用户A"


# ══════════════════════════════════════════════════════════════════════
# VideoAsset + VideoAssetStore
# ══════════════════════════════════════════════════════════════════════

class TestVideoAsset:

    def test_create_minimal(self) -> None:
        va = VideoAsset(video_id="v001", platform="douyin")
        assert va.video_id == "v001"
        assert va.author_id == ""

    def test_all_fields(self) -> None:
        va = VideoAsset(
            video_id="dy_v001",
            video_url="https://douyin.com/video/dy_v001",
            platform="douyin",
            author_id="reg_install_001",
            author_name="成都光伏老王",
            author_url="https://douyin.com/user/reg_install_001",
            title="别墅光伏安装实拍",
            publish_time="2026-07-18",
            like_count=1520,
            comment_count=85,
            collect_count=320,
            share_count=45,
            housing_signal="别墅",
            relevance_score=9,
        )
        assert va.author_name == "成都光伏老王"
        assert va.housing_signal == "别墅"
        assert va.relevance_score == 9

    def test_ai_analysis_fields(self) -> None:
        va = VideoAsset(
            video_id="v002",
            hook_3_seconds="电费从3000降到300",
            pain_point="城市别墅业主电费高",
            video_structure="痛点→方案→数据→见证→CTA",
        )
        assert va.hook_3_seconds == "电费从3000降到300"
        assert va.pain_point == "城市别墅业主电费高"

    def test_to_dict(self) -> None:
        va = VideoAsset(video_id="v003", title="测试", housing_signal="别墅")
        d = va.to_dict()
        assert d["video_id"] == "v003"
        assert d["housing_signal"] == "别墅"

    def test_from_video_candidate(self) -> None:
        vc = VideoCandidate(
            platform="douyin", video_id="dy_v010",
            title="别墅光伏改造", housing_signal="别墅",
            publish_time="2026-07-19", comment_count=45, relevance_score=8,
        )
        va = VideoAsset.from_video_candidate(vc)
        assert va.video_id == "dy_v010"
        assert va.housing_signal == "别墅"
        assert va.comment_count == 45
        assert va.platform == "douyin"
        assert va.collected_at != ""


class TestVideoAssetStore:

    def test_save_and_get(self, tmp_csv: Path) -> None:
        store = VideoAssetStore(csv_path=tmp_csv)
        va = VideoAsset(video_id="v001", platform="douyin", title="测试视频")
        store.save(va)

        loaded = store.get("v001")
        assert loaded is not None
        assert loaded.title == "测试视频"

    def test_save_batch(self, tmp_csv: Path) -> None:
        store = VideoAssetStore(csv_path=tmp_csv)
        assets = [
            VideoAsset(video_id="v001", platform="douyin"),
            VideoAsset(video_id="v002", platform="douyin"),
            VideoAsset(video_id="v003", platform="xiaohongshu"),
        ]
        count = store.save_batch(assets)
        assert count == 3
        assert store.count() == 3

    def test_dedup_by_video_id(self, tmp_csv: Path) -> None:
        store = VideoAssetStore(csv_path=tmp_csv)
        store.save(VideoAsset(video_id="v001", title="旧标题"))
        store.save(VideoAsset(video_id="v001", title="新标题"))

        loaded = store.get("v001")
        assert loaded is not None
        assert loaded.title == "新标题"
        assert store.count() == 1

    def test_list_all(self, tmp_csv: Path) -> None:
        store = VideoAssetStore(csv_path=tmp_csv)
        store.save(VideoAsset(video_id="v001", platform="douyin"))
        store.save(VideoAsset(video_id="v002", platform="douyin"))

        all_v = store.list_all()
        assert len(all_v) == 2

    def test_list_by_platform(self, tmp_csv: Path) -> None:
        store = VideoAssetStore(csv_path=tmp_csv)
        store.save(VideoAsset(video_id="v001", platform="douyin"))
        store.save(VideoAsset(video_id="v002", platform="xiaohongshu"))

        douyin = store.list_by_platform("douyin")
        assert len(douyin) == 1
        assert douyin[0].platform == "douyin"

    def test_list_by_author(self, tmp_csv: Path) -> None:
        store = VideoAssetStore(csv_path=tmp_csv)
        store.save(VideoAsset(video_id="v001", author_id="a001", author_name="老王"))
        store.save(VideoAsset(video_id="v002", author_id="a002", author_name="老张"))
        store.save(VideoAsset(video_id="v003", author_id="a001", author_name="老王"))

        by_author = store.list_by_author("a001")
        assert len(by_author) == 2

    def test_get_nonexistent(self, tmp_csv: Path) -> None:
        store = VideoAssetStore(csv_path=tmp_csv)
        assert store.get("no_such_id") is None

    def test_count_empty(self, tmp_csv: Path) -> None:
        store = VideoAssetStore(csv_path=tmp_csv)
        assert store.count() == 0

    def test_csv_header(self, tmp_csv: Path) -> None:
        store = VideoAssetStore(csv_path=tmp_csv)
        store.save(VideoAsset(video_id="v001"))
        # Verify CSV has all expected fields
        with open(tmp_csv, 'r') as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames
            for field in VIDEO_CSV_FIELDS:
                assert field in header, f"Missing field: {field}"


# ══════════════════════════════════════════════════════════════════════
# CompetitorCandidate 扩展
# ══════════════════════════════════════════════════════════════════════

class TestCompetitorCandidateV3:

    def test_account_purpose_field(self) -> None:
        cc = CompetitorCandidate()
        assert hasattr(cc, "account_purpose")
        assert cc.account_purpose == ""

    def test_learning_priority_field(self) -> None:
        cc = CompetitorCandidate()
        assert hasattr(cc, "learning_priority")
        assert cc.learning_priority == 0

    def test_set_customer_source(self) -> None:
        cc = CompetitorCandidate(
            account_id="reg_install_001",
            account_purpose="customer_source",
            learning_priority=0,
        )
        assert cc.account_purpose == "customer_source"
        assert cc.learning_priority == 0

    def test_set_content_learning(self) -> None:
        cc = CompetitorCandidate(
            account_id="city_case_001",
            account_purpose="content_learning",
            learning_priority=8,
        )
        assert cc.account_purpose == "content_learning"
        assert cc.learning_priority == 8

    def test_set_both(self) -> None:
        cc = CompetitorCandidate(
            account_id="nat_brand_001",
            account_purpose="both",
            learning_priority=5,
        )
        assert cc.account_purpose == "both"
        assert cc.learning_priority == 5

    def test_competitor_master_has_new_fields(self) -> None:
        """competitor_master.csv 包含 account_purpose + learning_priority。"""
        import csv
        csv_path = PROJECT_ROOT / "02_DATA" / "02_COMPETITOR_DATABASE" / "competitor_master.csv"
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        for row in rows:
            assert "account_purpose" in row, f"Missing account_purpose in {row.get('account_id')}"
            assert "learning_priority" in row, f"Missing learning_priority in {row.get('account_id')}"
            assert row["account_purpose"] in ("customer_source", "content_learning", "both", ""), \
                f"Invalid account_purpose: {row['account_purpose']}"

    def test_discovery_engine_still_works(self) -> None:
        """回归: CompetitorDiscovery 正常。"""
        engine = CompetitorDiscovery(mode="mock")
        assert engine.mode == "mock"
        assert len(MOCK_CANDIDATES) >= 9


# ══════════════════════════════════════════════════════════════════════
# CollectionTask 扩展
# ══════════════════════════════════════════════════════════════════════

class TestCollectionTaskV3:

    def test_task_type_field(self) -> None:
        task = CollectionTask()
        assert hasattr(task, "task_type")
        assert task.task_type == "collection"

    def test_is_first_collection_field(self) -> None:
        task = CollectionTask()
        assert hasattr(task, "is_first_collection")
        assert task.is_first_collection is True

    def test_task_type_values(self) -> None:
        task = CollectionTask(task_type="discovery")
        assert task.task_type == "discovery"

        task2 = CollectionTask(task_type="monitor")
        assert task2.task_type == "monitor"

        task3 = CollectionTask(task_type="collection")
        assert task3.task_type == "collection"

    def test_time_window_days_is_7(self, tm: TaskManager) -> None:
        """P0 首次采集: time_window_days=7。"""
        task = tm.create(
            platform="douyin",
            account_id="test_acc",
            account_name="测试账号",
            priority="P0",
        )
        assert task.comment_limit.time_window_days == 7

    def test_first_collection_flag(self, tm: TaskManager) -> None:
        task = tm.create(
            platform="douyin",
            account_id="test_acc",
            account_name="测试账号",
        )
        assert task.is_first_collection is True

    def test_seed_time_range_days(self, tm: TaskManager) -> None:
        """seed_from_accounts: P0=7天。"""
        accounts = [{
            "platform": "douyin",
            "account_id": "acc_seed_1",
            "account_name": "测试",
            "grade": "S",
        }]
        tasks = tm.seed_from_accounts(accounts)
        assert len(tasks) >= 1
        assert tasks[0].video_filter.time_range_days == 7

    def test_to_dict_includes_new_fields(self) -> None:
        task = CollectionTask(
            task_id="T001",
            task_type="collection",
            is_first_collection=True,
        )
        d = task.to_dict()
        assert d["task_type"] == "collection"
        assert d["is_first_collection"] is True

    def test_old_fields_still_work(self, tm: TaskManager) -> None:
        """回归: 旧字段正常。"""
        task = tm.create(
            platform="douyin",
            account_id="acc_old",
            account_name="老账号",
            priority="P1",
        )
        assert task.platform == "douyin"
        assert task.status == "pending"
        assert task.max_retries == 3


# ══════════════════════════════════════════════════════════════════════
# 回归测试
# ══════════════════════════════════════════════════════════════════════

class TestRegression:

    def test_base_collector_still_works(self) -> None:
        """BaseCollector 子类仍可正常实例化。"""
        from douyin_connector import DouyinConnector
        c = DouyinConnector(credentials={})
        assert c.platform_name == "douyin"

    def test_collector_validate_still_works(self) -> None:
        """validate 仍正常工作。"""
        from douyin_connector import DouyinConnector
        c = DouyinConnector(credentials={})
        assert c.validate(CommentRecord(content="有效评论")) is True
        assert c.validate(CommentRecord(content="")) is False

    def test_comment_record_serialization_roundtrip(self) -> None:
        cr = CommentRecord(
            comment_id="c_r1",
            platform="douyin",
            content="测试",
            author="用户",
            user_id="u_rt",
            user_profile_url="https://douyin.com/user/u_rt",
            is_own_account=False,
        )
        d = cr.to_dict()
        cr2 = CommentRecord.from_dict(d)
        assert cr2.user_id == "u_rt"
        assert cr2.is_own_account is False

    def test_task_full_lifecycle(self, tm: TaskManager) -> None:
        """任务完整生命周期: create → start → complete。"""
        task = tm.create(
            platform="douyin",
            account_id="lifecycle_test",
            account_name="生命周期测试",
            priority="P0",
        )
        assert task.status == "pending"
        assert task.comment_limit.time_window_days == 7

        tm.start(task.task_id)
        loaded = tm.get(task.task_id)
        assert loaded is not None
        assert loaded.status == "running"

        tm.complete(task.task_id, last_cursor="c_999", collected_count=15)
        loaded2 = tm.get(task.task_id)
        assert loaded2 is not None
        assert loaded2.status == "completed"
        assert loaded2.last_cursor == "c_999"
