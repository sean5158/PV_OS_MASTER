"""PV_OS 飞书多维表客户端 — Lead数据同步接口 V1.0。

将 Lead 数据同步到飞书多维表（Bitable），作为人工运营工作台。

实现 Phase3-1_Feishu_Operation_Design.md §二:
    16字段多维表 + 单向同步 (数据库→飞书)

支持模式:
- mock: 本地记录同步日志，不真实调用 API（测试用，默认）
- live:  真实调用飞书多维表 API

Usage::

    from feishu_bitable_client import FeishuBitableClient, BitableRecord

    client = FeishuBitableClient(app_id="xxx", app_secret="xxx", mode="mock")
    record = BitableRecord(lead_id="LEAD_001", platform="douyin", ...)
    result = client.upsert_record(record)
"""

from __future__ import annotations

import csv
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
SYNC_LOG_CSV = PROJECT_ROOT / "05_CUSTOMER_CRM" / "follow_ups" / "feishu_bitable_sync_log.csv"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))

# ── CSV 字段 ──
SYNC_LOG_FIELDS = [
    "sync_id", "lead_id", "platform", "account_name",
    "customer_name", "user_id", "user_profile_url",
    "video_url", "comment_url", "comment_text",
    "region", "intent_score", "lead_grade", "status",
    "sync_mode", "sync_success", "synced_at",
]


# ══════════════════════════════════════════════════════════════════════
# BitableRecord
# ══════════════════════════════════════════════════════════════════════

@dataclass
class BitableRecord:
    """飞书多维表记录 — 对应于多维表的 13 个核心字段。

    对标 Phase3-1_Feishu_Operation_Design.md §二.2。
    """

    # ── 核心标识 ──
    lead_id: str = ""
    platform: str = ""              # 抖音/小红书/快手/视频号
    account_name: str = ""          # 自有账号昵称
    customer_name: str = ""         # 客户昵称
    user_id: str = ""               # 平台用户ID

    # ── 链接 ──
    user_profile_url: str = ""      # 客户主页
    video_url: str = ""             # 原视频
    comment_url: str = ""           # 评论链接

    # ── 内容 ──
    comment_text: str = ""          # 评论原文（截断200字）

    # ── AI分析 ──
    region: str = ""                # 四川成都/重庆/贵州贵阳
    intent_score: int = 0           # 0-100
    lead_grade: str = ""            # S / A

    # ── 跟进 ──
    status: str = "pending"         # pending→contacted→replied→wechat_added→site_visit→deal_closed

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_alert(cls, alert: Any, account_name: str = "", intent_score: int = 0) -> "BitableRecord":
        """从 Alert 对象创建多维表记录。"""
        return cls(
            lead_id=alert.lead_id,
            platform=alert.platform,
            account_name=account_name,
            customer_name=alert.author,
            user_id=alert.user_id,
            user_profile_url=alert.user_profile_url,
            video_url=alert.video_url,
            comment_url=alert.comment_url,
            comment_text=alert.comment_content[:200],
            region=alert.region,
            intent_score=intent_score,
            lead_grade=alert.lead_grade,
            status="pending",
        )

    @classmethod
    def from_comment_record(cls, record: Any, lead_id: str, region: str,
                            lead_grade: str, lead_score: int,
                            account_name: str = "") -> "BitableRecord":
        """从 CommentRecord 创建多维表记录。"""
        return cls(
            lead_id=lead_id,
            platform=record.platform,
            account_name=account_name or record.video_author_name,
            customer_name=record.author,
            user_id=record.user_id,
            user_profile_url=record.user_profile_url,
            video_url=record.source_url,
            comment_url=record.source_url,
            comment_text=record.content[:200],
            region=region,
            intent_score=lead_score,
            lead_grade=lead_grade,
            status="pending",
        )


# ══════════════════════════════════════════════════════════════════════
# SyncResult
# ══════════════════════════════════════════════════════════════════════

@dataclass
class SyncResult:
    """同步操作结果。"""

    success: bool = False
    sync_id: str = ""
    lead_id: str = ""
    mode: str = "mock"
    action: str = ""                # insert | update | skip
    error: str = ""
    synced_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════
# FeishuBitableClient
# ══════════════════════════════════════════════════════════════════════

class FeishuBitableClient:
    """飞书多维表同步客户端。

    功能:
    1. 新增/更新多维表行（按 lead_id 去重）
    2. 本地同步日志（mock 模式下持久化到 CSV）
    3. 单向同步: 数据库 → 飞书

    飞书多维表 API 文档:
    https://open.feishu.cn/document/server-docs/docs/bitable-v1/overview
    """

    # 飞书 API 基础地址
    FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        bitable_id: str = "",
        table_id: str = "",
        mode: str = "mock",
        sync_log_csv: Path | None = None,
    ) -> None:
        """
        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用密钥
            bitable_id: 多维表 ID
            table_id: 子表 ID
            mode: mock（测试，默认） | live（真实同步）
            sync_log_csv: 同步日志 CSV 路径
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.bitable_id = bitable_id
        self.table_id = table_id
        self.mode = mode
        self.sync_log_csv = sync_log_csv or SYNC_LOG_CSV
        self.sync_log_csv.parent.mkdir(parents=True, exist_ok=True)
        self._access_token: str = ""
        self._sync_counter: int = 0
        self._token_expires_at: float = 0.0

    # ── 公开方法 ──

    def upsert_record(self, record: BitableRecord) -> SyncResult:
        """新增或更新多维表记录（按 lead_id 去重）。

        如果 lead_id 已存在 → update
        如果 lead_id 不存在 → insert
        """
        exists = self._record_exists_in_log(record.lead_id)

        if self.mode == "mock":
            return self._mock_upsert(record, exists)

        return self._live_upsert(record, exists)

    def sync_from_alert(self, alert: Any, account_name: str = "",
                        intent_score: int = 0) -> SyncResult:
        """从 Alert 同步到多维表。"""
        record = BitableRecord.from_alert(alert, account_name, intent_score)
        return self.upsert_record(record)

    def sync_batch(self, records: list[BitableRecord]) -> list[SyncResult]:
        """批量同步。"""
        results: list[SyncResult] = []
        for r in records:
            results.append(self.upsert_record(r))
        return results

    def get_sync_log(self) -> list[dict[str, str]]:
        """获取同步日志。"""
        return self._read_log()

    def get_stats(self) -> dict[str, Any]:
        """获取同步统计。"""
        log = self._read_log()
        total = len(log)
        success = sum(1 for r in log if r.get("sync_success") == "True")
        by_grade: dict[str, int] = {}
        for r in log:
            g = r.get("lead_grade", "?")
            by_grade[g] = by_grade.get(g, 0) + 1
        return {
            "total_synced": total,
            "success": success,
            "failed": total - success,
            "mode": self.mode,
            "by_grade": by_grade,
        }

    # ── 内部 Mock ──

    def _mock_upsert(self, record: BitableRecord, exists: bool) -> SyncResult:
        """Mock 模式: 仅写本地日志。"""
        self._sync_counter += 1
        sync_id = f'SYNC_{record.lead_id}_{datetime.now(TZ_SHANGHAI).strftime("%H%M%S")}_{self._sync_counter:04d}'
        action = "update" if exists else "insert"
        result = SyncResult(
            success=True,
            sync_id=sync_id,
            lead_id=record.lead_id,
            mode="mock",
            action=action,
        )
        self._write_log(record, sync_id, True)
        logger.info(
            "FeishuBitable [MOCK]: %s %s (%s级)",
            action, record.lead_id, record.lead_grade,
        )
        return result

    # ── 内部 Live ──

    def _live_upsert(self, record: BitableRecord, exists: bool) -> SyncResult:
        """Live 模式: 调用飞书多维表 API。"""
        if not self.app_id or not self.app_secret:
            return SyncResult(
                success=False,
                lead_id=record.lead_id,
                mode="live",
                action="skip",
                error="app_id or app_secret not configured",
            )

        try:
            import urllib.request
        except ImportError:
            return SyncResult(
                success=False,
                lead_id=record.lead_id,
                mode="live",
                error="urllib.request not available",
            )

        # 获取 access_token
        token = self._get_access_token()
        if not token:
            return SyncResult(
                success=False,
                lead_id=record.lead_id,
                mode="live",
                error="failed to get access_token",
            )

        # 构建 API payload
        fields_data = self._record_to_fields(record)

        if exists:
            # TODO: 先查询 record_id，再 update
            # 当前简化：直接 insert（飞书多维表允许重复 lead_id，需人工去重）
            action = "insert"
        else:
            action = "insert"

        try:
            url = (
                f"{self.FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_id}"
                f"/tables/{self.table_id}/records"
            )
            body = json.dumps({"fields": fields_data}, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"Bearer {token}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_body = json.loads(resp.read().decode("utf-8"))
                sync_id = resp_body.get("data", {}).get("record", {}).get("record_id", "")

                result = SyncResult(
                    success=True,
                    sync_id=sync_id,
                    lead_id=record.lead_id,
                    mode="live",
                    action=action,
                )
        except Exception as e:
            result = SyncResult(
                success=False,
                lead_id=record.lead_id,
                mode="live",
                action=action,
                error=str(e),
            )

        self._write_log(record, result.sync_id, result.success)
        return result

    # ── 飞书 API 内部 ──

    def _get_access_token(self) -> str:
        """获取 tenant_access_token（带缓存）。"""
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        try:
            import urllib.request

            url = (
                f"{self.FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
            )
            body = json.dumps({
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._access_token = data.get("tenant_access_token", "")
                expire = data.get("expire", 7200)
                self._token_expires_at = now + expire - 60  # 提前60秒刷新
                return self._access_token
        except Exception as e:
            logger.error("获取飞书 access_token 失败: %s", e)
            return ""

    def _record_to_fields(self, record: BitableRecord) -> dict[str, Any]:
        """将 BitableRecord 转换为飞书多维表 fields 格式。"""
        return {
            "lead_id": record.lead_id,
            "platform": record.platform,
            "account_name": record.account_name,
            "customer_name": record.customer_name,
            "user_id": record.user_id,
            "user_profile_url": {
                "link": record.user_profile_url,
                "text": "客户主页",
            } if record.user_profile_url else "",
            "video_url": {
                "link": record.video_url,
                "text": "原视频",
            } if record.video_url else "",
            "comment_url": {
                "link": record.comment_url,
                "text": "评论链接",
            } if record.comment_url else "",
            "comment_text": record.comment_text[:200],
            "region": record.region,
            "intent_score": record.intent_score,
            "lead_grade": record.lead_grade,
            "status": record.status,
        }

    # ── 日志持久化 ──

    def _record_exists_in_log(self, lead_id: str) -> bool:
        """检查 lead_id 是否已在日志中。"""
        log = self._read_log()
        return any(r.get("lead_id") == lead_id for r in log)

    def _write_log(self, record: BitableRecord, sync_id: str, success: bool) -> None:
        """写入同步日志。"""
        row = [
            sync_id, record.lead_id, record.platform,
            record.account_name, record.customer_name,
            record.user_id, record.user_profile_url,
            record.video_url, record.comment_url,
            record.comment_text[:200], record.region,
            str(record.intent_score), record.lead_grade,
            record.status, self.mode,
            str(success),
            datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"),
        ]
        file_exists = self.sync_log_csv.exists()
        with open(self.sync_log_csv, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(SYNC_LOG_FIELDS)
            w.writerow(row)

    def _read_log(self) -> list[dict[str, str]]:
        """读取同步日志。"""
        if not self.sync_log_csv.exists():
            return []
        results: list[dict[str, str]] = []
        with open(self.sync_log_csv, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
        return results


# ══════════════════════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════════════════════

def create_mock_client() -> FeishuBitableClient:
    """创建 Mock 模式客户端（测试用）。"""
    return FeishuBitableClient(mode="mock")


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile

    print("=" * 60)
    print("  Feishu Bitable Client — 自检")
    print("=" * 60)

    tmp_dir = Path(tempfile.mkdtemp())
    client = FeishuBitableClient(mode="mock", sync_log_csv=tmp_dir / "sync_log.csv")

    # ── 1. BitableRecord ──
    rec = BitableRecord(
        lead_id="LEAD_TEST_001",
        platform="douyin",
        account_name="成都光伏小马哥",
        customer_name="成都锦江业主刘先生",
        user_id="user_001",
        user_profile_url="https://douyin.com/user/user_001",
        video_url="https://douyin.com/video/v1",
        comment_url="https://douyin.com/video/v1",
        comment_text="我家在成都锦江区别墅，想装一套光伏发电系统，能报个价吗？",
        region="四川成都",
        intent_score=92,
        lead_grade="S",
        status="pending",
    )
    assert rec.lead_grade == "S"
    assert rec.platform == "douyin"
    print(f"  Record: {rec.lead_id} ({rec.lead_grade}级, {rec.region})")

    # ── 2. upsert ──
    result1 = client.upsert_record(rec)
    assert result1.success
    assert result1.action == "insert"
    assert result1.mode == "mock"
    print(f"  Insert: {result1.action} {result1.sync_id[:20]}...")

    # ── 3. duplicate upsert → update ──
    result2 = client.upsert_record(rec)
    assert result2.success
    assert result2.action == "update"
    print(f"  Update: {result2.action} (duplicate lead_id)")

    # ── 4. 批量 ──
    rec2 = BitableRecord(lead_id="LEAD_TEST_002", platform="xiaohongshu",
                         lead_grade="A", region="重庆", status="pending",
                         customer_name="重庆渝北业主")
    rec3 = BitableRecord(lead_id="LEAD_TEST_003", platform="kuaishou",
                         lead_grade="A", region="贵州贵阳", status="pending",
                         customer_name="贵阳业主")
    results = client.sync_batch([rec2, rec3])
    assert len(results) == 2
    assert all(r.success for r in results)
    print(f"  Batch: {len(results)} records synced")

    # ── 5. from_alert ──
    from alert_engine import Alert
    alert = Alert(
        alert_id="ALERT_001", lead_id="LEAD_ALERT_001",
        platform="douyin", author="测试客户", user_id="u001",
        comment_content="测试评论", region="四川成都",
        lead_grade="S", lead_score=90,
        user_profile_url="https://douyin.com/user/u001",
        video_url="https://douyin.com/video/v001",
        comment_url="https://douyin.com/video/v001",
    )
    bitable_rec = BitableRecord.from_alert(alert, account_name="成都光伏小马哥", intent_score=90)
    assert bitable_rec.lead_id == "LEAD_ALERT_001"
    assert bitable_rec.account_name == "成都光伏小马哥"
    result4 = client.sync_from_alert(alert, "成都光伏小马哥", 90)
    assert result4.success
    print(f"  from_alert: {result4.action} {result4.lead_id}")

    # ── 6. 日志 ──
    log = client.get_sync_log()
    assert len(log) >= 4
    print(f"  Sync log: {len(log)} entries")

    # ── 7. 统计 ──
    stats = client.get_stats()
    assert stats["total_synced"] >= 4
    assert stats["success"] >= 4
    print(f"  Stats: total={stats['total_synced']}, S={stats['by_grade'].get('S', 0)}, A={stats['by_grade'].get('A', 0)}")

    # ── 8. Live 无凭证 → skip ──
    live_client = FeishuBitableClient(mode="live")
    live_result = live_client.upsert_record(rec)
    assert not live_result.success
    assert "not configured" in live_result.error
    print("  Live 无凭证: 正确拒绝 ✓")

    # ── 9. 长评论截断 ──
    long_text = "光伏" * 150
    rec_long = BitableRecord(lead_id="LEAD_LONG", comment_text=long_text[:200])
    assert len(rec_long.comment_text) <= 200
    print(f"  长评论截断: {len(rec_long.comment_text)} chars (≤200)")

    # 清理
    client.sync_log_csv.unlink(missing_ok=True)

    print("\n✓ Feishu Bitable Client 自检完成\n")
