#!/usr/bin/env python3
"""PV_OS 评论采集器独立运行入口。

一键执行：采集 → 清洗 → 触发 Pipeline。

Usage::

    # Mock 模式（默认）：用测试数据跑通全链路
    python run_collector.py

    # 仅采集不触发 Pipeline
    python run_collector.py --no-pipeline

    # 仅清洗已有数据
    python run_collector.py --clean-only

    # 指定平台
    python run_collector.py --platform douyin
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_loader import load_collection_config, load_platform_credentials, get_enabled_platforms  # noqa: E402
from collector_base import create_collector  # noqa: E402
from data_cleaner import clean_raw_files  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="PV_OS 评论采集器")
    parser.add_argument("--platform", type=str, help="仅采集指定平台")
    parser.add_argument("--no-pipeline", action="store_true", help="采集后不触发 Pipeline")
    parser.add_argument("--clean-only", action="store_true", help="仅执行数据清洗")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    args = parser.parse_args()

    if args.clean_only:
        logger.info("执行数据清洗...")
        platforms = [args.platform] if args.platform else None
        report = clean_raw_files(platforms=platforms, dry_run=args.dry_run)
        _print_report(report)
        return

    # 采集模式
    config = load_collection_config()
    credentials = load_platform_credentials()
    enabled = [args.platform] if args.platform else get_enabled_platforms(config)

    logger.info("PV_OS 评论采集器启动")
    logger.info(f"  平台: {enabled}")
    logger.info(f"  模式: {'Mock (测试数据)' if not credentials.get('douyin', {}).get('cookie') else 'Live'}")

    for platform in enabled:
        logger.info(f"\n── {platform} 采集 ──")
        collector = create_collector(platform, credentials.get(platform, {}))
        if collector is None:
            logger.warning("  跳过: 无连接器")
            continue

        # 采集并保存
        result = collector.collect_and_save(
            account_id=f"{platform}_test_001",
            account_name=f"测试账号-{platform}",
            max_count=10,
        )
        if result:
            logger.info(f"  保存: {result}")

    # 采集后自动清洗
    logger.info("\n── 数据清洗 ──")
    platforms = [args.platform] if args.platform else None
    report = clean_raw_files(platforms=platforms, dry_run=args.dry_run)
    _print_report(report)

    if not args.no_pipeline:
        logger.info("\n── Pipeline 触发 ──")
        logger.info("  通过 collection_scheduler.py --once 可触发完整 Pipeline")
        logger.info("  或: python 10_AI_AUTOMATION_ENGINE/run_pipeline.py --test")


def _print_report(report: dict) -> None:
    print(f"\n  采集报告:")
    print(f"    原始: {report.get('total', 0)}")
    print(f"    去重: {report.get('duplicates', 0)}")
    print(f"    噪声: {report.get('noise', 0)}")
    print(f"    无效: {report.get('invalid', 0)}")
    print(f"    清洗后: {report.get('cleaned', 0)}")


if __name__ == "__main__":
    main()
