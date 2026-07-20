"""PV_OS 飞书 Webhook 客户端 — 消息卡片发送 V1.0。

将 AlertEngine 生成的 FeishuAlertPayload 通过飞书机器人 Webhook 发送到指定群。

实现 Phase3-1_Feishu_Operation_Design.md §一:
    Alert Engine → 飞书机器人 → 群消息/@负责人

支持模式:
- mock: 仅生成 payload，不真实发送（测试用，默认）
- live:  真实 HTTP POST 到飞书 Webhook

Usage::

    from feishu_webhook_client import FeishuWebhookClient
    from alert_engine import FeishuAlertPayload

    client = FeishuWebhookClient(webhook_url="https://open.feishu.cn/...", mode="mock")
    payload = FeishuAlertPayload(platform="douyin", ...)
    result = client.send(payload)
    # result: {"success": True, "mode": "mock", "payload": {...}}
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))


# ══════════════════════════════════════════════════════════════════════
# SendResult
# ══════════════════════════════════════════════════════════════════════

@dataclass
class SendResult:
    """飞书消息发送结果。"""

    success: bool = False
    mode: str = "mock"              # mock | live
    message_id: str = ""            # 飞书返回的消息 ID
    http_status: int = 0            # HTTP 状态码
    error: str = ""                 # 错误信息
    payload_snapshot: dict[str, Any] = field(default_factory=dict)
    sent_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════
# FeishuWebhookClient
# ══════════════════════════════════════════════════════════════════════

class FeishuWebhookClient:
    """飞书 Webhook 消息发送客户端。

    支持 mock（测试）和 live（真实发送）两种模式。

    飞书自定义机器人 Webhook 文档:
    https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
    """

    # 飞书 Webhook 标准地址
    FEISHU_WEBHOOK_BASE = "https://open.feishu.cn/open-apis/bot/v2/hook"

    def __init__(
        self,
        webhook_url: str = "",
        mode: str = "mock",
        owner_open_id: str = "",
        timeout_seconds: int = 10,
    ) -> None:
        """
        Args:
            webhook_url: 飞书机器人 Webhook 完整 URL
            mode: mock（测试，默认） | live（真实发送）
            owner_open_id: S级 @负责人的飞书 open_id
            timeout_seconds: HTTP 请求超时
        """
        self.webhook_url = webhook_url
        self.mode = mode
        self.owner_open_id = owner_open_id
        self.timeout = timeout_seconds
        self._send_history: list[SendResult] = []

    def send(self, payload: Any, at_owner: bool = False) -> SendResult:
        """发送飞书消息卡片。

        Args:
            payload: FeishuAlertPayload 实例
            at_owner: 是否 @负责人（S级为 True）

        Returns:
            SendResult
        """
        if self.mode == "mock":
            return self._mock_send(payload, at_owner)

        return self._live_send(payload, at_owner)

    def send_alert(self, payload: Any, lead_grade: str = "A") -> SendResult:
        """发送 Alert 消息（便捷方法，自动判断是否 @负责人）。

        S级: @负责人 + 红卡片
        A级: 群消息 + 蓝卡片
        """
        at_owner = (lead_grade == "S")
        return self.send(payload, at_owner)

    def get_send_history(self) -> list[SendResult]:
        """获取发送历史。"""
        return self._send_history

    def get_stats(self) -> dict[str, Any]:
        """获取发送统计。"""
        total = len(self._send_history)
        success_count = sum(1 for r in self._send_history if r.success)
        return {
            "total_sent": total,
            "success": success_count,
            "failed": total - success_count,
            "mode": self.mode,
        }

    # ── 内部 ──

    def _mock_send(self, payload: Any, at_owner: bool = False) -> SendResult:
        """Mock 模式: 生成消息但不发送。"""
        msg = payload.to_feishu_message()

        # 如果是 S级且需要 @负责人
        if at_owner and self.owner_open_id:
            msg["card"]["header"]["title"]["content"] = (
                f"🔔 新客户咨询提醒 (@负责人)"
            )
            # 在飞书卡片中追加 at 元素
            msg["card"]["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"<at id={self.owner_open_id}></at> 请及时处理",
                },
            })

        result = SendResult(
            success=True,
            mode="mock",
            message_id=f"mock_msg_{datetime.now(TZ_SHANGHAI).strftime('%Y%m%d%H%M%S')}",
            payload_snapshot=msg,
        )
        self._send_history.append(result)
        logger.info(
            "FeishuWebhook [MOCK]: %s 级 Alert 已生成 (at_owner=%s)",
            payload.lead_grade, at_owner,
        )
        return result

    def _live_send(self, payload: Any, at_owner: bool = False) -> SendResult:
        """Live 模式: 真实 HTTP POST 到飞书 Webhook。"""
        try:
            import urllib.request
        except ImportError:
            return SendResult(
                success=False,
                mode="live",
                error="urllib.request not available",
            )

        if not self.webhook_url:
            return SendResult(
                success=False,
                mode="live",
                error="webhook_url not configured",
            )

        msg = payload.to_feishu_message()

        # S级 @负责人
        if at_owner and self.owner_open_id:
            msg["card"]["header"]["title"]["content"] = (
                f"🔔 新客户咨询提醒 (@负责人)"
            )
            msg["card"]["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"<at id={self.owner_open_id}></at> 请及时处理",
                },
            })

        try:
            data = json.dumps(msg, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_body = resp.read().decode("utf-8")
                resp_json = json.loads(resp_body)
                http_status = resp.status
                message_id = resp_json.get("data", {}).get("message_id", "")

                result = SendResult(
                    success=(http_status == 200),
                    mode="live",
                    message_id=message_id,
                    http_status=http_status,
                    payload_snapshot=msg,
                )

        except urllib.error.HTTPError as e:
            result = SendResult(
                success=False,
                mode="live",
                http_status=e.code,
                error=f"HTTP {e.code}: {e.reason}",
                payload_snapshot=msg,
            )
        except Exception as e:
            result = SendResult(
                success=False,
                mode="live",
                error=str(e),
                payload_snapshot=msg,
            )

        self._send_history.append(result)
        logger.info(
            "FeishuWebhook [LIVE]: %s级 Alert → HTTP %s (%s)",
            payload.lead_grade,
            result.http_status,
            "OK" if result.success else result.error,
        )
        return result


# ══════════════════════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════════════════════

def create_mock_client() -> FeishuWebhookClient:
    """创建 Mock 模式客户端（测试用）。"""
    return FeishuWebhookClient(mode="mock")


def send_test_alert(
    client: FeishuWebhookClient,
    platform: str = "douyin",
    grade: str = "S",
) -> SendResult:
    """发送一条测试 Alert（快速验证）。"""
    from alert_engine import FeishuAlertPayload

    payload = FeishuAlertPayload(
        platform=platform,
        video_title="别墅光伏安装实拍",
        customer_name="成都锦江业主刘先生",
        comment_content="我家在成都锦江区别墅，想装一套光伏发电系统，能报个价吗？",
        region="四川成都",
        lead_grade=grade,
        lead_score=92,
        alert_time=datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M"),
        user_profile_url="https://douyin.com/user/test_user",
        comment_url="https://douyin.com/video/test_video",
        video_url="https://douyin.com/video/test_video",
        response_deadline="24小时内" if grade == "S" else "48小时内",
    )
    return client.send_alert(payload, lead_grade=grade)


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from alert_engine import FeishuAlertPayload

    print("=" * 60)
    print("  Feishu Webhook Client — 自检")
    print("=" * 60)

    # Mock 模式
    client = FeishuWebhookClient(mode="mock", owner_open_id="ou_test_001")

    # S级 Alert
    payload_s = FeishuAlertPayload(
        platform="douyin",
        video_title="别墅光伏安装实拍",
        customer_name="成都锦江业主刘先生",
        comment_content="我家在成都锦江区别墅，想装一套光伏发电系统，能报个价吗？",
        region="四川成都",
        lead_grade="S",
        lead_score=92,
        alert_time=datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M"),
        user_profile_url="https://douyin.com/user/u1",
        comment_url="https://douyin.com/video/v1",
        video_url="https://douyin.com/video/v1",
        response_deadline="24小时内",
    )
    result_s = client.send_alert(payload_s, lead_grade="S")
    assert result_s.success
    assert result_s.mode == "mock"
    assert "@负责人" in result_s.payload_snapshot["card"]["header"]["title"]["content"]
    print("  S级 Alert (mock + @负责人): ✓")

    # A级 Alert
    payload_a = FeishuAlertPayload(
        platform="xiaohongshu",
        video_title="阳光房光伏改造",
        customer_name="重庆渝北业主",
        comment_content="阳光房能做光伏顶吗？大概多少钱？",
        region="重庆",
        lead_grade="A",
        lead_score=72,
        alert_time=datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M"),
        user_profile_url="https://xhs.com/user/u2",
        comment_url="https://xhs.com/explore/v2",
        video_url="https://xhs.com/explore/v2",
        response_deadline="48小时内",
    )
    result_a = client.send_alert(payload_a, lead_grade="A")
    assert result_a.success
    assert "@负责人" not in result_a.payload_snapshot["card"]["header"]["title"]["content"]
    print("  A级 Alert (mock, 无@): ✓")

    # 历史记录
    assert len(client.get_send_history()) == 2
    stats = client.get_stats()
    assert stats["total_sent"] == 2
    assert stats["success"] == 2
    print(f"  统计: {stats}")

    # JSON序列化验证
    msg_json = json.dumps(result_s.payload_snapshot, ensure_ascii=False)
    assert len(msg_json) > 200
    print(f"  消息JSON: {len(msg_json)} 字符")

    # Live模式无URL
    live_client = FeishuWebhookClient(mode="live")
    result_no_url = live_client.send(payload_s)
    assert not result_no_url.success
    assert "not configured" in result_no_url.error
    print("  Live 无 URL: 正确拒绝 ✓")

    print("\n✓ Feishu Webhook Client 自检完成\n")
