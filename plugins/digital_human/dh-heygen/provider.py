"""HeyGen provider 适配器:离线视频生成 + Interactive/LiveAvatar 实时(WebRTC)。

REST 直连(httpx,无厂商 SDK):
  离线:POST /v2/video/generate → GET /v1/video_status.get 轮询
  实时:POST /v1/streaming.new(拿 LiveKit url/token)→ streaming.start →
       streaming.task(task_type=repeat,BYO-LLM 纯文本驱动)→ streaming.interrupt
       → streaming.stop(按分钟计费,必须显式停)
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

_PROVIDER = "heygen"
_BASE = "https://api.heygen.com"
_TIMEOUT_S = 30.0

# video_status.get 状态 → 契约 status
_VIDEO_STATUS_MAP = {
    "pending": "submitted",
    "waiting": "processing",
    "processing": "processing",
    "completed": "done",
    "failed": "failed",
}

# 分辨率/比例 → 像素(HeyGen dimension 参数)
_DIMENSIONS = {
    ("9:16", "1080p"): (1080, 1920),
    ("9:16", "720p"): (720, 1280),
    ("16:9", "1080p"): (1920, 1080),
    ("16:9", "720p"): (1280, 720),
}


class HeygenBackend(DigitalHumanBackendBase):
    """HeyGen backend:视频生成 + LiveAvatar 实时互动。"""

    name = _PROVIDER
    display_name = "HeyGen LiveAvatar"
    region = "overseas"
    kind = "cloud"
    modes = ("offline", "realtime")
    require_env = ()

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    # ── 凭据 ─────────────────────────────────────────────────────
    def _api_key(self) -> str:
        return resolve(_PROVIDER, "api_key", "HEYGEN_API_KEY")

    def is_available(self) -> bool:
        return bool(self._api_key())

    def unavailable_reason(self) -> str:
        if self.is_available():
            return ""
        return "HeyGen API Key 未配置——请在 qiye-app 设置页填 HEYGEN_API_KEY"

    def _base(self) -> str:
        return resolve(_PROVIDER, "endpoint", "HEYGEN_API_ENDPOINT", _BASE).rstrip("/")

    def _headers(self) -> Dict[str, str]:
        return {"X-Api-Key": self._api_key(), "Content-Type": "application/json"}

    async def _request(self, method: str, path: str,
                       json_body: Optional[Dict[str, Any]] = None,
                       params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一 HTTP;返回 {"ok","data","error"} 信封,不抛异常。"""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                resp = await client.request(method, f"{self._base()}{path}",
                                            headers=self._headers(),
                                            json=json_body, params=params)
            payload = resp.json() if resp.content else {}
            if resp.status_code >= 400:
                msg = ""
                if isinstance(payload, dict):
                    err = payload.get("error") or payload.get("message") or payload
                    msg = err.get("message") if isinstance(err, dict) else str(err)
                return {"ok": False, "data": {},
                        "error": f"HeyGen HTTP {resp.status_code}: {msg or resp.text[:200]}"}
            data = payload.get("data") if isinstance(payload, dict) else None
            return {"ok": True, "data": data if isinstance(data, dict) else (payload or {}),
                    "error": ""}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "data": {}, "error": f"HeyGen 请求失败: {exc}"}

    # ── 离线视频生成 ──────────────────────────────────────────────
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
        avatar_id = opt.avatar_id or resolve(_PROVIDER, "default_avatar_id")
        if not avatar_id:
            return DigitalHumanResult(
                success=False, provider=self.name,
                error_message="缺 avatar_id——用 list_avatars 选形象,或在 qiye-app 配默认形象")
        width, height = _DIMENSIONS.get(
            (opt.aspect_ratio, opt.resolution), _DIMENSIONS[("9:16", "1080p")])
        voice: Dict[str, Any] = {"type": "text", "input_text": script}
        voice_id = opt.voice_id or resolve(_PROVIDER, "default_voice_id")
        if voice_id:
            voice["voice_id"] = voice_id
        body: Dict[str, Any] = {
            "video_inputs": [{
                "character": {"type": "avatar", "avatar_id": avatar_id,
                              "avatar_style": "normal"},
                "voice": voice,
                **({"background": {"type": "image", "url": opt.background}}
                   if opt.background else {}),
            }],
            "dimension": {"width": width, "height": height},
            "caption": bool(opt.subtitle),
        }
        r = await self._request("POST", "/v2/video/generate", json_body=body)
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
        r = await self._request("GET", "/v1/video_status.get",
                                params={"video_id": task_id})
        if not r["ok"]:
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=r["error"])
        data = r["data"]
        status = _VIDEO_STATUS_MAP.get(str(data.get("status", "")).lower(), "processing")
        err = data.get("error")
        return DigitalHumanResult(
            success=status == "done",
            provider=self.name,
            task_id=task_id,
            status=status,
            video_url=str(data.get("video_url", "") or ""),
            duration_s=data.get("duration"),
            error_message=(str(err) if err else None) if status == "failed" else None,
            raw=data,
        )

    async def list_avatars(self) -> List[Dict[str, Any]]:
        reason = self.unavailable_reason()
        if reason:
            return [{"success": False, "provider": self.name, "error": reason}]
        r = await self._request("GET", "/v2/avatars")
        if not r["ok"]:
            return [{"success": False, "provider": self.name, "error": r["error"]}]
        return list(r["data"].get("avatars") or [])

    # ── 实时(Interactive Avatar / LiveAvatar)─────────────────────
    async def start_session(
        self, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanSession:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=reason)
        opt = options or DigitalHumanOptions()
        body: Dict[str, Any] = {
            "quality": str(opt.extra.get("quality", "") or "high"),
        }
        avatar_id = opt.avatar_id or resolve(_PROVIDER, "default_streaming_avatar_id")
        if avatar_id:
            body["avatar_id"] = avatar_id
        voice_id = opt.voice_id or resolve(_PROVIDER, "default_voice_id")
        if voice_id:
            body["voice"] = {"voice_id": voice_id}
        r = await self._request("POST", "/v1/streaming.new", json_body=body)
        if not r["ok"]:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=r["error"])
        data = r["data"]
        session_id = str(data.get("session_id", "") or "")
        if not session_id:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message="未拿到 session_id", raw=data)
        started = await self._request("POST", "/v1/streaming.start",
                                      json_body={"session_id": session_id})
        if not started["ok"]:
            await self._request("POST", "/v1/streaming.stop",
                                json_body={"session_id": session_id})
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=started["error"], raw=data)
        render = {
            "type": "rtc",
            "protocol": "livekit",
            "url": str(data.get("url", "") or ""),
            "token": str(data.get("access_token", "") or ""),
        }
        self._sessions[session_id] = {"render": render}
        return DigitalHumanSession(success=True, provider=self.name,
                                   session_id=session_id, render=render, raw=data)

    async def speak(
        self, session_id: str, text: str, *,
        stream: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        reason = self.unavailable_reason()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        # task_type=repeat:数字人只当嘴和脸,原样播报我们 LLM 的文本(BYO-LLM)
        r = await self._request("POST", "/v1/streaming.task", json_body={
            "session_id": session_id,
            "text": text,
            "task_type": "repeat",
            "task_mode": "async",
        })
        return {"success": r["ok"], "provider": self.name, "session_id": session_id,
                **({"error": r["error"]} if not r["ok"] else {"raw": r["data"]})}

    async def interrupt(self, session_id: str) -> Dict[str, Any]:
        reason = self.unavailable_reason()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        r = await self._request("POST", "/v1/streaming.interrupt",
                                json_body={"session_id": session_id})
        return {"success": r["ok"], "provider": self.name, "session_id": session_id,
                **({"error": r["error"]} if not r["ok"] else {})}

    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        reason = self.unavailable_reason()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        r = await self._request("POST", "/v1/streaming.stop",
                                json_body={"session_id": session_id})
        self._sessions.pop(session_id, None)
        return {"success": r["ok"], "provider": self.name, "session_id": session_id,
                **({"error": r["error"] + "(实时会话按分钟计费,失败请到 HeyGen 控制台确认已停)"}
                   if not r["ok"] else {})}

    async def session_status(self, session_id: str) -> Dict[str, Any]:
        reason = self.unavailable_reason()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        r = await self._request("GET", "/v1/streaming.list")
        if not r["ok"]:
            return {"success": False, "provider": self.name, "error": r["error"]}
        sessions = list(r["data"].get("sessions") or [])
        hit = next((s for s in sessions
                    if str(s.get("session_id")) == session_id), None)
        return {"success": True, "provider": self.name, "session_id": session_id,
                "running": hit is not None, "raw": hit or {}}

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return [{"provider": self.name, "session_id": sid} for sid in self._sessions]
