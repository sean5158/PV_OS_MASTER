"""PV_OS 数据清洗管道。

连接采集输出的 raw JSON → 清洗 → 输出到 02_DATA/04_COMMENT_DATABASE/

清洗步骤：
1. 去重（跨批次）
2. 格式标准化
3. 去噪（广告、垃圾内容识别）
4. 字段完整性校验
5. 按平台/日期归档

Usage::

    python data_cleaner.py                          # 清洗所有 raw/ 文件
    python data_cleaner.py --platform douyin        # 仅清洗抖音
    python data_cleaner.py --dry-run                # 预览模式
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "02_DATA" / "raw"
CLEAN_DIR = PROJECT_ROOT / "02_DATA" / "04_COMMENT_DATABASE" / "cleaned"
ARCHIVE_CSV = PROJECT_ROOT / "02_DATA" / "04_COMMENT_DATABASE" / "comment_archive.csv"
TZ_SHANGHAI = timezone(timedelta(hours=8))


# ── 步骤 1：去重 ──
def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按 comment_id 全局去重，保留最新版本。"""
    seen: dict[str, dict[str, Any]] = {}
    for r in records:
        cid = r.get("comment_id", r.get("id", ""))
        if not cid:
            continue
        if cid in seen:
            existing_ct = seen[cid].get("create_time", "")
            new_ct = r.get("create_time", "")
            if new_ct > existing_ct:
                seen[cid] = r
        else:
            seen[cid] = r
    return list(seen.values())


# ── 步骤 2：格式标准化 ──
def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """将不同来源的字段名统一到标准 schema。"""
    return {
        "comment_id": record.get("comment_id", record.get("id", "")),
        "platform": record.get("platform", ""),
        "content": record.get("content", record.get("comment_text", "")).strip(),
        "author": record.get("author", record.get("nickname", "")),
        "source_account": record.get("source_account", ""),
        "source_account_id": record.get("source_account_id", ""),
        "source_video_id": record.get("source_video_id", ""),
        "source_video_title": record.get("source_video_title", record.get("video_title", "")),
        "source_url": record.get("source_url", ""),
        "create_time": record.get("create_time", record.get("comment_time", "")),
        "collected_time": record.get("collected_time", datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")),
        "ip_location": record.get("ip_location", ""),
        "like_count": record.get("like_count", 0),
        "batch_id": record.get("batch_id", ""),
        "processing_status": "cleaned",
    }


# ── 步骤 3：去噪 ──
SPAM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"加[微威vV][信xX]|\+[vV]|[Vv]\s*[:：]\s*\w{6,}", re.IGNORECASE),  # 引流微信
    re.compile(r"兼职|日结|招聘|Q[QqQ]群|扣扣群"),                                   # 兼职广告
    re.compile(r"^[👍🙏🌹💪❤️🔥👏🎉]+$"),                                              # 纯表情
    re.compile(r"^(哈){3,}$|^(笑){3,}$"),                                             # 无意义重复
]
NOISE_MIN_LENGTH = 2  # 最低有效字符数


def is_noise(content: str) -> bool:
    """判断评论是否为噪声（广告、纯表情、无意义内容）。"""
    text = content.strip()

    # 太短
    if len(text) < NOISE_MIN_LENGTH:
        return True

    # 纯标点/空白
    if not re.search(r"[\u4e00-\u9fff\w]", text):
        return True

    # 垃圾模式
    for pat in SPAM_PATTERNS:
        if pat.search(text):
            return True

    return False


# ── 步骤 4：字段完整性校验 ──
REQUIRED_FIELDS = ["comment_id", "platform", "content"]


def validate_record(record: dict[str, Any]) -> tuple[bool, str]:
    """校验记录完整性。返回 (是否通过, 原因)。"""
    for field in REQUIRED_FIELDS:
        if not record.get(field):
            return False, f"缺失必填字段: {field}"

    if not record["content"].strip():
        return False, "评论内容为空"

    return True, "ok"


# ── 主清洗流程 ──
def clean_raw_files(
    platforms: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """扫描 raw/ 目录，执行完整清洗流程。

    Returns:
        统计报告
    """
    if not RAW_DIR.exists():
        logger.warning("raw/ 目录不存在: %s", RAW_DIR)
        return {"status": "empty", "total": 0, "cleaned": 0, "noise": 0, "invalid": 0}

    # 收集所有原始文件
    all_records: list[dict[str, Any]] = []
    files_scanned = 0

    for platform_dir in sorted(RAW_DIR.iterdir()):
        if not platform_dir.is_dir() or platform_dir.name.startswith("."):
            continue
        if platform_dir.name == "test_comments":
            continue
        if platforms and platform_dir.name not in platforms:
            continue

        for date_dir in sorted(platform_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            for json_file in sorted(date_dir.glob("batch_*.json")):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        all_records.extend(data)
                    elif isinstance(data, dict):
                        all_records.append(data)
                    files_scanned += 1
                except (json.JSONDecodeError, OSError) as e:
                    logger.warning("跳过 %s: %s", json_file, e)

    logger.info("扫描 %d 个文件，共 %d 条原始记录", files_scanned, len(all_records))

    # 步骤 1: 去重
    before_dedup = len(all_records)
    all_records = deduplicate(all_records)
    dup_count = before_dedup - len(all_records)
    logger.info("去重: %d → %d (去除 %d 条重复)", before_dedup, len(all_records), dup_count)

    # 步骤 2: 标准化
    normalized = [normalize_record(r) for r in all_records]

    # 步骤 3: 去噪
    cleaned: list[dict[str, Any]] = []
    noise_count = 0
    for r in normalized:
        if is_noise(r["content"]):
            noise_count += 1
            continue
        cleaned.append(r)
    logger.info("去噪: %d → %d (去除 %d 条噪声)", len(normalized), len(cleaned), noise_count)

    # 步骤 4: 校验
    valid: list[dict[str, Any]] = []
    invalid_count = 0
    for r in cleaned:
        ok, reason = validate_record(r)
        if ok:
            valid.append(r)
        else:
            invalid_count += 1
            logger.debug("无效记录 %s: %s", r.get("comment_id", "?"), reason)

    logger.info("校验: %d → %d (去除 %d 条无效)", len(cleaned), len(valid), invalid_count)

    # ── 输出 ──
    if not dry_run and valid:
        CLEAN_DIR.mkdir(parents=True, exist_ok=True)

        today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
        output_file = CLEAN_DIR / f"cleaned_{today}.json"
        output_file.write_text(
            json.dumps(valid, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("清洗完成，保存 %d 条 → %s", len(valid), output_file)

    return {
        "status": "ok" if valid else "empty",
        "total": len(all_records) + dup_count,
        "duplicates": dup_count,
        "noise": noise_count,
        "invalid": invalid_count,
        "cleaned": len(valid),
        "files_scanned": files_scanned,
    }


# ── CLI ──
def main() -> None:
    parser = argparse.ArgumentParser(description="PV_OS 评论数据清洗管道")
    parser.add_argument("--platform", type=str, help="仅清洗指定平台 (douyin/xiaohongshu/kuaishou)")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不写入文件")
    args = parser.parse_args()

    platforms = [args.platform] if args.platform else None

    print("\n" + "=" * 50)
    print("  PV_OS Data Cleaner")
    print("=" * 50)
    if args.dry_run:
        print("  [DRY RUN 模式 — 不会写入文件]\n")

    report = clean_raw_files(platforms=platforms, dry_run=args.dry_run)

    print(f"\n  扫描文件: {report['files_scanned']}")
    print(f"  原始总数: {report['total']}")
    print(f"  去重:     {report['duplicates']}")
    print(f"  噪声:     {report['noise']}")
    print(f"  无效:     {report['invalid']}")
    print(f"  清洗后:   {report['cleaned']}")
    if not args.dry_run and report["cleaned"] > 0:
        today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
        print(f"\n  输出:     02_DATA/04_COMMENT_DATABASE/cleaned/cleaned_{today}.json")
    print()


if __name__ == "__main__":
    main()
