"""PV_OS Own Account Registry — 自有账号管理 V1.0。

实现 PV_OS_ACCOUNT_MODEL_V3.md §二 Own Account:
    管理 PV_OS 自身运营的视频平台账号，用于 Inbound 评论采集和内容发布。

存储: 02_DATA/02_COMPETITOR_DATABASE/own_account_master.csv

Usage::

    from own_account_registry import OwnAccount, OwnAccountRegistry

    registry = OwnAccountRegistry()
    registry.register(OwnAccount(
        account_id="own_001",
        platform="douyin",
        platform_account_id="dy_own_001",
        account_name="成都光伏小马哥",
        account_url="https://douyin.com/user/dy_own_001",
    ))
    all_own = registry.list_all()
"""

from __future__ import annotations

import csv
import logging
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
OWN_ACCOUNT_CSV = PROJECT_ROOT / "02_DATA" / "02_COMPETITOR_DATABASE" / "own_account_master.csv"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

logger = logging.getLogger(__name__)
TZ_SHANGHAI = timezone(timedelta(hours=8))

OWN_ACCOUNT_CSV_FIELDS = [
    "account_id", "platform", "platform_account_id",
    "account_name", "account_url",
    "monitor_comments", "content_frequency",
    "primary_topic", "description",
    "region", "contact_email",
    "status", "registered_at", "updated_at",
]


@dataclass
class OwnAccount:
    """自有账号数据模型 — 对标 PV_OS_ACCOUNT_MODEL_V3.md §二.3。

    用途: 内容发布 + Inbound评论采集。
    """

    # ── 核心标识 ──
    account_id: str = ""
    platform: str = ""              # douyin | xiaohongshu | kuaishou | shipinhao
    platform_account_id: str = ""   # 平台账号唯一ID
    account_name: str = ""
    account_url: str = ""

    # ── 监控配置 ──
    monitor_comments: bool = True   # 是否监控该账号评论
    content_frequency: str = ""     # 发布频率: daily/weekly/biweekly

    # ── 内容方向 ──
    primary_topic: str = ""         # 主要内容方向
    description: str = ""

    # ── 地理 ──
    region: str = "四川"            # 账号IP所属区域

    # ── 联系 ──
    contact_email: str = ""

    # ── 状态 ──
    status: str = "active"          # active | paused | deprecated
    registered_at: str = field(default_factory=lambda: datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S"))
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OwnAccount":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    @classmethod
    def from_row(cls, row: list[str], field_names: list[str]) -> "OwnAccount":
        d = dict(zip(field_names, row))
        return cls.from_dict(d)

    def to_row(self) -> list[str]:
        return [str(self.to_dict().get(f, "")) for f in OWN_ACCOUNT_CSV_FIELDS]

    def get_platform_account_ids(self) -> set[str]:
        """返回用于匹配的平台账号ID集合。"""
        ids = {self.platform_account_id}
        if self.account_url:
            ids.add(self.account_url)
        return ids


class OwnAccountRegistry:
    """自有账号注册表。

    存储: 02_DATA/02_COMPETITOR_DATABASE/own_account_master.csv
    """

    def __init__(self, csv_path: Path | None = None) -> None:
        self.csv_path = csv_path or OWN_ACCOUNT_CSV
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

    # ── CRUD ──

    def register(self, account: OwnAccount) -> None:
        """注册新自有账号。按 account_id 去重。"""
        if not account.updated_at:
            account.updated_at = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")
        existing = self._read_all()
        data_rows = existing[1:] if len(existing) > 1 else []
        existing_dict: dict[str, list[str]] = {r[0]: r for r in data_rows}
        existing_dict[account.account_id] = account.to_row()
        self._write_all(list(existing_dict.values()))
        logger.info("OwnAccountRegistry: 注册 %s (%s)", account.account_id, account.account_name)

    def get(self, account_id: str) -> OwnAccount | None:
        """获取单个自有账号。"""
        rows = self._read_all()
        if len(rows) <= 1:
            return None
        for row in rows[1:]:
            if row[0] == account_id:
                return OwnAccount.from_row(row, OWN_ACCOUNT_CSV_FIELDS)
        return None

    def list_all(self) -> list[OwnAccount]:
        """列出所有自有账号。"""
        results: list[OwnAccount] = []
        rows = self._read_all()
        if len(rows) <= 1:
            return results
        for row in rows[1:]:
            results.append(OwnAccount.from_row(row, OWN_ACCOUNT_CSV_FIELDS))
        return results

    def list_active(self) -> list[OwnAccount]:
        """列出 active 状态的自有账号。"""
        return [a for a in self.list_all() if a.status == "active"]

    def list_by_platform(self, platform: str) -> list[OwnAccount]:
        """按平台筛选自有账号。"""
        return [a for a in self.list_all() if a.platform == platform]

    def update(self, account_id: str, **kwargs: Any) -> bool:
        """更新自有账号字段。"""
        account = self.get(account_id)
        if account is None:
            logger.warning("OwnAccountRegistry: 账号 %s 不存在", account_id)
            return False
        for k, v in kwargs.items():
            if hasattr(account, k):
                setattr(account, k, v)
        account.updated_at = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")
        self.register(account)  # save 覆盖
        return True

    def delete(self, account_id: str) -> bool:
        """标记账号为 deprecated。"""
        return self.update(account_id, status="deprecated")

    def is_own_account(self, platform_account_id: str, account_url: str = "") -> bool:
        """判断是否为自有账号 (用于 CommentRecord.is_own_account 标记)。"""
        for a in self.list_active():
            if platform_account_id and platform_account_id == a.platform_account_id:
                return True
            if account_url and account_url == a.account_url:
                return True
        return False

    def get_matching_account_ids(self) -> set[str]:
        """获取所有用于匹配的标识符集合。"""
        ids: set[str] = set()
        for a in self.list_active():
            ids.update(a.get_platform_account_ids())
        return ids

    def count(self) -> int:
        rows = self._read_all()
        return len(rows) - 1 if len(rows) > 0 else 0

    def count_active(self) -> int:
        return len(self.list_active())

    # ── 内部 ──

    def _read_all(self) -> list[list[str]]:
        if not self.csv_path.exists():
            return [OWN_ACCOUNT_CSV_FIELDS]
        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        # 兼容旧表头
        if rows and rows[0] != OWN_ACCOUNT_CSV_FIELDS:
            logger.info("OwnAccountRegistry: 重建表头")
            return [OWN_ACCOUNT_CSV_FIELDS]
        return rows

    def _write_all(self, rows: list[list[str]]) -> None:
        rows.sort(key=lambda r: r[0])
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(OWN_ACCOUNT_CSV_FIELDS)
            w.writerows(rows)


# ══════════════════════════════════════════════════════════════════════
# 快速创建函数
# ══════════════════════════════════════════════════════════════════════

def create_default_own_accounts() -> list[OwnAccount]:
    """创建默认自有账号列表，用于测试和引导。

    注意: 这些是 Mock 数据，仅用于 Phase 2C 测试。
    正式运营前需要替换为真实账号信息。
    """
    now = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d %H:%M:%S")
    return [
        OwnAccount(
            account_id="own_douyin_001",
            platform="douyin",
            platform_account_id="dy_own_chengdu_solar",
            account_name="成都光伏小马哥",
            account_url="https://douyin.com/user/dy_own_chengdu_solar",
            monitor_comments=True,
            content_frequency="daily",
            primary_topic="城市家庭光伏安装案例",
            description="四川成都本地IP，专注别墅/叠拼/阳光房光伏",
            region="四川",
            registered_at=now,
            updated_at=now,
        ),
        OwnAccount(
            account_id="own_xhs_001",
            platform="xiaohongshu",
            platform_account_id="xhs_own_chengdu_solar",
            account_name="成都光伏小马哥",
            account_url="https://xiaohongshu.com/user/xhs_own_chengdu_solar",
            monitor_comments=True,
            content_frequency="weekly",
            primary_topic="光伏生活美学",
            description="小红书自有账号，展示光伏案例",
            region="四川",
            registered_at=now,
            updated_at=now,
        ),
        OwnAccount(
            account_id="own_douyin_002",
            platform="douyin",
            platform_account_id="dy_own_pv_knowledge",
            account_name="光伏知识科普",
            account_url="https://douyin.com/user/dy_own_pv_knowledge",
            monitor_comments=False,
            content_frequency="weekly",
            primary_topic="光伏知识科普",
            description="知识科普号，不监控评论",
            region="四川",
            registered_at=now,
            updated_at=now,
        ),
    ]


# ══════════════════════════════════════════════════════════════════════
# 自检
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile, os

    print("=" * 60)
    print("  Own Account Registry — 自检")
    print("=" * 60)

    tmp = Path(tempfile.mkdtemp()) / "test_own_account.csv"
    registry = OwnAccountRegistry(csv_path=tmp)

    # 注册
    accounts = create_default_own_accounts()
    for acct in accounts:
        registry.register(acct)
    print(f"  注册: {registry.count()} 个自有账号")
    assert registry.count() == 3
    assert registry.count_active() == 3

    # 查询
    a = registry.get("own_douyin_001")
    assert a is not None
    assert a.platform == "douyin"
    assert a.account_name == "成都光伏小马哥"
    print(f"  查询: {a.account_name} ({a.platform})")

    # 按平台筛选
    douyin_accounts = registry.list_by_platform("douyin")
    assert len(douyin_accounts) == 2
    print(f"  抖音自有账号: {len(douyin_accounts)}")

    # is_own_account 判断
    assert registry.is_own_account("dy_own_chengdu_solar")
    assert registry.is_own_account("", "https://douyin.com/user/dy_own_chengdu_solar")
    assert not registry.is_own_account("unknown_competitor")
    print(f"  is_own_account: ✓")

    # 更新
    registry.update("own_douyin_001", content_frequency="weekly")
    a2 = registry.get("own_douyin_001")
    assert a2 is not None and a2.content_frequency == "weekly"
    print(f"  更新: content_frequency = {a2.content_frequency}")

    # 删除
    registry.delete("own_douyin_002")
    assert registry.count_active() == 2
    print(f"  delete: active count = {registry.count_active()}")

    # CSV 持久化
    registry2 = OwnAccountRegistry(csv_path=tmp)
    assert registry2.count() == 3
    print(f"  持久化: {registry2.count()} 条记录")

    tmp.unlink(missing_ok=True)

    print("\n✓ Own Account Registry 自检完成\n")
