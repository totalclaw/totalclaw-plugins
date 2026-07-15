"""NVIDIA ACE/Tokkio 私有化 provider 适配器。

对接用户自部署的 ACE Runtime(runtime.yaml 引用 NVIDIA 官方 NIM 分发,
不自建镜像;Runtime 包内含桥接层把 TotalClaw Local Avatar Runtime 协议 v1
翻译到 Tokkio/ACE 微服务)。适配器只说协议 v1(docs/LOCAL_RUNTIME_PROTOCOL.md)。

铁律:绝不自动拉起本地服务——endpoint 未配置即不可用。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from totalclaw_core.plugins.digital_human import (
    DigitalHumanBackendBase,
    DigitalHumanOptions,
    DigitalHumanResult,
    DigitalHumanSession,
)

from ._config import resolve

_PROVIDER = "nvidia_ace"
_ENDPOINT_ENV = "TOTALCLAW_DH_ACE_ENDPOINT"
_TIMEOUT_S = 15.0
_SPEAK_TIMEOUT_S = 30.0

_NO_ENDPOINT_MSG = (
    "NVIDIA ACE 运行时 endpoint 未配置——安装本插件后在 qiye-app 向导部署"
    "(GPU 服务器,引用 NVIDIA 官方 NIM;需 NGC 凭据),或已有部署直填 endpoint"
)


class NvidiaAceBackend(DigitalHumanBackendBase):
    """NVIDIA ACE/Tokkio backend(Local Avatar Runtime 协议 v1 薄客户端)。"""

    name = _PROVIDER
    display_name = "NVIDIA ACE/Tokkio 私有化"
    region = "local"
    kind = "selfhosted"
    modes = ("realtime",)
    require_env = ()

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _endpoint(self) -> str:
        return resolve(_PROVIDER, "endpoint", _ENDPOINT_ENV).rstrip("/")

    def is_available(self) -> bool:
        return bool(self._endpoint())

    def unavailable_reason(self) -> str:
        return "" if self.is_available() else _NO_ENDPOINT_MSG

    async def _request(self, method: str, path: str,
                       json_body: Optional[Dict[str, Any]] = None,
                       timeout: float = _TIMEOUT_S) -> Dict[str, Any]:
        ep = self._endpoint()
        if not ep:
            return {"ok": False, "data": {}, "error": _NO_ENDPOINT_MSG}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(method, f"{ep}{path}", json=json_body)
            data = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                msg = data.get("message") or data.get("error") if isinstance(data, dict) else ""
                return {"ok": False, "data": data if isinstance(data, dict) else {},
                        "error": f"ACE 运行时 HTTP {resp.status_code}: {msg or resp.text[:200]}"}
            return {"ok": True, "data": data if isinstance(data, dict) else {}, "error": ""}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "data": {},
                    "error": f"ACE 运行时连接失败({ep}): {exc}——请确认运行时已启动"}

    async def synthesize(
        self, script: str, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanResult:
        return DigitalHumanResult(
            success=False, provider=self.name, status="failed",
            error_message="nvidia_ace 仅实时互动,不支持离线合成(离线请用云厂商 provider)")

    async def start_session(
        self, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanSession:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=reason)
        opt = options or DigitalHumanOptions()
        r = await self._request("POST", "/v1/sessions", json_body={
            "avatar_id": opt.avatar_id,
            "voice_id": opt.voice_id,
            "extra": opt.extra,
        })
        if not r["ok"]:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=r["error"])
        session_id = str(r["data"].get("session_id", "") or "")
        render = r["data"].get("render") or {}
        if not session_id:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message="运行时未返回 session_id", raw=r["data"])
        self._sessions[session_id] = {"render": render}
        return DigitalHumanSession(success=True, provider=self.name,
                                   session_id=session_id, render=render, raw=r["data"])

    async def speak(
        self, session_id: str, text: str, *,
        stream: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        r = await self._request("POST", f"/v1/sessions/{session_id}/speak",
                                json_body={"text": text, "stream": stream or {}},
                                timeout=_SPEAK_TIMEOUT_S)
        return {"success": r["ok"], "provider": self.name, "session_id": session_id,
                **({"error": r["error"]} if not r["ok"] else {})}

    async def interrupt(self, session_id: str) -> Dict[str, Any]:
        r = await self._request("POST", f"/v1/sessions/{session_id}/interrupt",
                                json_body={})
        return {"success": r["ok"], "provider": self.name, "session_id": session_id,
                **({"error": r["error"]} if not r["ok"] else {})}

    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        r = await self._request("DELETE", f"/v1/sessions/{session_id}")
        self._sessions.pop(session_id, None)
        return {"success": r["ok"], "provider": self.name, "session_id": session_id,
                **({"error": r["error"]} if not r["ok"] else {})}

    async def session_status(self, session_id: str) -> Dict[str, Any]:
        r = await self._request("GET", f"/v1/sessions/{session_id}")
        if not r["ok"]:
            return {"success": False, "provider": self.name, "error": r["error"]}
        return {"success": True, "provider": self.name, "session_id": session_id,
                "running": bool(r["data"].get("running")), "raw": r["data"]}

    async def list_sessions(self) -> List[Dict[str, Any]]:
        r = await self._request("GET", "/v1/sessions")
        if r["ok"]:
            return list(r["data"].get("sessions") or [])
        return [{"provider": self.name, "session_id": sid} for sid in self._sessions]
