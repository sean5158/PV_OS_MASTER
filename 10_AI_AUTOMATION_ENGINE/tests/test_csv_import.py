"""CSV Import Collector 测试 (P2-2)。

覆盖: CSV读取 → 字段映射 → 数据清洗 → Pipeline端到端。

Run::

    cd PV_OS_MASTER
    .venv/bin/python -m pytest 10_AI_AUTOMATION_ENGINE/tests/test_csv_import.py -v
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "08_SYSTEM" / "scripts"
ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ENGINE_ROOT))

from collector_base import CommentRecord  # noqa: E402
from csv_import_collector import (  # noqa: E402
    CsvImportCollector,
    CSV_REQUIRED_FIELDS,
    CSV_OPTIONAL_FIELDS,
    import_comments_from_csv,
)
from platform_adapter import PlatformAdapterManager, CollectorMode  # noqa: E402
from engine import Engine  # noqa: E402

TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_csv_path() -> Path:
    """创建包含 4 条不同场景评论的示例 CSV。"""
    rows = [
        {
            "id": "test_001", "platform": "douyin", "comment_id": "dy_test_001",
            "content": "我在成都高新区，叠拼别墅想装光伏，能报个价吗？",
            "author": "成都王先生", "create_time": "2026-07-20 10:00:00",
            "source_url": "https://douyin.com/v/001", "ip_location": "四川成都",
            "video_title": "叠拼别墅光伏安装实拍", "keyword": "别墅光伏",
        },
        {
            "id": "test_002", "platform": "douyin", "comment_id": "dy_test_002",
            "content": "重庆渝北独栋别墅，夏天电费太高了，装光伏一年能省多少？",
            "author": "重庆老张", "create_time": "2026-07-19 15:00:00",
            "source_url": "https://douyin.com/v/002", "ip_location": "重庆",
            "video_title": "别墅光伏夏天省电实测", "keyword": "别墅光伏,省钱",
        },
        {
            "id": "test_003", "platform": "xiaohongshu", "comment_id": "xhs_real_001",
            "content": "成都这边有靠谱的光伏安装推荐吗？家里阳光房想改造成光伏顶",
            "author": "成都小美", "create_time": "2026-07-20 09:00:00",
            "source_url": "https://xhs.com/explore/001", "ip_location": "四川成都",
            "video_title": "阳光房光伏改造前后对比", "keyword": "阳光房,光伏改造",
        },
        {
            "id": "test_004", "platform": "douyin", "comment_id": "dy_test_004",
            "content": "光伏发电靠谱吗？想了解一下",
            "author": "观望用户", "create_time": "2026-07-15 10:00:00",
            "source_url": "https://douyin.com/v/004", "ip_location": "贵州贵阳",
            "video_title": "光伏科普", "keyword": "光伏科普",
        },
    ]

    fieldnames = ["id", "platform", "comment_id", "content", "author",
                  "create_time", "source_url", "ip_location", "video_title", "keyword"]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig",
                                     delete=False, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return Path(f.name)


@pytest.fixture
def collector() -> CsvImportCollector:
    return CsvImportCollector()


@pytest.fixture
def adapter() -> PlatformAdapterManager:
    return PlatformAdapterManager(
        config={"platforms": {}},
        credentials={},
    )


@pytest.fixture
def engine() -> Engine:
    wf = PROJECT_ROOT / "10_AI_AUTOMATION_ENGINE" / "workflows" / "comment_to_lead_pipeline.yml"
    return Engine(wf)


# ══════════════════════════════════════════════════════════════════════
# CSV 读取测试
# ══════════════════════════════════════════════════════════════════════

class TestCsvReading:

    def test_collect_returns_all_records(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(
            account_id="test_acc",
            csv_path=str(sample_csv_path),
        )
        assert len(records) == 4

    def test_collect_respects_max_count(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(
            account_id="test_acc",
            max_count=2,
            csv_path=str(sample_csv_path),
        )
        assert len(records) == 2

    def test_collect_empty_csv_path(self, collector: CsvImportCollector) -> None:
        records = collector.collect(account_id="test")
        assert records == []

    def test_collect_file_not_found(self, collector: CsvImportCollector) -> None:
        records = collector.collect(
            account_id="test",
            csv_path="/nonexistent/path.csv",
        )
        assert records == []

    def test_all_records_are_comment_records(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(
            account_id="test_acc",
            csv_path=str(sample_csv_path),
        )
        assert all(isinstance(r, CommentRecord) for r in records)


# ══════════════════════════════════════════════════════════════════════
# 字段映射测试
# ══════════════════════════════════════════════════════════════════════

class TestFieldMapping:

    def test_comment_id_mapping(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        ids = {r.comment_id for r in records}
        assert "dy_test_001" in ids
        assert "xhs_real_001" in ids

    def test_platform_mapping(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        platforms = {r.platform for r in records}
        assert "douyin" in platforms
        assert "xiaohongshu" in platforms

    def test_content_mapping(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        villa_content = [r for r in records if "别墅" in r.content]
        assert len(villa_content) >= 2

    def test_author_mapping(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        authors = {r.author for r in records}
        assert "成都王先生" in authors
        assert "观望用户" in authors

    def test_create_time_mapping(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        times = [r.create_time for r in records]
        assert "2026-07-20 10:00:00" in times
        assert "2026-07-15 10:00:00" in times

    def test_ip_location_mapping(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        locations = {r.ip_location for r in records}
        assert "四川成都" in locations
        assert "重庆" in locations

    def test_video_title_mapping(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        titles = {r.source_video_title for r in records}
        assert "叠拼别墅光伏安装实拍" in titles
        assert "阳光房光伏改造前后对比" in titles

    def test_source_url_mapping(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        urls = [r for r in records if r.source_url]
        assert len(urls) == 4

    def test_source_account_injected(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(
            account_id="PV_COMP_001",
            account_name="成都光伏专家",
            csv_path=str(sample_csv_path),
        )
        for r in records:
            assert r.source_account == "成都光伏专家"
            assert r.source_account_id == "PV_COMP_001"

    def test_collected_time_present(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        for r in records:
            assert r.collected_time != ""

    def test_comment_id_fallback_to_id(self, collector: CsvImportCollector) -> None:
        """CSV 无 comment_id 字段时，使用 id 字段。"""
        # 创建没有 comment_id 字段的 CSV
        fieldnames = ["id", "platform", "content", "author", "create_time"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig",
                                         delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "id": "no_cid_001", "platform": "douyin",
                "content": "测试评论", "author": "测试用户",
                "create_time": "2026-07-20 10:00:00",
            })
            csv_path = Path(f.name)

        records = collector.collect(account_id="test", csv_path=str(csv_path))
        assert len(records) == 1
        assert records[0].comment_id == "no_cid_001"
        csv_path.unlink()


# ══════════════════════════════════════════════════════════════════════
# 数据清洗测试
# ══════════════════════════════════════════════════════════════════════

class TestDataCleanerIntegration:

    def test_collect_and_save_creates_raw_file(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = collector.collect_and_save(
                csv_path=str(sample_csv_path),
                account_id="test_acc",
                account_name="测试账号",
                output_root=Path(tmp),
            )
            assert result is not None
            assert result.exists()
            data = json.loads(result.read_text(encoding="utf-8"))
            assert len(data) >= 1

    def test_validation_filters_empty_content(self, collector: CsvImportCollector) -> None:
        """空内容评论应被过滤。"""
        record_empty = CommentRecord(comment_id="e1", content="")
        record_valid = CommentRecord(comment_id="v1", content="有效评论")
        assert collector.validate(record_empty) is False
        assert collector.validate(record_valid) is True

    def test_deduplicate_removes_duplicates(self, collector: CsvImportCollector) -> None:
        """相同 comment_id 的去重。"""
        r1 = CommentRecord(comment_id="dup_001", content="评论A", create_time="2026-07-20 10:00:00")
        r2 = CommentRecord(comment_id="dup_001", content="评论A-更新", create_time="2026-07-20 11:00:00")
        r3 = CommentRecord(comment_id="unique_001", content="评论B", create_time="2026-07-20 10:00:00")
        result = collector.deduplicate([r1, r2, r3])
        assert len(result) == 2
        # 应保留时间更新的
        dup = [r for r in result if r.comment_id == "dup_001"][0]
        assert dup.create_time == "2026-07-20 11:00:00"

    def test_collected_time_auto_generated(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        for r in records:
            assert r.collected_time != ""
            # 格式应为 YYYY-MM-DD HH:MM:SS
            assert len(r.collected_time) == 19

    def test_processing_status_collected(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        for r in records:
            assert r.processing_status == "collected"

    def test_to_pipeline_event_format(self, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        """CSV 导入的 CommentRecord.to_pipeline_event() 格式正确。"""
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        for r in records:
            event = r.to_pipeline_event()
            assert "id" in event
            assert "platform" in event
            assert "content" in event
            assert "author" in event
            assert event["id"] == r.comment_id


# ══════════════════════════════════════════════════════════════════════
# Platform Adapter 集成测试
# ══════════════════════════════════════════════════════════════════════

class TestPlatformAdapterIntegration:

    def test_get_collector_file_mode(self, adapter: PlatformAdapterManager) -> None:
        c = adapter.get_collector("csv_import", mode="file")
        assert c is not None
        assert c.connector_mode == "file"

    def test_get_collector_auto_mode_routes_to_file(self, adapter: PlatformAdapterManager) -> None:
        c = adapter.get_collector("csv_import", mode="auto")
        assert c is not None
        assert c.connector_mode == "file"

    def test_xiaohongshu_auto_routes_to_file(self, adapter: PlatformAdapterManager) -> None:
        """小红书 auto 模式优先文件导入。"""
        c = adapter.get_collector("xiaohongshu", mode="auto")
        assert c is not None
        assert c.connector_mode == "file"

    def test_resolve_mode_csv_import(self, adapter: PlatformAdapterManager) -> None:
        assert adapter.resolve_mode("csv_import", "auto") == CollectorMode.FILE
        assert adapter.resolve_mode("csv_import", "file") == CollectorMode.FILE

    def test_list_available_modes_includes_file(self, adapter: PlatformAdapterManager) -> None:
        modes = adapter.list_available_modes("csv_import")
        assert "file" in modes
        assert "mock" in modes

    def test_file_collector_via_adapter(self, adapter: PlatformAdapterManager, sample_csv_path: Path) -> None:
        c = adapter.get_collector("csv_import", mode="file")
        records = c.collect(
            account_id="via_adapter_test",
            csv_path=str(sample_csv_path),
        )
        assert len(records) == 4
        assert all(isinstance(r, CommentRecord) for r in records)


# ══════════════════════════════════════════════════════════════════════
# Pipeline 端到端测试
# ══════════════════════════════════════════════════════════════════════

class TestPipelineEndToEnd:

    def test_villa_comment_through_pipeline(self, engine: Engine, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        """别墅评论: CSV → CommentRecord → Pipeline → S 级。"""
        records = collector.collect(
            account_id="PV_COMP_001",
            account_name="成都光伏专家",
            csv_path=str(sample_csv_path),
        )
        # 找别墅评论 (test_001)
        villa = [r for r in records if "别墅" in r.content and "报个价" in r.content]
        assert len(villa) >= 1

        event = villa[0].to_pipeline_event()
        result = engine.run_single(event)

        assert "_pipeline_error" not in result
        assert "scoring" in result
        assert result["scoring"]["lead_grade"] == "S"
        assert result["scoring"]["total_score"] >= 80

    def test_inquiry_comment_through_pipeline(self, engine: Engine, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        """咨询评论: CSV → CommentRecord → Pipeline → A/B 级。"""
        records = collector.collect(
            account_id="PV_COMP_001",
            account_name="测试账号",
            csv_path=str(sample_csv_path),
        )
        # 找"想了解"评论 (test_004)
        inquiry = [r for r in records if "想了解" in r.content]
        assert len(inquiry) == 1

        event = inquiry[0].to_pipeline_event()
        result = engine.run_single(event)

        assert "_pipeline_error" not in result
        assert "scoring" in result
        assert result["scoring"]["lead_grade"] in ("A", "B")

    def test_all_csv_comments_pipeline_no_error(self, engine: Engine, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        """CSV 全部 4 条评论通过 Pipeline 不应报错。"""
        records = collector.collect(
            account_id="test",
            csv_path=str(sample_csv_path),
        )
        assert len(records) == 4

        for r in records:
            event = r.to_pipeline_event()
            result = engine.run_single(event)
            assert "_pipeline_error" not in result, f"Pipeline error for {r.comment_id}: {result.get('_pipeline_error')}"
            assert "scoring" in result

    def test_pipeline_grades_distribution(self, engine: Engine, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        """验证 CSV 评论的分级分布。"""
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        grades: dict[str, int] = {}
        for r in records:
            event = r.to_pipeline_event()
            result = engine.run_single(event)
            grade = result["scoring"]["lead_grade"]
            grades[grade] = grades.get(grade, 0) + 1

        # 应有 S 级（别墅报价）和 A/B 级（咨询）
        assert "S" in grades
        assert grades.get("S", 0) >= 1

    def test_crm_output_after_csv_pipeline(self, engine: Engine, collector: CsvImportCollector, sample_csv_path: Path) -> None:
        """CSV 导入 → Pipeline → CRM 文件生成。"""
        records = collector.collect(account_id="test", csv_path=str(sample_csv_path))
        for r in records:
            engine.run_single(r.to_pipeline_event())

        crm_root = PROJECT_ROOT / "05_CUSTOMER_CRM"
        assert (crm_root / "leads" / "hot" / "hot_leads.csv").exists()
        assert (crm_root / "leads" / "nurture_pool.csv").exists()


# ══════════════════════════════════════════════════════════════════════
# 便捷函数测试
# ══════════════════════════════════════════════════════════════════════

class TestConvenienceFunctions:

    def test_import_comments_from_csv(self, sample_csv_path: Path) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = import_comments_from_csv(
                csv_path=str(sample_csv_path),
                account_id="test_acc",
                account_name="测试账号",
                output_dir=tmp,
            )
            assert result is not None
            assert result.exists()


# ══════════════════════════════════════════════════════════════════════
# 边界场景测试
# ══════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_empty_csv(self, collector: CsvImportCollector) -> None:
        """空 CSV（仅有表头）应返回空列表。"""
        fieldnames = ["id", "platform", "content", "author", "create_time"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig",
                                         delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            csv_path = Path(f.name)

        records = collector.collect(account_id="test", csv_path=str(csv_path))
        assert records == []
        csv_path.unlink()

    def test_csv_with_empty_content_rows(self, collector: CsvImportCollector) -> None:
        """含空内容的行应被跳过。"""
        fieldnames = ["id", "platform", "content", "author", "create_time"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig",
                                         delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "id": "empty_001", "platform": "douyin",
                "content": "", "author": "空用户",
                "create_time": "2026-07-20 10:00:00",
            })
            writer.writerow({
                "id": "valid_001", "platform": "douyin",
                "content": "有效评论内容", "author": "有效用户",
                "create_time": "2026-07-20 10:00:00",
            })
            csv_path = Path(f.name)

        records = collector.collect(account_id="test", csv_path=str(csv_path))
        assert len(records) == 1
        assert records[0].comment_id == "valid_001"
        csv_path.unlink()

    def test_utf8_bom_handled(self, collector: CsvImportCollector) -> None:
        """UTF-8 BOM 头应正确处理（encoding='utf-8-sig'）。"""
        fieldnames = ["id", "platform", "content", "author", "create_time"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig",
                                         delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "id": "bom_001", "platform": "douyin",
                "content": "BOM测试评论", "author": "BOM用户",
                "create_time": "2026-07-20 10:00:00",
            })
            csv_path = Path(f.name)

        records = collector.collect(account_id="test", csv_path=str(csv_path))
        assert len(records) == 1
        assert records[0].comment_id == "bom_001"
        csv_path.unlink()

    def test_csv_with_extra_columns(self, collector: CsvImportCollector) -> None:
        """多余列应被忽略。"""
        fieldnames = ["id", "platform", "content", "author", "create_time", "extra_field", "another_extra"]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig",
                                         delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "id": "extra_001", "platform": "douyin",
                "content": "多余列测试", "author": "用户",
                "create_time": "2026-07-20 10:00:00",
                "extra_field": "忽略", "another_extra": "也忽略",
            })
            csv_path = Path(f.name)

        records = collector.collect(account_id="test", csv_path=str(csv_path))
        assert len(records) == 1
        assert records[0].content == "多余列测试"
        csv_path.unlink()


# ══════════════════════════════════════════════════════════════════════
# 回归测试: 确保不影响 P0/P1
# ══════════════════════════════════════════════════════════════════════

class TestRegression:

    def test_platform_adapter_still_works_for_douyin(self, adapter: PlatformAdapterManager) -> None:
        c = adapter.get_collector("douyin", mode="mock")
        assert c is not None
        comments = c.collect(account_id="test", max_count=5)
        assert len(comments) >= 1

    def test_platform_adapter_still_works_for_xiaohongshu(self, adapter: PlatformAdapterManager) -> None:
        c = adapter.get_collector("xiaohongshu", mode="mock")
        assert c is not None
        comments = c.collect(account_id="test", max_count=5)
        assert len(comments) >= 1

    def test_legacy_create_collector_still_works(self) -> None:
        from collector_base import create_collector
        c = create_collector("douyin", credentials={})
        assert c is not None
        comments = c.collect(account_id="test", max_count=3)
        assert len(comments) == 3
