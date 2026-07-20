"""PV_OS 平台适配器管理器。

统一管理 Collector 创建、模式切换 (auto/mock/public)、凭证校验、速率限制。
为 P2 真实平台数据接入提供统一入口，同时保持 Mock 模式可用。

架构::

    platform_adapter.get_collector(platform, mode)
        ├─ mode=auto:  凭证有效→public, 无效→mock (智能降级)
        ├─ mode=mock:  始终返回 Mock Collector
        └─ mode=public:  必须有有效凭证才返回 Public Collector

Usage::

    from platform_adapter import PlatformAdapterManager

    adapter = PlatformAdapterManager()
    collector = adapter.get_collector("douyin", mode="auto")
    comments = collector.collect_and_save(account_id="xxx", account_name="某博主")

    # 或使用便捷函数
    from platform_adapter import get_collector
    collector = get_collector("douyin", mode="mock")
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Any

# 复用现有模块
from collector_base import BaseCollector, create_collector as _legacy_create
from config_loader import load_collection_config, load_platform_credentials
from live_collector_base import RateLimiter

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ══════════════════════════════════════════════════════════════════════
# 模式定义
# ══════════════════════════════════════════════════════════════════════

class CollectorMode(str, Enum):
    """采集器运行模式。"""
    AUTO = "auto"    # 智能: 凭证有效→live, 否则→mock
    MOCK = "mock"    # 始终 Mock (P0 默认)
    PUBLIC = "public"    # 公开数据采集
    FILE = "file"    # CSV/文件导入模式

    def __str__(self) -> str:
        return self.value


# ══════════════════════════════════════════════════════════════════════
# 平台配置默认值
# ══════════════════════════════════════════════════════════════════════

DEFAULT_RATE_LIMITS: dict[str, dict[str, Any]] = {
    "douyin":       {"requests_per_minute": 10, "cooldown_seconds": 30},
    "xiaohongshu":  {"requests_per_minute": 5,  "cooldown_seconds": 60},
    "kuaishou":     {"requests_per_minute": 10, "cooldown_seconds": 30},
    "wechat_video": {"requests_per_minute": 3,  "cooldown_seconds": 120},
    "csv_import":   {"requests_per_minute": 999, "cooldown_seconds": 0},
}

SUPPORTED_PLATFORMS = ["douyin", "xiaohongshu", "kuaishou", "wechat_video", "csv_import"]


# ══════════════════════════════════════════════════════════════════════
# PlatformAdapterManager
# ══════════════════════════════════════════════════════════════════════

class PlatformAdapterManager:
    """平台适配器管理器 — P2 统一入口。

    职责:
    1. 模式解析: auto/mock/public → 实际模式
    2. 凭证校验: 判断是否有有效凭证
    3. Collector 创建: 路由到 Mock 或 Live 实现
    4. 速率限制: 为每个平台提供 RateLimiter
    5. 降级兜底: 凭证无效时自动降级为 Mock

    与现有架构的关系:
    - 不修改 BaseCollector / CommentRecord
    - 不修改 create_collector() 工厂函数
    - 作为 create_collector() 的上层替代入口
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
    ) -> None:
        self._config = config or load_collection_config()
        self._credentials = credentials or load_platform_credentials()
        self._rate_limiters: dict[str, RateLimiter] = {}
        self._init_rate_limiters()

    # ── 公开方法 ──

    def get_collector(
        self,
        platform: str,
        mode: str = "auto",
    ) -> BaseCollector | None:
        """获取指定平台的 Collector 实例。

        Args:
            platform: douyin | xiaohongshu | kuaishou | wechat_video
            mode: auto (默认) | mock | public

        Returns:
            BaseCollector 实例，或不支持的平台时返回 None

        Raises:
            ValueError: mode=public 但无有效凭证
        """
        if platform not in SUPPORTED_PLATFORMS:
            logger.warning("不支持的平台: %s", platform)
            return None

        resolved = self.resolve_mode(platform, mode)

        if resolved == CollectorMode.MOCK:
            return self._create_mock_collector(platform)
        elif resolved == CollectorMode.PUBLIC:
            return self._create_live_collector(platform)
        elif resolved == CollectorMode.FILE:
            return self._create_file_collector(platform)
        else:
            logger.warning("未知模式: %s", resolved)
            return self._create_mock_collector(platform)

    def resolve_mode(self, platform: str, requested: str = "auto") -> CollectorMode:
        """解析最终运行模式。

        auto:
          - csv_import/xiaohongshu → file (文件导入优先)
          - 有有效凭证 → public
          - 无凭证 → mock (降级)
        mock:
          - 始终返回 mock
        public:
          - 必须有有效凭证，否则抛出 ValueError
        file:
          - 始终返回 file
        """
        mode = CollectorMode(requested)

        if mode == CollectorMode.FILE:
            return CollectorMode.FILE

        if mode == CollectorMode.MOCK:
            return CollectorMode.MOCK

        if mode == CollectorMode.PUBLIC:
            if not self.validate_credentials(platform):
                raise ValueError(
                    f"平台 {platform} 凭证无效，无法使用 public 模式。"
                    f"请检查 platform_credentials.yml。"
                )
            return CollectorMode.PUBLIC

        # auto: 智能判断
        # csv_import / 小红书 优先文件导入
        if platform in ("csv_import", "xiaohongshu"):
            logger.info("%s: auto → file (文件导入优先)", platform)
            return CollectorMode.FILE

        if self.validate_credentials(platform):
            logger.info("%s: auto → public (凭证有效)", platform)
            return CollectorMode.PUBLIC
        else:
            logger.info("%s: auto → mock (凭证缺失，降级)", platform)
            return CollectorMode.MOCK

    def validate_credentials(self, platform: str) -> bool:
        """验证指定平台的凭证是否有效。

        P2-1 阶段仅检查格式完整性，不做真实 API 验证:
        - cookie 字段存在且非空
        - 或 api_key 字段存在且非空

        Returns:
            True: 凭证格式有效
            False: 凭证缺失或格式无效
        """
        creds = self._credentials.get(platform, {})
        if not creds or not isinstance(creds, dict):
            return False

        # 至少需要 cookie 或 api_key
        cookie = creds.get("cookie", "")
        api_key = creds.get("api_key", "")

        return bool(cookie) or bool(api_key)

    def get_rate_limiter(self, platform: str) -> RateLimiter:
        """获取平台对应的速率限制器。

        从配置读取速率参数，未配置时使用默认值。
        """
        if platform not in self._rate_limiters:
            self._init_rate_limiter(platform)
        return self._rate_limiters[platform]

    def list_available_modes(self, platform: str) -> list[str]:
        """列出平台可用的模式。

        Returns:
            可用模式列表，如 ["mock"] 或 ["mock", "public"]
        """
        modes = ["mock"]
        if platform in ("csv_import", "xiaohongshu"):
            modes.append("file")
        if self.validate_credentials(platform):
            modes.append("public")
        modes.append("auto")
        return modes

    def status(self) -> dict[str, dict[str, Any]]:
        """返回所有平台的适配器状态。

        Returns:
            {platform: {"mode_available": [...], "credentials_valid": bool, "rate_limit": {...}}}
        """
        result: dict[str, dict[str, Any]] = {}
        for p in SUPPORTED_PLATFORMS:
            result[p] = {
                "mode_available": self.list_available_modes(p),
                "credentials_valid": self.validate_credentials(p),
                "rate_limit": {
                    "requests_per_minute": self._rate_limiters[p].requests_per_minute,
                    "cooldown_seconds": self._rate_limiters[p].cooldown_seconds,
                },
                "enabled_in_config": self._is_platform_enabled(p),
            }
        return result

    # ── 内部方法 ──

    def _is_platform_enabled(self, platform: str) -> bool:
        """检查平台在 config.yml 中是否启用。"""
        platforms = self._config.get("platforms", {})
        cfg = platforms.get(platform, {})
        return cfg.get("enabled", False) if isinstance(cfg, dict) else False

    def _create_file_collector(self, platform: str) -> BaseCollector | None:
        """创建 File Collector — CSV/JSON 文件导入模式。

        适用于: 小红书手动导出、第三方工具导出的 CSV 数据。
        """
        if platform == "csv_import" or platform == "xiaohongshu":
            try:
                from csv_import_collector import CsvImportCollector  # noqa: PLC0415
                logger.info("%s: 使用 CSV Import Collector", platform)
                return CsvImportCollector()
            except ImportError:
                logger.warning("%s: CSV Import Collector 导入失败", platform)

        # 降级: 使用现有 Connector
        logger.warning("%s: file 模式不支持，降级为 mock", platform)
        return self._create_mock_collector(platform)

    def _create_mock_collector(self, platform: str) -> BaseCollector | None:
        """创建 Mock Collector — 复用现有 create_collector() 工厂。

        传入空凭证确保 mock 模式。
        """
        return _legacy_create(platform, credentials={})

    def _create_live_collector(self, platform: str) -> BaseCollector | None:
        """创建 Live Collector — 传入真实凭证。

        P2-1 阶段: 如果具体 Live Collector 类未实现，
        则降级返回 Mock Collector + 警告。
        """
        creds = self._credentials.get(platform, {})

        # 尝试使用 Live Collector
        try:
            if platform == "douyin":
                from douyin_live_collector import DouyinLiveCollector  # noqa: PLC0415
                rl = self.get_rate_limiter(platform)
                return DouyinLiveCollector(credentials=creds, rate_limiter=rl)
            elif platform == "xiaohongshu":
                from xiaohongshu_live_collector import XiaohongshuLiveCollector  # noqa: PLC0415
                rl = self.get_rate_limiter(platform)
                return XiaohongshuLiveCollector(credentials=creds, rate_limiter=rl)
            elif platform == "kuaishou":
                from kuaishou_live_collector import KuaishouLiveCollector  # noqa: PLC0415
                rl = self.get_rate_limiter(platform)
                return KuaishouLiveCollector(credentials=creds, rate_limiter=rl)
            elif platform == "wechat_video":
                from wechat_video_live_collector import WechatVideoLiveCollector  # noqa: PLC0415
                rl = self.get_rate_limiter(platform)
                return WechatVideoLiveCollector(credentials=creds, rate_limiter=rl)
        except ImportError:
            logger.warning(
                "%s: Live Collector 未实现，降级为 Mock。"
                "请先完成 P2-1 平台接入开发。",
                platform,
            )

        # 降级: 使用现有 Connector + 真实凭证
        collector = _legacy_create(platform, credentials=creds)
        if collector:
            logger.info("%s: 使用现有 Connector + public 凭证", platform)
        return collector

    def _init_rate_limiters(self) -> None:
        """初始化所有平台的速率限制器。"""
        for p in SUPPORTED_PLATFORMS:
            self._init_rate_limiter(p)

    def _init_rate_limiter(self, platform: str) -> None:
        """从配置初始化单个平台的速率限制器。"""
        defaults = DEFAULT_RATE_LIMITS.get(platform, {"requests_per_minute": 5, "cooldown_seconds": 60})

        # 从 config.yml 读取覆盖
        platforms_cfg = self._config.get("platforms", {})
        plat_cfg = platforms_cfg.get(platform, {})
        rate_cfg = plat_cfg.get("rate_limit", {}) if isinstance(plat_cfg, dict) else {}

        rpm = rate_cfg.get("requests_per_minute", defaults["requests_per_minute"])
        cd = rate_cfg.get("cooldown_seconds", defaults["cooldown_seconds"])

        self._rate_limiters[platform] = RateLimiter(
            requests_per_minute=rpm,
            cooldown_seconds=cd,
        )


# ══════════════════════════════════════════════════════════════════════
# 模块级单例 + 便捷函数
# ══════════════════════════════════════════════════════════════════════

_default_adapter: PlatformAdapterManager | None = None


def get_adapter(
    config: dict[str, Any] | None = None,
    credentials: dict[str, Any] | None = None,
) -> PlatformAdapterManager:
    """获取默认 PlatformAdapterManager 单例。"""
    global _default_adapter
    if _default_adapter is None or config is not None or credentials is not None:
        _default_adapter = PlatformAdapterManager(config=config, credentials=credentials)
    return _default_adapter


def get_collector(
    platform: str,
    mode: str = "auto",
    config: dict[str, Any] | None = None,
    credentials: dict[str, Any] | None = None,
) -> BaseCollector | None:
    """便捷函数: 一步获取 Collector。

    Args:
        platform: 平台名
        mode: auto | mock | public
        config: 采集配置 (可选)
        credentials: 平台凭证 (可选)

    Returns:
        BaseCollector 实例

    Example:
        collector = get_collector("douyin", mode="mock")
        collector.collect_and_save("acc_001", "测试账号")
    """
    adapter = get_adapter(config=config, credentials=credentials)
    return adapter.get_collector(platform, mode)


def get_platform_status() -> dict[str, dict[str, Any]]:
    """获取所有平台适配器状态（便捷函数）。"""
    return get_adapter().status()


# ══════════════════════════════════════════════════════════════════════
# CLI 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Platform Adapter Manager — 自检")
    print("=" * 60)

    adapter = PlatformAdapterManager()

    # 模式解析
    print("\n── 模式解析 ──")
    for p in SUPPORTED_PLATFORMS:
        resolved = adapter.resolve_mode(p, "auto")
        modes = adapter.list_available_modes(p)
        print(f"  {p:15s} auto→{resolved.value:6s}  可用: {modes}")

    # Collector 创建
    print("\n── Collector 创建 ──")
    for p in SUPPORTED_PLATFORMS:
        c = adapter.get_collector(p, mode="mock")
        mode_attr = getattr(c, "connector_mode", "mock") if c else "N/A"
        has_mock = hasattr(c, "_mock_collect") if c else False
        print(f"  {p:15s} Mock Collector: {'✓' if c else '✗'}  (mode={mode_attr}, has_mock={has_mock})")

    # CSV Import
    c_csv = adapter.get_collector("csv_import", mode="file")
    print(f"  csv_import       File Collector: {'✓' if c_csv else '✗'}  (mode={getattr(c_csv, 'connector_mode', 'N/A')})")

    # 速率限制
    print("\n── 速率限制 ──")
    for p in SUPPORTED_PLATFORMS:
        rl = adapter.get_rate_limiter(p)
        print(f"  {p:15s} {rl.requests_per_minute} req/min, cooldown={rl.cooldown_seconds}s")

    # 整体状态
    print("\n── 整体状态 ──")
    status = adapter.status()
    for p, s in status.items():
        cred_ok = "✓" if s["credentials_valid"] else "✗"
        enabled = "✓" if s["enabled_in_config"] else "✗"
        print(f"  {p:15s} 凭证:{cred_ok}  启用:{enabled}  可用模式:{s['mode_available']}")

    print("\n✓ Platform Adapter Manager 自检完成")
    print()
