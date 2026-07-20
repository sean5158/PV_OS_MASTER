"""PV_OS Alert Engine — Inbound 客户主动咨询提醒引擎 V1.0。

实现 PV_OS_ALERT_ENGINE_DESIGN_V1.md:
    自有账号评论 S/A 级潜客 → 飞书机器人通知 → 人工回复。

包含:
1. Alert — 提醒数据结构
2. AlertEngine — 提醒生成 + 分级通知 + 抑制重复
3. ContactJourney — 客户触达旅程模型
4. FeishuAlertPayload — 飞书通知数据结构

Usage::

    from alert_engine import AlertEngine, ContactJourney, FeishuAlertPayload
    from collector_base import CommentRecord

    engine = AlertEngine()
    # 判断是否触发提醒
    if engine.should_alert(lead_grade="S", is_inbound=True):
        alert = engine.create_alert(comment_record, lead_grade="S", score=92, region="四川成都")
        payload = engine.build_feishu_payload(alert)
        # payload 可直接序列化为飞书机器人消息格式

存储:
- alert_log: 05_CUSTOMER_CRM/follow_ups/alert_log.csv
- contact_journey: 05_CUSTOMER_CRM/follow_ups/contact_journey.csv
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
CRM_FOLLOWUPS = PROJECT_ROOT / "05_CUSTOMER_CRM" / "follow_ups"
ALERT_LOG_CSV = CRM_FOLLOWUPS / "alert_log.csv"
CONTACT_JOURNEY_CSV = CRM_FOLLOWUPS / "contact_journey.csv"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))

# ── CSV 字段 ──
ALERT_LOG_FIELDS = [
    "alert_id", "lead_id", "comment_id", "user_id",
    "platform", "author", "comment_content",
    "video_title", "video_url",
    "region", "lead_grade", "lead_score",
    "user_profile_url", "comment_url",
    "notify_level", "alert_status",
    "created_at", "notified_at",
]

CONTACT_JOURNEY_FIELDS = [
    "journey_id", "lead_id", "user_id", "user_name",
    "platform", "comment_content_snippet",
    "source_url", "user_profile_url",
    "status", "contact_channel",
    "first_contact_at", "last_contact_at",
    "notes", "owner", "created_at", "updated_at",
]

# ── 有效状态转换 ──
VALID_JOURNEY_STATUSES = [
    "pending", "contacted", "replied",
    "wechat_added", "site_visit", "deal_closed", "no_need",
]

# ── 飞书 alert 去重窗口 (24小时)
ALERT_DEDUP_HOURS = 24


# ══════════════════════════════════════════════════════════════════════
# Alert — 提醒数据结构
# ══════════════════════════════════════════════════════════════════════

@dataclass
class Alert:
    """单条提醒。对标 PV_OS_ALERT_ENGINE_DESIGN_V1.md §三。"""

    # ── 标识 ──
    alert_id: str = ""
    lead_id: str = ""
    comment_id: str = ""
    user_id: str = ""

    # ── 来源 ──
    platform: str = ""
    author: str = ""
    comment_content: str = ""
    video_title: str = ""
    video_url: str = ""

    # ── 分析 ──
    region: str = ""
    lead_grade: str = ""        # S / A / B / C
    lead_score: int = 0

    # ── 链接 ──
    user_profile_url: str = ""
    comment_url: str = ""

    # ── 通知 ──
    notify_level: str = ""      # immediate / batch / none
    alert_status: str = "pending"  # pending / sent / suppressed

    # ── 时间 ──
    created_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"))
    notified_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Alert":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    def _dedup_key(self) -> str:
        """生成去重键: comment_id + date。"""
        date_part = self.created_at[:10] if self.created_at else datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
        return hashlib.md5(f"{self.comment_id}:{date_part}".encode()).hexdigest()


# ══════════════════════════════════════════════════════════════════════
# ContactJourney — 客户触达旅程
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ContactJourney:
    """客户触达旅程。对标 PV_OS_ALERT_ENGINE_DESIGN_V1.md §六。

    状态流转: pending → contacted → replied → wechat_added → site_visit → deal_closed
    """

    # ── 标识 ──
    journey_id: str = ""
    lead_id: str = ""
    user_id: str = ""
    user_name: str = ""

    # ── 来源 ──
    platform: str = ""
    comment_content_snippet: str = ""   # 评论摘要 (最大200字)
    source_url: str = ""
    user_profile_url: str = ""

    # ── 状态 ──
    status: str = "pending"         # pending|contacted|replied|wechat_added|site_visit|deal_closed|no_need
    contact_channel: str = ""       # 平台私信 | 微信 | 电话

    # ── 时间 ──
    first_contact_at: str = ""
    last_contact_at: str = ""

    # ── 人工 ──
    notes: str = ""
    owner: str = ""                 # 负责人

    # ── 系统 ──
    created_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContactJourney":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    @classmethod
    def from_row(cls, row: list[str]) -> "ContactJourney":
        d = dict(zip(CONTACT_JOURNEY_FIELDS, row))
        return cls.from_dict(d)

    def to_row(self) -> list[str]:
        return [str(self.to_dict().get(f, "")) for f in CONTACT_JOURNEY_FIELDS]

    def transition_to(self, new_status: str, notes: str = "") -> bool:
        """状态转换。返回 True 表示转换成功。"""
        if new_status not in VALID_JOURNEY_STATUSES:
            logger.warning("无效状态: %s", new_status)
            return False

        current_idx = VALID_JOURNEY_STATUSES.index(self.status) if self.status in VALID_JOURNEY_STATUSES else 0
        new_idx = VALID_JOURNEY_STATUSES.index(new_status)

        # 允许同级或前进（除 no_need 外不允许倒退）
        if new_status == "no_need":
            self.status = new_status
            self.updated_at = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")
            if notes:
                self.notes = notes
            return True

        if new_idx >= current_idx:
            self.status = new_status
            now = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")
            self.updated_at = now
            if new_status == "contacted" and not self.first_contact_at:
                self.first_contact_at = now
            self.last_contact_at = now
            if notes:
                self.notes = notes
            return True

        logger.warning("状态不可倒退: %s → %s", self.status, new_status)
        return False


# ══════════════════════════════════════════════════════════════════════
# FeishuAlertPayload — 飞书通知数据结构
# ══════════════════════════════════════════════════════════════════════

@dataclass
class FeishuAlertPayload:
    """飞书机器人通知负载。

    可序列化为飞书消息卡片 JSON。
    对标 PV_OS_ALERT_ENGINE_DESIGN_V1.md §三。
    """

    title: str = "🔔 新客户咨询提醒"
    platform: str = ""
    video_title: str = ""
    customer_name: str = ""
    comment_content: str = ""
    region: str = ""
    lead_grade: str = ""
    lead_score: int = 0
    alert_time: str = ""
    user_profile_url: str = ""
    comment_url: str = ""
    video_url: str = ""
    response_deadline: str = ""    # "24小时内" | "48小时内"

    def to_feishu_message(self) -> dict[str, Any]:
        """生成飞书消息卡片 JSON。

        飞书消息卡片格式参考:
        https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/card-components
        """
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": self.title,
                    },
                    "template": "red" if self.lead_grade == "S" else "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {"is_short": True, "text": {"tag": "lark_md", "content": f"**平台**\n{self.platform}"}},
                            {"is_short": True, "text": {"tag": "lark_md", "content": f"**视频**\n{self.video_title}"}},
                        ],
                    },
                    {
                        "tag": "div",
                        "fields": [
                            {"is_short": True, "text": {"tag": "lark_md", "content": f"**客户**\n{self.customer_name}"}},
                            {"is_short": True, "text": {"tag": "lark_md", "content": f"**地区**\n{self.region}"}},
                        ],
                    },
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": f"**💬 评论内容**\n{self.comment_content}"},
                    },
                    {
                        "tag": "div",
                        "fields": [
                            {"is_short": True, "text": {"tag": "lark_md", "content": f"**评分**: {self.lead_grade}级 ({self.lead_score}分)"}},
                            {"is_short": True, "text": {"tag": "lark_md", "content": f"**时效**: {self.response_deadline}"}},
                        ],
                    },
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": f"📎 [客户主页]({self.user_profile_url}) ｜ 📎 [评论链接]({self.comment_url}) ｜ 📎 [视频链接]({self.video_url})"},
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {"tag": "plain_text", "content": f"PV_OS Alert Engine · {self.alert_time}"},
                        ],
                    },
                ],
            },
        }

    def to_text_summary(self) -> str:
        """生成纯文本摘要 (用于日志)。"""
        lines = [
            f"🔔 新客户咨询提醒",
            f"",
            f"平台：{self.platform}",
            f"视频：{self.video_title}",
            f"客户：{self.customer_name}",
            f"评论：{self.comment_content[:100]}",
            f"地区：{self.region}",
            f"评分：{self.lead_grade}级 ({self.lead_score}分)",
            f"时间：{self.alert_time}",
            f"",
            f"📎 客户主页：{self.user_profile_url}",
            f"📎 评论链接：{self.comment_url}",
            f"📎 视频链接：{self.video_url}",
            f"",
            f"⏰ 请在 {self.response_deadline} 回复",
        ]
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
# AlertEngine — 提醒引擎
# ══════════════════════════════════════════════════════════════════════

class AlertEngine:
    """Inbound 客户主动咨询提醒引擎。

    功能:
    1. 分级通知: S → immediate, A → batch, B/C → none
    2. 重复提醒抑制: 同一 comment_id 24h 内不重复通知
    3. Alert 生成 + 飞书 payload
    4. ContactJourney 管理
    """

    def __init__(
        self,
        alert_csv: Path | None = None,
        journey_csv: Path | None = None,
    ) -> None:
        self.alert_csv = alert_csv or ALERT_LOG_CSV
        self.journey_csv = journey_csv or CONTACT_JOURNEY_CSV
        self.alert_csv.parent.mkdir(parents=True, exist_ok=True)

    # ── 通知策略 ──

    def should_alert(self, lead_grade: str, is_inbound: bool = True) -> bool:
        """判断是否应该触发提醒。

        Args:
            lead_grade: S / A / B / C
            is_inbound: 是否为自有账号评论
        """
        if not is_inbound:
            return False
        return lead_grade in ("S", "A")

    def get_notify_level(self, lead_grade: str) -> str:
        """获取通知级别。

        S → immediate (@负责人, 24h内回复)
        A → batch (群消息, 48h内回复)
        B → none (培育池)
        C → none (资产保存)
        """
        mapping = {"S": "immediate", "A": "batch", "B": "none", "C": "none"}
        return mapping.get(lead_grade, "none")

    def get_response_deadline(self, lead_grade: str) -> str:
        """获取回复时效要求。"""
        mapping = {"S": "24小时内", "A": "48小时内"}
        return mapping.get(lead_grade, "-")

    # ── Alert 创建 ──

    def create_alert(
        self,
        record: Any,
        lead_grade: str,
        score: int,
        region: str = "",
        lead_id: str = "",
    ) -> Alert:
        """从 CommentRecord + 分析结果创建 Alert。

        Args:
            record: CommentRecord 实例
            lead_grade: S / A / B / C
            score: Lead 分数
            region: 区域分析结果
            lead_id: 关联线索ID
        """
        alert_id = f"ALERT_{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")

        return Alert(
            alert_id=alert_id,
            lead_id=lead_id or f"LEAD_{uuid.uuid4().hex[:8].upper()}",
            comment_id=record.comment_id,
            user_id=record.user_id,
            platform=record.platform,
            author=record.author,
            comment_content=record.content,
            video_title=record.source_video_title,
            video_url=record.source_url,
            region=region,
            lead_grade=lead_grade,
            lead_score=score,
            user_profile_url=record.user_profile_url,
            comment_url=record.source_url,
            notify_level=self.get_notify_level(lead_grade),
            alert_status="pending",
            created_at=now,
        )

    def is_duplicate(self, comment_id: str) -> bool:
        """检查同一 comment_id 在 24h 内是否已提醒。"""
        if not self.alert_csv.exists():
            return False

        now = datetime.now(TZ_SHANGHAI)
        cutoff = now - timedelta(hours=ALERT_DEDUP_HOURS)

        with open(self.alert_csv, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("comment_id") == comment_id:
                    created = row.get("created_at", "")
                    try:
                        created_dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                        created_dt = created_dt.replace(tzinfo=TZ_SHANGHAI)
                        if created_dt > cutoff:
                            return True
                    except (ValueError, TypeError):
                        pass
        return False

    def process_inbound_lead(
        self,
        record: Any,
        lead_grade: str,
        score: int,
        region: str = "",
        lead_id: str = "",
    ) -> Alert | None:
        """处理 Inbound Lead: 判断 → 创建Alert → 记录日志。

        Returns:
            Alert (如果需要提醒) 或 None (不需要提醒或重复)
        """
        if not self.should_alert(lead_grade, is_inbound=True):
            return None

        if self.is_duplicate(record.comment_id):
            logger.info("AlertEngine: 重复提醒抑制 comment_id=%s", record.comment_id)
            return None

        alert = self.create_alert(record, lead_grade, score, region, lead_id)
        self._save_alert(alert)
        logger.info("AlertEngine: 新提醒 %s (%s级, %d分)", alert.alert_id, lead_grade, score)
        return alert

    # ── 飞书 Payload ──

    def build_feishu_payload(self, alert: Alert) -> FeishuAlertPayload:
        """从 Alert 构建飞书通知 Payload。"""
        return FeishuAlertPayload(
            platform=alert.platform,
            video_title=alert.video_title,
            customer_name=alert.author,
            comment_content=alert.comment_content,
            region=alert.region,
            lead_grade=alert.lead_grade,
            lead_score=alert.lead_score,
            alert_time=alert.created_at,
            user_profile_url=alert.user_profile_url,
            comment_url=alert.comment_url,
            video_url=alert.video_url,
            response_deadline=self.get_response_deadline(alert.lead_grade),
        )

    # ── ContactJourney ──

    def create_journey(
        self,
        lead_id: str,
        user_id: str,
        user_name: str = "",
        platform: str = "",
        comment_content: str = "",
        source_url: str = "",
        user_profile_url: str = "",
    ) -> ContactJourney:
        """为客户创建触达旅程。"""
        journey = ContactJourney(
            journey_id=f"JOURNEY_{uuid.uuid4().hex[:8].upper()}",
            lead_id=lead_id,
            user_id=user_id,
            user_name=user_name,
            platform=platform,
            comment_content_snippet=comment_content[:200],
            source_url=source_url,
            user_profile_url=user_profile_url,
            status="pending",
        )
        self._save_journey(journey)
        logger.info("AlertEngine: 创建旅程 %s (lead=%s)", journey.journey_id, lead_id)
        return journey

    def get_journey(self, journey_id: str) -> ContactJourney | None:
        """获取旅程。"""
        journeys = self._read_journeys()
        for j in journeys:
            if j.journey_id == journey_id:
                return j
        return None

    def get_journey_by_lead(self, lead_id: str) -> ContactJourney | None:
        """按 lead_id 获取旅程。"""
        journeys = self._read_journeys()
        for j in journeys:
            if j.lead_id == lead_id:
                return j
        return None

    def update_journey(self, journey_id: str, new_status: str, notes: str = "") -> bool:
        """更新旅程状态。"""
        journey = self.get_journey(journey_id)
        if journey is None:
            logger.warning("AlertEngine: 旅程 %s 不存在", journey_id)
            return False
        success = journey.transition_to(new_status, notes)
        if success:
            self._save_journey(journey)
        return success

    def list_all_journeys(self) -> list[ContactJourney]:
        """列出所有旅程。"""
        return self._read_journeys()

    def list_active_journeys(self) -> list[ContactJourney]:
        """列出活跃旅程 (未成交/未放弃)。"""
        terminal = {"deal_closed", "no_need"}
        return [j for j in self._read_journeys() if j.status not in terminal]

    def list_pending_journeys(self) -> list[ContactJourney]:
        """列出待触达旅程。"""
        return [j for j in self._read_journeys() if j.status == "pending"]

    # ── 统计 ──

    def get_stats(self) -> dict[str, Any]:
        """获取引擎统计信息。"""
        alerts = self._read_alerts()
        journeys = self._read_journeys()

        total_alerts = len(alerts)
        s_count = sum(1 for a in alerts if a.lead_grade == "S")
        a_count = sum(1 for a in alerts if a.lead_grade == "A")

        journey_by_status: dict[str, int] = {}
        for j in journeys:
            journey_by_status[j.status] = journey_by_status.get(j.status, 0) + 1

        return {
            "total_alerts": total_alerts,
            "s_alerts": s_count,
            "a_alerts": a_count,
            "total_journeys": len(journeys),
            "pending_journeys": len(self.list_pending_journeys()),
            "active_journeys": len(self.list_active_journeys()),
            "journey_by_status": journey_by_status,
        }

    # ── 内部持久化 ──

    def _save_alert(self, alert: Alert) -> None:
        file_exists = self.alert_csv.exists()
        row = [str(alert.to_dict().get(f, "")) for f in ALERT_LOG_FIELDS]
        with open(self.alert_csv, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(ALERT_LOG_FIELDS)
            w.writerow(row)

    def _read_alerts(self) -> list[Alert]:
        if not self.alert_csv.exists():
            return []
        results: list[Alert] = []
        with open(self.alert_csv, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(Alert.from_dict(row))
        return results

    def _save_journey(self, journey: ContactJourney) -> None:
        """保存或更新旅程 (按 journey_id 去重)。"""
        existing = self._read_journeys()
        existing_dict: dict[str, ContactJourney] = {j.journey_id: j for j in existing}
        existing_dict[journey.journey_id] = journey

        rows = [j.to_row() for j in existing_dict.values()]
        rows.sort(key=lambda r: r[0])
        with open(self.journey_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(CONTACT_JOURNEY_FIELDS)
            w.writerows(rows)

    def _read_journeys(self) -> list[ContactJourney]:
        if not self.journey_csv.exists():
            return []
        results: list[ContactJourney] = []
        with open(self.journey_csv, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None or header != CONTACT_JOURNEY_FIELDS:
                # 兼容旧格式
                return []
            for row in reader:
                if len(row) == len(CONTACT_JOURNEY_FIELDS):
                    results.append(ContactJourney.from_row(row))
        return results


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile, os
    from collector_base import CommentRecord

    print("=" * 60)
    print("  Alert Engine — 自检")
    print("=" * 60)

    tmp_dir = Path(tempfile.mkdtemp())
    engine = AlertEngine(
        alert_csv=tmp_dir / "test_alert_log.csv",
        journey_csv=tmp_dir / "test_contact_journey.csv",
    )

    # ── 1. 通知策略 ──
    assert engine.should_alert("S", is_inbound=True) == True
    assert engine.should_alert("A", is_inbound=True) == True
    assert engine.should_alert("B", is_inbound=True) == False
    assert engine.should_alert("S", is_inbound=False) == False
    assert engine.get_notify_level("S") == "immediate"
    assert engine.get_notify_level("A") == "batch"
    assert engine.get_notify_level("C") == "none"
    assert engine.get_response_deadline("S") == "24小时内"
    print("  通知策略: ✓")

    # ── 2. Alert 创建 ──
    record = CommentRecord(
        comment_id="cmt_inbound_001",
        platform="douyin",
        content="我家在成都锦江区，别墅想装光伏发电系统，能报个价吗？",
        author="成都锦江业主刘先生",
        source_video_title="别墅光伏安装实拍",
        source_url="https://douyin.com/video/own_v001",
        user_id="user_001",
        user_profile_url="https://douyin.com/user/user_001",
    )

    alert = engine.create_alert(record, "S", 92, "四川成都", "PV_LEAD_TEST_001")
    assert alert.lead_grade == "S"
    assert alert.notify_level == "immediate"
    assert alert.alert_status == "pending"
    print(f"  Alert: {alert.alert_id} ({alert.lead_grade}级, {alert.lead_score}分)")

    # ── 3. 重复抑制 ──
    assert engine.is_duplicate("cmt_inbound_001") == False
    engine._save_alert(alert)
    assert engine.is_duplicate("cmt_inbound_001") == True
    assert engine.is_duplicate("cmt_unknown") == False
    print("  重复抑制: ✓")

    # ── 4. process_inbound_lead ──
    record2 = CommentRecord(
        comment_id="cmt_inbound_002",
        platform="xiaohongshu",
        content="阳光房光伏发电效果怎么样？成都能装吗",
        author="成都小区别墅业主",
        source_video_title="阳光房光伏改造案例",
        source_url="https://xiaohongshu.com/explore/xxx",
        user_id="user_002",
        user_profile_url="https://xiaohongshu.com/user/user_002",
    )

    alert2 = engine.process_inbound_lead(record2, "A", 72, "四川成都")
    assert alert2 is not None
    assert alert2.lead_grade == "A"
    assert alert2.notify_level == "batch"
    print(f"  process_inbound_lead: {alert2.alert_id} ({alert2.lead_grade}级)")

    # B级不应触发
    record3 = CommentRecord(comment_id="cmt_inbound_003", content="测试", platform="douyin")
    alert3 = engine.process_inbound_lead(record3, "B", 45)
    assert alert3 is None
    print("  B级不触发: ✓")

    # ── 5. 飞书 Payload ──
    payload = engine.build_feishu_payload(alert)
    assert payload.platform == "douyin"
    assert payload.lead_grade == "S"
    assert "24小时内" in payload.response_deadline

    # JSON 序列化
    feishu_msg = payload.to_feishu_message()
    assert feishu_msg["msg_type"] == "interactive"
    assert len(feishu_msg["card"]["elements"]) >= 5
    print("  飞书 Payload: ✓")
    print(f"  飞书消息 JSON: {len(json.dumps(feishu_msg, ensure_ascii=False))} 字符")

    # 文本摘要
    text = payload.to_text_summary()
    assert "成都锦江业主刘先生" in text
    assert "S级 (92分)" in text
    print("  文本摘要: ✓")

    # ── 6. ContactJourney ──
    journey = engine.create_journey(
        lead_id="PV_LEAD_TEST_001",
        user_id="user_001",
        user_name="成都锦江业主刘先生",
        platform="douyin",
        comment_content="我家在成都锦江区，别墅想装光伏发电系统，能报个价吗？",
        source_url="https://douyin.com/video/own_v001",
        user_profile_url="https://douyin.com/user/user_001",
    )
    assert journey.status == "pending"
    assert journey.lead_id == "PV_LEAD_TEST_001"
    print(f"  旅程: {journey.journey_id} ({journey.status})")

    # 状态转换
    assert journey.transition_to("contacted") == True
    assert journey.status == "contacted"
    assert journey.first_contact_at != ""
    print(f"  contacted: {journey.status}")

    assert journey.transition_to("replied") == True
    assert journey.transition_to("wechat_added") == True
    assert journey.transition_to("site_visit") == True
    assert journey.transition_to("deal_closed") == True
    print(f"  全流程: pending → {journey.status} ✓")

    # 不可倒退
    journey2 = ContactJourney(journey_id="test2", status="replied")
    assert journey2.transition_to("pending") == False
    assert journey2.transition_to("contacted") == False
    print("  不可倒退: ✓")

    # no_need 允许
    journey3 = ContactJourney(journey_id="test3", status="pending")
    assert journey3.transition_to("no_need") == True
    print("  no_need: ✓")

    # ── 7. 持久化 ──
    journeys = engine.list_all_journeys()
    assert len(journeys) >= 3
    print(f"  旅程总数: {len(journeys)}")

    pending = engine.list_pending_journeys()
    print(f"  待触达: {len(pending)}")

    active = engine.list_active_journeys()
    print(f"  活跃: {len(active)}")

    # ── 8. 统计 ──
    stats = engine.get_stats()
    assert stats["total_alerts"] >= 2
    assert stats["s_alerts"] >= 1
    print(f"  统计: alerts={stats['total_alerts']}, S={stats['s_alerts']}, A={stats['a_alerts']}")

    # 清理
    engine.alert_csv.unlink(missing_ok=True)
    engine.journey_csv.unlink(missing_ok=True)

    print("\n✓ Alert Engine 自检完成\n")
