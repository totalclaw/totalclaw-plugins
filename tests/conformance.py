#!/usr/bin/env python3
"""插件契约符合性测试(SPEC §4 机检)。

对 plugins/digital_human/ 下每个插件(_TEMPLATE 除外),在"零配置"环境
(TOTALCLAW_HOME 指向空目录 + 厂商 env 全清)验证:

  1. 包可导入(顶层零厂商 SDK 依赖——惰性 import 铁律)
  2. register(ctx) 恰好注册 1 个 backend,provider 名 = 目录名去 dh- 前缀转下划线
  3. 元数据合法:region∈{cn,overseas,local},kind∈{cloud,selfhosted},
     modes⊆{offline,realtime} 且非空,describe() 可用
  4. 零配置时 is_available()=False 且 unavailable_reason() 非空(配置引导)
  5. 全接口族(synthesize/query_task/start_session/speak/interrupt/stop_session/
     session_status/list_sessions)零配置调用不抛裸异常,返回结构化信封
  6. register 零副作用:注册前后无网络/无进程(以"零配置即时返回"近似机检)

默认用内置契约影子(与 agent totalclaw_core.plugins.digital_human 公开面同构,
快照自 v0.63.72 core_body.py);设 TOTALCLAW_AGENT_PATH 则改挂真实 agent 契约。

用法:python3 tests/conformance.py    退出码 0=全过
"""
from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "plugins" / "digital_human"

VALID_REGIONS = {"cn", "overseas", "local"}
VALID_KINDS = {"cloud", "selfhosted"}
VALID_MODES = {"offline", "realtime"}

# 零配置环境要清掉的厂商/配置 env 前缀
_ENV_PREFIXES = ("ALIBABA_CLOUD_", "ALIYUN_", "TENCENTCLOUD_", "TENCENT_IVH_",
                 "HEYGEN_", "TAVUS_", "TOTALCLAW_DH_", "TOTALCLAW_DIGITAL_HUMAN")

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# 契约影子(与 agent core_body.py 公开面同构;真实 agent 在场时不用)
# ---------------------------------------------------------------------------

def _install_contract_stub() -> types.ModuleType:
    import abc
    from dataclasses import dataclass, field
    from typing import Any, Dict, List, Optional

    dh = types.ModuleType("totalclaw_core.plugins.digital_human")

    @dataclass
    class DigitalHumanOptions:
        avatar_id: str = ""
        voice_id: str = ""
        aspect_ratio: str = "9:16"
        resolution: str = "1080p"
        background: str = ""
        subtitle: bool = True
        audio_url: str = ""
        extra: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class DigitalHumanResult:
        success: bool
        provider: str
        task_id: str = ""
        video_url: str = ""
        duration_s: Optional[float] = None
        status: str = ""
        cost: Optional[float] = None
        error_message: Optional[str] = None
        raw: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class DigitalHumanSession:
        success: bool
        provider: str
        session_id: str = ""
        render: Dict[str, Any] = field(default_factory=dict)
        error_message: Optional[str] = None
        raw: Dict[str, Any] = field(default_factory=dict)

    class DigitalHumanBackendBase(abc.ABC):
        name = "abstract"
        require_env: tuple = ()
        default_timeout_s = 900.0
        region = "cn"
        kind = "cloud"
        modes: tuple = ("offline",)
        display_name = ""

        def is_available(self) -> bool:
            if not self.require_env:
                return True
            return all(os.environ.get(v) for v in self.require_env)

        def unavailable_reason(self) -> str:
            if self.is_available():
                return ""
            missing = [v for v in self.require_env if not os.environ.get(v)]
            return f"凭据未配置(需 {', '.join(missing)})" if missing else "未配置"

        def supports_mode(self, mode: str) -> bool:
            return mode in tuple(self.modes or ())

        def describe(self) -> Dict[str, Any]:
            return {
                "name": self.name,
                "display_name": self.display_name or self.name,
                "region": self.region,
                "kind": self.kind,
                "modes": list(self.modes or ()),
                "is_available": self.is_available(),
                "unavailable_reason": self.unavailable_reason(),
            }

        async def start_session(self, *, options=None) -> "DigitalHumanSession":
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message="not-supported")

        async def speak(self, session_id, text, *, stream=None) -> Dict[str, Any]:
            return {"success": False, "provider": self.name, "error": "not-supported"}

        async def interrupt(self, session_id) -> Dict[str, Any]:
            return {"success": False, "provider": self.name, "error": "not-supported"}

        async def stop_session(self, session_id) -> Dict[str, Any]:
            return {"success": False, "provider": self.name, "error": "not-supported"}

        async def session_status(self, session_id) -> Dict[str, Any]:
            return {"success": False, "provider": self.name, "error": "not-supported"}

        async def list_sessions(self) -> List[Dict[str, Any]]:
            return []

        @abc.abstractmethod
        async def synthesize(self, script, *, options=None) -> "DigitalHumanResult":
            ...

        async def query_task(self, task_id) -> "DigitalHumanResult":
            raise NotImplementedError

        async def list_avatars(self) -> List[Dict[str, Any]]:
            raise NotImplementedError

    _registry: dict = {}

    def register_backend(b) -> None:
        if not getattr(b, "name", None):
            raise ValueError("backend 必须设置 name")
        _registry[b.name] = b

    def get_backend(name):
        return _registry.get(name)

    def list_backends():
        return sorted(_registry)

    def clear_registry():
        _registry.clear()

    for obj in (DigitalHumanOptions, DigitalHumanResult, DigitalHumanSession,
                DigitalHumanBackendBase):
        setattr(dh, obj.__name__, obj)
    dh.register_backend = register_backend
    dh.get_backend = get_backend
    dh.list_backends = list_backends
    dh.clear_registry = clear_registry

    core = types.ModuleType("totalclaw_core")
    plugins = types.ModuleType("totalclaw_core.plugins")
    core.plugins = plugins
    plugins.digital_human = dh
    sys.modules["totalclaw_core"] = core
    sys.modules["totalclaw_core.plugins"] = plugins
    sys.modules["totalclaw_core.plugins.digital_human"] = dh
    return dh


def _contract():
    agent_path = os.environ.get("TOTALCLAW_AGENT_PATH")
    if agent_path:
        sys.path.insert(0, agent_path)
        import totalclaw_core.plugins.digital_human as dh
        print(f"契约:真实 agent({agent_path})")
        return dh
    print("契约:内置影子(快照 v0.63.72;设 TOTALCLAW_AGENT_PATH 可挂真实 agent)")
    return _install_contract_stub()


# ---------------------------------------------------------------------------
# 逐插件检查
# ---------------------------------------------------------------------------

def _load_plugin(plugin_dir: Path):
    mod_name = plugin_dir.name.replace("-", "_")
    spec = importlib.util.spec_from_file_location(
        mod_name, plugin_dir / "__init__.py",
        submodule_search_locations=[str(plugin_dir)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _expected_provider(plugin_name: str) -> str:
    return plugin_name.removeprefix("dh-").replace("-", "_")


def check_plugin(plugin_dir: Path, dh) -> None:
    name = plugin_dir.name
    expected = _expected_provider(name)
    dh.clear_registry()
    try:
        mod = _load_plugin(plugin_dir)
    except Exception as exc:  # noqa: BLE001
        fail(f"{name}: 导入失败(顶层禁厂商 SDK): {exc}")
        return
    ctx = types.SimpleNamespace(logger=logging.getLogger("conformance"),
                                config={})
    try:
        mod.register(ctx)
    except Exception as exc:  # noqa: BLE001
        fail(f"{name}: register(ctx) 抛异常: {exc}")
        return
    registered = dh.list_backends()
    if registered != [expected]:
        fail(f"{name}: 注册结果 {registered},期望 ['{expected}']")
        return
    b = dh.get_backend(expected)

    # 元数据
    if b.region not in VALID_REGIONS:
        fail(f"{name}: region={b.region!r} 非法")
    if b.kind not in VALID_KINDS:
        fail(f"{name}: kind={b.kind!r} 非法")
    modes = set(b.modes or ())
    if not modes or not modes <= VALID_MODES:
        fail(f"{name}: modes={b.modes!r} 非法")
    try:
        d = b.describe()
        assert d["name"] == expected
    except Exception as exc:  # noqa: BLE001
        fail(f"{name}: describe() 异常: {exc}")

    # 零配置:不可用 + 引导文案
    try:
        if b.is_available():
            fail(f"{name}: 零配置下 is_available() 应为 False")
        elif not b.unavailable_reason():
            fail(f"{name}: 不可用但 unavailable_reason() 为空(缺配置引导)")
    except Exception as exc:  # noqa: BLE001
        fail(f"{name}: is_available/unavailable_reason 异常: {exc}")

    # 全接口族:零配置调用必须优雅返回
    async def _exercise():
        r = await b.synthesize("测试文本")
        assert hasattr(r, "success") and r.success is False, "synthesize 应失败并带引导"
        assert getattr(r, "error_message", None), "synthesize 失败须带 error_message"
        r2 = await b.synthesize("")
        assert r2.success is False, "空 script 应失败"
        try:
            q = await b.query_task("fake-task-id")
            assert q.success is False
        except NotImplementedError:
            pass  # 契约允许:不支持 query_task 的 provider
        s = await b.start_session()
        assert s.success is False and s.error_message, "start_session 零配置须失败+引导"
        for meth, args in (("speak", ("sid", "hi")), ("interrupt", ("sid",)),
                           ("stop_session", ("sid",)), ("session_status", ("sid",))):
            out = await getattr(b, meth)(*args)
            assert isinstance(out, dict) and "success" in out, f"{meth} 须返回结构化信封"
        ls = await b.list_sessions()
        assert isinstance(ls, list)

    try:
        asyncio.run(_exercise())
    except AssertionError as exc:
        fail(f"{name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        fail(f"{name}: 接口族零配置调用抛裸异常: {type(exc).__name__}: {exc}")


def main() -> None:
    # 零配置环境:清厂商 env + 空 TOTALCLAW_HOME
    for key in list(os.environ):
        if key.startswith(_ENV_PREFIXES):
            del os.environ[key]
    tmp_home = tempfile.mkdtemp(prefix="totalclaw-conformance-")
    os.environ["TOTALCLAW_HOME"] = tmp_home

    dh = _contract()
    plugin_dirs = sorted(d for d in PLUGINS_DIR.iterdir()
                         if d.is_dir() and d.name != "_TEMPLATE")
    for plugin_dir in plugin_dirs:
        check_plugin(plugin_dir, dh)
        print(f"ok    {plugin_dir.name}" if not any(
            f.startswith(plugin_dir.name + ":") for f in failures)
            else f"bad   {plugin_dir.name}")

    if failures:
        print(f"\n符合性未过:{len(failures)} 项 FAIL({len(plugin_dirs)} 个插件)",
              file=sys.stderr)
        raise SystemExit(1)
    print(f"\n符合性通过:{len(plugin_dirs)} 个插件全接口族零配置调用无裸异常")


if __name__ == "__main__":
    main()
