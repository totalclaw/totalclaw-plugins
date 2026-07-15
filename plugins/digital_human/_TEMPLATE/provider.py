"""CHANGEME provider 适配器(薄客户端,零重依赖)。

自包含铁律(SPEC.md §3):只 import totalclaw_core.plugins.digital_human 契约面 +
标准库/httpx;厂商 SDK 惰性 import(方法内)且缺包给引导文案;重运行时永不进插件。
契约方法全为 async;缺凭据/缺配置一律返回引导文案信封,禁止抛裸异常
(机检:python3 tests/conformance.py)。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from totalclaw_core.plugins.digital_human import (
    DigitalHumanBackendBase,
    DigitalHumanOptions,
    DigitalHumanResult,
    DigitalHumanSession,
)

from ._config import resolve

_PROVIDER = "changeme"


class ChangeMeBackend(DigitalHumanBackendBase):
    """CHANGEME backend。"""

    name = _PROVIDER
    display_name = "CHANGEME"
    region = "cn"              # cn / overseas / local(私有化)
    kind = "cloud"             # cloud / selfhosted
    modes = ("offline",)       # ("offline",) 和/或 ("realtime",)
    require_env = ()           # 凭据走 env→config 双源时留空,用 is_available 统一判定

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    # ── 凭据/可用性(env 优先,config digital_human.providers.<name> 兜底)──
    def _api_key(self) -> str:
        return resolve(_PROVIDER, "api_key", "CHANGEME_API_KEY")

    def is_available(self) -> bool:
        return bool(self._api_key())

    def unavailable_reason(self) -> str:
        if self.is_available():
            return ""
        return "CHANGEME 凭据未配置——请在 qiye-app 设置页填 CHANGEME_API_KEY"

    # ── 离线合成(不支持则返回引导,勿抛异常)────────────────────────
    async def synthesize(
        self, script: str, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanResult:
        if not script.strip():
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message="script 不能为空")
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=reason)
        # TODO: 提交厂商合成任务,返回 task_id/status=submitted
        return DigitalHumanResult(success=False, provider=self.name, status="failed",
                                  error_message="CHANGEME synthesize 未实现")

    async def query_task(self, task_id: str) -> DigitalHumanResult:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=reason)
        # TODO: 轮询任务;done 时带 video_url
        return DigitalHumanResult(success=False, provider=self.name, task_id=task_id,
                                  error_message="CHANGEME query_task 未实现")

    # ── 实时接口族(不支持的档位删掉这些覆盖,基类默认返回 not-supported)──
    async def start_session(
        self, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanSession:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=reason)
        # TODO: 开会话,render 按契约五型(rtc/iframe/webgl/video_url/virtual_camera)
        return DigitalHumanSession(success=False, provider=self.name,
                                   error_message="CHANGEME start_session 未实现")

    async def speak(
        self, session_id: str, text: str, *,
        stream: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        reason = self.unavailable_reason()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        return {"success": False, "provider": self.name,
                "error": "CHANGEME speak 未实现"}

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return [{"provider": self.name, "session_id": sid} for sid in self._sessions]
