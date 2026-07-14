#!/usr/bin/env python3
"""PV_OS Automation Engine CLI.

Usage::

    # Run with a sample JSON comment
    python run_pipeline.py --comment data.json

    # Run in test mode with built-in sample comments
    python run_pipeline.py --test

    # Show what would happen (dry run)
    python run_pipeline.py --test --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so engine imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENGINE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(ENGINE_ROOT))

from engine import Engine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

SAMPLE_COMMENTS = [
    {
        "id": "douyin_test_S_001",
        "platform": "douyin",
        "content": "我家在成都郊区别墅，想装一套光伏系统，能报个价吗？电话联系138xxxx",
        "author": "用户A",
        "create_time": "2026-07-12 10:00:00",
        "source_url": "https://douyin.com/video/test_s",
        "ip_location": "四川成都",
        "video_title": "别墅光伏安装实拍",
        "keyword": "别墅光伏",
    },
    {
        "id": "douyin_test_A_001",
        "platform": "douyin",
        "content": "农村自建房想装光伏发电，大概多少钱？有补贴吗",
        "author": "用户B",
        "create_time": "2026-07-10 14:00:00",
        "source_url": "https://douyin.com/video/test_a",
        "ip_location": "重庆",
        "video_title": "农村光伏发电省钱吗",
        "keyword": "农村光伏",
    },
    {
        "id": "douyin_test_B_001",
        "platform": "xiaohongshu",
        "content": "光伏发电靠谱吗？想了解一下",
        "author": "用户C",
        "create_time": "2026-07-01 09:00:00",
        "source_url": "https://xiaohongshu.com/note/test_b",
        "ip_location": "贵州贵阳",
        "video_title": "光伏发电入门科普",
        "keyword": "光伏",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="PV_OS Automation Engine CLI")
    parser.add_argument("--test", action="store_true", help="Run with built-in sample comments")
    parser.add_argument("--comment", type=str, help="Path to a JSON comment file")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without executing")
    args = parser.parse_args()

    workflow_path = PROJECT_ROOT / "10_AI_AUTOMATION_ENGINE" / "workflows" / "comment_to_lead_pipeline.yml"
    engine = Engine(workflow_path)

    if args.dry_run:
        print(f"\nWorkflow: {engine.name}")
        print(f"Steps ({len(engine.steps)}):")
        for i, step in enumerate(engine.steps, 1):
            print(f"  {i}. {step.get('name')}")
        return

    if args.comment:
        data = json.loads(Path(args.comment).read_text(encoding="utf-8"))
        result = engine.run_single(data)
        _print_result(result)

    elif args.test:
        for comment in SAMPLE_COMMENTS:
            print(f"\n{'='*60}")
            print(f"  Testing: {comment['id']} — {comment['content'][:40]}...")
            print(f"{'='*60}")
            result = engine.run_single(comment)
            _print_result(result)

    else:
        parser.print_help()


def _print_result(result: dict) -> None:
    scoring = result.get("scoring", {})
    lead = result.get("lead", {})
    follow_up = result.get("follow_up", {})

    print(f"\n  Grade:       {scoring.get('lead_grade', '?')}")
    print(f"  Total Score: {scoring.get('total_score', '?')}/100")
    print(f"  Demand: {scoring.get('demand_score', '?')}  "
          f"Region: {scoring.get('region_score', '?')}  "
          f"Housing: {scoring.get('housing_score', '?')}  "
          f"Time: {scoring.get('time_score', '?')}  "
          f"Auth: {scoring.get('authenticity_score', '?')}")
    print(f"  Lead ID:     {lead.get('lead_id', '—')}")
    print(f"  Status:      {lead.get('status', '—')}")
    print(f"  Urgency:     {scoring.get('urgency', '—')}")
    if follow_up:
        print(f"  Follow-up:   {follow_up.get('action', '')} (due {follow_up.get('due_by', '')})")
    if "_pipeline_error" in result:
        print(f"  ⚠ Pipeline halted at step: {result['_pipeline_error']}")


if __name__ == "__main__":
    main()
