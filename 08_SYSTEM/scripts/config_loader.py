"""PV_OS 配置加载器。

从 02_DATA/01_COLLECTION/config.yml 和 platform_credentials.yml 加载采集配置。

Usage::

    from config_loader import load_collection_config
    config = load_collection_config()
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "02_DATA" / "01_COLLECTION"
DEFAULT_CONFIG = CONFIG_DIR / "config.yml"
CREDENTIALS_FILE = CONFIG_DIR / "platform_credentials.yml"
CREDENTIALS_TEMPLATE = CONFIG_DIR / "platform_credentials.template.yml"


def load_yaml(path: Path) -> dict[str, Any]:
    """安全加载 YAML 文件，文件不存在时返回空字典。"""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_collection_config(config_path: Path | None = None) -> dict[str, Any]:
    """加载采集主配置。"""
    path = config_path or DEFAULT_CONFIG
    return load_yaml(path)


def load_platform_credentials() -> dict[str, Any]:
    """加载平台凭证。

    优先读取 platform_credentials.yml（不纳入版本管理），
    不存在时回退到 .template.yml 并提示配置。
    """
    if CREDENTIALS_FILE.exists():
        creds = load_yaml(CREDENTIALS_FILE)
        if creds:
            return creds

    # 回退到模板
    if CREDENTIALS_TEMPLATE.exists():
        print(f"[WARNING] 未找到 {CREDENTIALS_FILE}，使用模板。请复制模板并填写真实凭证。")
        return load_yaml(CREDENTIALS_TEMPLATE)

    return {}


def get_enabled_platforms(config: dict[str, Any] | None = None) -> list[str]:
    """返回已启用的平台列表，按优先级排序。"""
    if config is None:
        config = load_collection_config()

    platforms = config.get("platforms", {})
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

    enabled = [
        name
        for name, cfg in platforms.items()
        if isinstance(cfg, dict) and cfg.get("enabled", False)
    ]

    enabled.sort(key=lambda p: priority_order.get(
        platforms[p].get("priority", "P3"), 99
    ))
    return enabled


def get_output_dir(config: dict[str, Any] | None = None) -> Path:
    """返回采集输出根目录。"""
    if config is None:
        config = load_collection_config()
    raw_rel = config.get("output", {}).get("raw_dir", "02_DATA/raw")
    return PROJECT_ROOT / raw_rel


if __name__ == "__main__":
    # 自检
    config = load_collection_config()
    print("采集配置加载成功")
    print(f"  启用平台: {get_enabled_platforms(config)}")
    print(f"  输出目录: {get_output_dir(config)}")
