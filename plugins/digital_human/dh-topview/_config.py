"""provider 配置解析(自包含,不依赖 agent 内部模块)。

优先级与 agent 既有三级一致(DIGITAL_HUMAN_PROVIDER_CONFIG.md §4):
os.environ → config.yaml `digital_human.providers.<provider>` 子块 → 默认值。
config.yaml 读取失败(缺文件/缺 PyYAML/格式坏)一律静默降级为 env-only。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


def _totalclaw_home() -> Path:
    env = os.environ.get("TOTALCLAW_HOME")
    return Path(env) if env else Path.home() / ".totalclaw"


def provider_block(provider: str) -> Dict[str, Any]:
    """读 `digital_human.providers.<provider>` 子块;任何异常返回 {}。"""
    path = _totalclaw_home() / "config.yaml"
    try:
        import yaml  # agent 运行环境必有;缺失则降级 env-only

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        block = raw.get("digital_human") or {}
        providers = block.get("providers") or {}
        sub = providers.get(provider)
        return sub if isinstance(sub, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def resolve(provider: str, key: str, env_var: str = "", default: str = "") -> str:
    """单值解析:env(若给了 env_var)→ config 子块 → default。返回 str。"""
    if env_var:
        v = os.environ.get(env_var)
        if v:
            return v
    v = provider_block(provider).get(key)
    if v is None or v == "":
        return default
    return str(v)
