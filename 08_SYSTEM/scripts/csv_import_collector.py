"""PV_OS CSV 导入采集器。

从 CSV 文件导入评论数据，桥接真实导出的评论数据进入现有 Pipeline。
适用于小红书等反爬严格平台的手动导出后导入场景。

CSV 字段映射 (competitor_comments.csv):
    id              → comment_id
    platform         → platform
    content          → content
    author           → author
    create_time      → create_time
    source_url       → source_url
    ip_location      → ip_location
    video_title      → source_video_title
    keyword          → (metadata, 附加到 record)

流水线:
    CSV 文件 → CsvImportCollector → CommentRecord[] → save_batch()
    → 02_DATA/raw/ → data_cleaner → Pipeline → CRM

Usage::

    from csv_import_collector import CsvImportCollector

    collector = CsvImportCollector()
    collector.collect_and_save(
        csv_path="competitor_comments.csv",
        account_id="xhs_import_001",
        account_name="竞品账号",
    )
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from collector_base import BaseCollector, CommentRecord

logger = logging.getLogger(__name__)

TZ_SHANGHAI = timezone(timedelta(hours=8))
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# CSV 标准字段
CSV_REQUIRED_FIELDS = [
    "id", "platform", "content", "author", "create_time",
]
CSV_OPTIONAL_FIELDS = [
    "source_url", "ip_location", "video_title", "keyword", "comment_id",
]


class CsvImportCollector(BaseCollector):
    """CSV 文件导入采集器。

    从本地 CSV 文件读取评论数据，转换为 CommentRecord，
    走标准 save_batch() → raw/ → data_cleaner → Pipeline 流程。

    这是 P2 阶段桥接真实数据的关键组件：
    - 抖音/小红书导出 CSV → 本采集器 → 全链路
    - 不需要写平台 API 对接代码
    - 适合反爬严格的平台
    """

    connector_mode: str = "file"

    def __init__(self, credentials: dict[str, Any] | None = None) -> None:
        super().__init__(credentials)
        self.platform_name = "csv_import"
        self.connector_mode = "file"

    def collect(
        self,
        account_id: str = "csv_import",
        max_count: int = 1000,
        **kwargs: Any,
    ) -> list[CommentRecord]:
        """从 CSV 文件采集评论。

        Args:
            account_id: 来源账号标识 (用于标记 source_account)
            max_count: 最大导入数
            csv_path: CSV 文件路径 (通过 kwargs 传入)

        Returns:
            CommentRecord 列表
        """
        csv_path = kwargs.get("csv_path", "")
        if not csv_path:
            logger.error("CSV 导入需要指定 csv_path 参数")
            return []

        path = Path(csv_path)
        if not path.exists():
            logger.error("CSV 文件不存在: %s", csv_path)
            return []

        # 读取 CSV
        records = self._read_csv(path)
        if not records:
            return []

        # 限制数量
        if len(records) > max_count:
            records = records[:max_count]

        # 推断平台
        platform = self._infer_platform(records)
        if platform:
            self.platform_name = platform

        # 注入来源信息
        for r in records:
            r.source_account = kwargs.get("account_name", account_id)
            r.source_account_id = account_id
            if not r.platform:
                r.platform = platform

        logger.info(
            "CSV 导入: %d 条评论 (文件=%s, 平台=%s)",
            len(records), path.name, self.platform_name,
        )
        return records

    def _read_csv(self, path: Path) -> list[CommentRecord]:
        """读取 CSV 文件并转换为 CommentRecord 列表。"""
        records: list[CommentRecord] = []

        with open(path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

            if not self._validate_header(fieldnames):
                logger.warning("CSV 字段不完整: %s，尝试继续导入", fieldnames)

            for row_num, row in enumerate(reader, start=1):
                try:
                    record = self._row_to_record(row, row_num)
                    records.append(record)
                except Exception as e:
                    logger.warning("CSV 第 %d 行解析失败: %s", row_num, e)
                    continue

        return records

    def _validate_header(self, fieldnames: list[str]) -> bool:
        """验证 CSV 表头是否包含所有必需字段。"""
        missing = [f for f in CSV_REQUIRED_FIELDS if f not in fieldnames]
        if missing:
            logger.warning("CSV 缺少必需字段: %s", missing)
            return False
        return True

    def _row_to_record(self, row: dict[str, str], row_num: int) -> CommentRecord:
        """单行 CSV → CommentRecord。

        字段映射:
            CSV                → CommentRecord
            ───────────────────────────────────
            id / comment_id    → comment_id
            platform           → platform
            content            → content
            author             → author
            create_time        → create_time
            source_url         → source_url
            ip_location        → ip_location
            video_title        → source_video_title
            keyword            → (元数据)
        """
        # 标准化创建时间
        create_time = row.get("create_time", "").strip()

        # comment_id 优先用 CSV 的 comment_id 字段，其次用 id
        comment_id = row.get("comment_id", "").strip() or row.get("id", "").strip()

        # content 必需
        content = row.get("content", "").strip()
        if not content:
            raise ValueError(f"第 {row_num} 行 content 为空")

        return CommentRecord(
            comment_id=comment_id,
            platform=row.get("platform", "").strip(),
            content=content,
            author=row.get("author", "").strip(),
            source_url=row.get("source_url", "").strip(),
            create_time=create_time,
            ip_location=row.get("ip_location", "").strip(),
            source_video_title=row.get("video_title", "").strip(),
            collected_time=datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"),
            like_count=0,
            processing_status="collected",
        )

    def _infer_platform(self, records: list[CommentRecord]) -> str:
        """从记录中推断平台。"""
        platforms: dict[str, int] = {}
        for r in records:
            if r.platform:
                platforms[r.platform] = platforms.get(r.platform, 0) + 1
        if platforms:
            return max(platforms, key=platforms.get)  # type: ignore[arg-type]
        return ""

    # ── 便捷方法：一站式导入 ──

    def collect_and_save(
        self,
        account_id: str = "csv_import",
        account_name: str = "",
        max_count: int = 1000,
        output_root: Path | None = None,
        **kwargs: Any,
    ) -> Path | None:
        """导入 CSV → 校验 → 去重 → 保存到 raw/。

        覆盖基类方法以支持 csv_path kwarg。
        """
        records = self.collect(account_id, max_count=max_count, **kwargs)

        # 注入来源信息
        for r in records:
            if not r.source_account:
                r.source_account = account_name or account_id
            if not r.source_account_id:
                r.source_account_id = account_id
            r.batch_id = f"csv_{datetime.now(TZ_SHANGHAI).strftime('%Y%m%d%H%M%S')}"

        # 校验
        valid = [r for r in records if self.validate(r)]
        logger.info("CSV 导入: %d 条, 有效 %d 条", len(records), len(valid))

        if not valid:
            return None

        # 去重 + 保存
        unique = self.deduplicate(valid)
        return self.save_batch(unique, platform=self.platform_name, output_root=output_root)

    def validate(self, record: CommentRecord) -> bool:
        """CSV 导入阶段校验 — 比基类更宽松。

        CSV 导入的数据通常已是人工筛选过的，只需基础校验。
        """
        if not record.content or not record.content.strip():
            return False
        return True

    @staticmethod
    def create_sample_csv(output_path: str | Path) -> Path:
        """创建示例 CSV 文件，包含 8 条覆盖各种场景的评论。

        Args:
            output_path: 输出路径

        Returns:
            创建的 CSV 文件路径
        """
        output_path = Path(output_path)
        fieldnames = [
            "id", "platform", "comment_id", "content", "author",
            "create_time", "source_url", "ip_location", "video_title", "keyword",
        ]

        rows = [
            {
                "id": "csv_001",
                "platform": "douyin",
                "comment_id": "dy_real_001",
                "content": "我在成都高新区，家里是叠拼别墅，想装一套光伏发电系统，能报个价吗？怎么联系？",
                "author": "成都王先生",
                "create_time": "2026-07-20 10:00:00",
                "source_url": "https://www.douyin.com/video/real_001",
                "ip_location": "四川成都",
                "video_title": "成都叠拼别墅光伏安装实拍",
                "keyword": "家庭光伏,别墅光伏",
            },
            {
                "id": "csv_002",
                "platform": "douyin",
                "comment_id": "dy_real_002",
                "content": "重庆渝北的，独栋别墅，夏天电费太高了，装光伏一年能省多少？",
                "author": "重庆老张",
                "create_time": "2026-07-19 15:00:00",
                "source_url": "https://www.douyin.com/video/real_002",
                "ip_location": "重庆",
                "video_title": "别墅光伏夏天省电实测",
                "keyword": "别墅光伏,省钱",
            },
            {
                "id": "csv_003",
                "platform": "xiaohongshu",
                "comment_id": "xhs_real_001",
                "content": "成都这边有靠谱的光伏安装推荐吗？家里阳光房想改造成光伏顶",
                "author": "成都小美",
                "create_time": "2026-07-20 09:00:00",
                "source_url": "https://www.xiaohongshu.com/explore/real_001",
                "ip_location": "四川成都",
                "video_title": "阳光房光伏改造前后对比",
                "keyword": "阳光房,光伏改造",
            },
            {
                "id": "csv_004",
                "platform": "douyin",
                "comment_id": "dy_real_003",
                "content": "绵阳的，普通住宅顶楼，能不能装光伏？大概多少钱一平方？",
                "author": "绵阳小李",
                "create_time": "2026-07-18 11:00:00",
                "source_url": "https://www.douyin.com/video/real_003",
                "ip_location": "四川绵阳",
                "video_title": "普通住宅光伏安装指南",
                "keyword": "家庭光伏,价格咨询",
            },
            {
                "id": "csv_005",
                "platform": "xiaohongshu",
                "comment_id": "xhs_real_002",
                "content": "贵阳花溪区开了个民宿，想装光伏降低运营成本，求推荐安装公司",
                "author": "民宿老板赵哥",
                "create_time": "2026-07-20 08:00:00",
                "source_url": "https://www.xiaohongshu.com/explore/real_002",
                "ip_location": "贵州贵阳",
                "video_title": "民宿光伏发电省钱案例",
                "keyword": "民宿光伏,小商业",
            },
            {
                "id": "csv_006",
                "platform": "douyin",
                "comment_id": "dy_real_004",
                "content": "光伏发电靠谱吗？我朋友说用几年就不行了，是真的吗？",
                "author": "观望者老刘",
                "create_time": "2026-07-15 10:00:00",
                "source_url": "https://www.douyin.com/video/real_004",
                "ip_location": "四川德阳",
                "video_title": "光伏发电能用多少年科普",
                "keyword": "光伏科普,效果咨询",
            },
            {
                "id": "csv_007",
                "platform": "douyin",
                "comment_id": "dy_real_005",
                "content": "哈哈哈这个视频有意思",
                "author": "路人甲",
                "create_time": "2026-07-20 12:00:00",
                "source_url": "https://www.douyin.com/video/real_005",
                "ip_location": "四川成都",
                "video_title": "光伏安装搞笑日常",
                "keyword": "",
            },
            {
                "id": "csv_008",
                "platform": "kuaishou",
                "comment_id": "ks_real_001",
                "content": "我在成都开了个茶楼，三层楼，装光伏划算不？有上门看场的吗？",
                "author": "茶楼陈老板",
                "create_time": "2026-07-19 14:00:00",
                "source_url": "https://www.kuaishou.com/video/real_001",
                "ip_location": "四川成都",
                "video_title": "茶楼光伏改造省钱方案",
                "keyword": "小商业,茶楼光伏",
            },
        ]

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info("示例 CSV 创建: %s (%d 条)", output_path, len(rows))
        return output_path


# ── 便捷函数 ──

def import_comments_from_csv(
    csv_path: str,
    account_id: str = "csv_import",
    account_name: str = "",
    output_dir: str = "",
) -> Path | None:
    """一键导入 CSV 评论数据。

    Args:
        csv_path: CSV 文件路径
        account_id: 来源账号标识
        account_name: 来源账号名称
        output_dir: 输出目录 (默认: 02_DATA/raw/)

    Returns:
        保存的文件路径，无有效数据时返回 None
    """
    collector = CsvImportCollector()
    output_root = Path(output_dir) if output_dir else None
    return collector.collect_and_save(
        csv_path=csv_path,
        account_id=account_id,
        account_name=account_name,
        output_root=output_root,
    )


# ── CLI 自检 ──

if __name__ == "__main__":
    print("=" * 60)
    print("  CSV Import Collector — 自检")
    print("=" * 60)

    # 创建示例 CSV
    sample_csv = Path("/tmp/pv_os_test_comments.csv")
    CsvImportCollector.create_sample_csv(sample_csv)
    print(f"\n  ✓ 示例 CSV 创建: {sample_csv}")
    print(f"    大小: {sample_csv.stat().st_size} bytes")

    # 读取验证
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        collector = CsvImportCollector()
        output_root = Path(tmp)

        result = collector.collect_and_save(
            csv_path=str(sample_csv),
            account_id="test_account",
            account_name="测试竞品账号",
            output_root=output_root,
        )

        if result:
            data = __import__("json").loads(result.read_text(encoding="utf-8"))
            print(f"\n  ✓ 导入成功: {len(data)} 条评论 → {result}")
            platforms = set(r["platform"] for r in data)
            print(f"    平台分布: {platforms}")
            for r in data[:3]:
                print(f"    [{r['platform']}] {r['content'][:50]}...")
        else:
            print("\n  ✗ 导入失败")

    sample_csv.unlink(missing_ok=True)
    print("\n✓ CSV Import Collector 自检完成")
    print()
