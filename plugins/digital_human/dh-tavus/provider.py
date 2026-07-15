"""Tavus provider 适配器:CVI 实时对话(iframe 嵌入)+ Replica 离线视频生成。

REST 直连(httpx,header x-api-key):
  实时:POST /v2/conversations → conversation_url(render type=iframe,Daily 房间)
       → POST /v2/conversations/{id}/end(必须显式停,按分钟计费)
  离线:POST /v2/videos(replica_id+script)→ GET /v2/videos/{id} 轮询

注意:CVI 是全双工音视频对话(用户语音直接进 Daily 房间,Tavus 侧 persona 可配
BYO-LLM 指向我们的 API);文本级 speak/interrupt 走 Daily Interactions Protocol
(app-message,前端桥),不在服务端 REST 面——对应方法返回结构化引导。
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

_PROVIDER = "tavus"
_BASE = "https://tavusapi.com"
_TIMEOUT_S = 30.0

_VIDEO_STATUS_MAP = {
    "queued": "submitted",
    "generating": "processing",
    "ready": "done",
    "error": "failed",
    "deleted": "failed",
}


class TavusBackend(DigitalHumanBackendBase):
    """Tavus backend:CVI 实时对话 + Replica 视频生成。"""

    name = _PROVIDER
    display_name = "Tavus CVI"
    region = "overseas"
    kind = "cloud"
    modes = ("offline", "realtime")
    require_env = ()

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _api_key(self) -> str:
        return resolve(_PROVIDER, "api_key", "TAVUS_API_KEY")

    def is_available(self) -> bool:
        return bool(self._api_key())

    def unavailable_reason(self) -> str:
        if self.is_available():
            return ""
        return "Tavus API Key 未配置——请在 qiye-app 设置页填 TAVUS_API_KEY"

    def _base(self) -> str:
        return resolve(_PROVIDER, "endpoint", "TAVUS_API_ENDPOINT", _BASE).rstrip("/")

    async def _request(self, method: str, path: str,
                       json_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                resp = await client.request(
                    method, f"{self._base()}{path}",
                    headers={"x-api-key": self._api_key(),
                             "Content-Type": "application/json"},
                    json=json_body)
            payload = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                msg = payload.get("message") if isinstance(payload, dict) else ""
                return {"ok": False, "data": {},
                        "error": f"Tavus HTTP {resp.status_code}: {msg or resp.text[:200]}"}
            return {"ok": True,
                    "data": payload if isinstance(payload, dict) else {},
                    "error": ""}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "data": {}, "error": f"Tavus 请求失败: {exc}"}

    # ── 离线视频生成(Replica)─────────────────────────────────────
    async def synthesize(
        self, script: str, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanResult:
        opt = options or DigitalHumanOptions()
        if not script.strip():
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message="script 不能为空")
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=reason)
        replica_id = opt.avatar_id or resolve(_PROVIDER, "default_replica_id")
        if not replica_id:
            return DigitalHumanResult(
                success=False, provider=self.name,
                error_message="缺 replica_id(Tavus 形象)——在 qiye-app 配默认 replica 或传 avatar_id")
        body: Dict[str, Any] = {
            "replica_id": replica_id,
            "script": script,
            "video_name": str(opt.extra.get("title", "") or "totalclaw"),
        }
        if opt.background:
            body["background_url"] = opt.background
        r = await self._request("POST", "/v2/videos", json_body=body)
        if not r["ok"]:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=r["error"])
        video_id = str(r["data"].get("video_id", "") or "")
        return DigitalHumanResult(
            success=bool(video_id), provider=self.name, task_id=video_id,
            status="submitted" if video_id else "failed",
            error_message=None if video_id else "未拿到 video_id",
            raw=r["data"],
        )

    async def query_task(self, task_id: str) -> DigitalHumanResult:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=reason)
        r = await self._request("GET", f"/v2/videos/{task_id}")
        if not r["ok"]:
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=r["error"])
        data = r["data"]
        status = _VIDEO_STATUS_MAP.get(str(data.get("status", "")).lower(), "processing")
        return DigitalHumanResult(
            success=status == "done",
            provider=self.name,
            task_id=task_id,
            status=status,
            video_url=str(data.get("download_url") or data.get("hosted_url") or ""),
            duration_s=data.get("duration"),
            error_message=str(data.get("error_message") or data.get("status_details") or "")
            or None if status == "failed" else None,
            raw=data,
        )

    async def list_avatars(self) -> List[Dict[str, Any]]:
        reason = self.unavailable_reason()
        if reason:
            return [{"success": False, "provider": self.name, "error": reason}]
        r = await self._request("GET", "/v2/replicas")
        if not r["ok"]:
            return [{"success": False, "provider": self.name, "error": r["error"]}]
        data = r["data"].get("data")
        return list(data if isinstance(data, list) else [])

    # ── 实时(CVI)────────────────────────────────────────────────
    async def start_session(
        self, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanSession:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=reason)
        opt = options or DigitalHumanOptions()
        body: Dict[str, Any] = {}
        replica_id = opt.avatar_id or resolve(_PROVIDER, "default_replica_id")
        if replica_id:
            body["replica_id"] = replica_id
        persona_id = str(opt.extra.get("persona_id", "") or resolve(_PROVIDER, "default_persona_id"))
        if persona_id:
            body["persona_id"] = persona_id
        if not body:
            return DigitalHumanSession(
                success=False, provider=self.name,
                error_message="缺 replica_id/persona_id——在 qiye-app 配置 Tavus 形象或 persona")
        greeting = str(opt.extra.get("greeting", "") or "")
        if greeting:
            body["custom_greeting"] = greeting
        max_duration = opt.extra.get("max_call_duration")
        if max_duration:
            body["properties"] = {"max_call_duration": int(max_duration)}
        r = await self._request("POST", "/v2/conversations", json_body=body)
        if not r["ok"]:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=r["error"])
        data = r["data"]
        conversation_id = str(data.get("conversation_id", "") or "")
        conversation_url = str(data.get("conversation_url", "") or "")
        if not (conversation_id and conversation_url):
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message="未拿到 conversation_id/url", raw=data)
        render = {"type": "iframe", "url": conversation_url}
        self._sessions[conversation_id] = {"render": render}
        return DigitalHumanSession(success=True, provider=self.name,
                                   session_id=conversation_id, render=render, raw=data)

    async def speak(
        self, session_id: str, text: str, *,
        stream: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "success": False, "provider": self.name, "error": "not-supported",
            "message": (
                "Tavus CVI 为全双工音视频对话:文本级驱动走 Daily Interactions Protocol"
                "(echo app-message),由 qiye 前端在 iframe/Daily 客户端侧发送;"
                "服务端 REST 无此口。BYO-LLM 请在 Tavus persona 配置指向我们的 API。"
            ),
        }

    async def interrupt(self, session_id: str) -> Dict[str, Any]:
        return {
            "success": False, "provider": self.name, "error": "not-supported",
            "message": "打断走前端 Daily Interactions Protocol(interrupt app-message),服务端 REST 无此口",
        }

    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        reason = self.unavailable_reason()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        r = await self._request("POST", f"/v2/conversations/{session_id}/end")
        self._sessions.pop(session_id, None)
        return {"success": r["ok"], "provider": self.name, "session_id": session_id,
                **({"error": r["error"] + "(会话按分钟计费,失败请到 Tavus 控制台确认已结束)"}
                   if not r["ok"] else {})}

    async def session_status(self, session_id: str) -> Dict[str, Any]:
        reason = self.unavailable_reason()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        r = await self._request("GET", f"/v2/conversations/{session_id}")
        if not r["ok"]:
            return {"success": False, "provider": self.name, "error": r["error"]}
        status = str(r["data"].get("status", "")).lower()
        return {"success": True, "provider": self.name, "session_id": session_id,
                "running": status == "active", "status": status, "raw": r["data"]}

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return [{"provider": self.name, "session_id": sid} for sid in self._sessions]
