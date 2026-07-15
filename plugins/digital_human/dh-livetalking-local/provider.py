"""LiveTalking 私有化(GPU 高保真档)provider 适配器。

直接对接 LiveTalking(lipku/LiveTalking,musetalk/wav2lip)原生 HTTP 面
(该项目 API 稳定且社区标准,不再包桥接层):
  WebRTC 协商:前端 POST {endpoint}/offer(SDP;render type=rtc,协商由前端完成,
  offer 响应含 sessionid,前端拿到后回传给 speak/status 使用)
  文本驱动:POST /human {sessionid, type:"echo", text}(echo=原样播报,BYO-LLM)
  打断:POST /human {sessionid, type:"echo", text:"", interrupt:true}
  (部分部署版本为独立 /interrupt_talk——config interrupt_path 可覆盖)
  状态:POST /is_speaking {sessionid}

RTMP/虚拟摄像头输出:LiveTalking 启动参数 --transport rtmp/virtualcam 决定,
属 Runtime 部署配置(runtime.yaml deploy 选项),直播层对接见 agent A-18。
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

_PROVIDER = "livetalking_local"
_ENDPOINT_ENV = "TOTALCLAW_DH_LIVETALKING_ENDPOINT"
_TIMEOUT_S = 15.0
_SPEAK_TIMEOUT_S = 30.0

_NO_ENDPOINT_MSG = (
    "LiveTalking 运行时 endpoint 未配置——安装本插件后在 qiye-app 向导部署"
    "(需 NVIDIA GPU;远程 GPU 服务器场景选『远程部署包』),或已有部署直填 endpoint"
)


def _to_sessionid(session_id: str):
    """LiveTalking 的 sessionid 是整数(单路默认 0);容忍字符串透传。"""
    try:
        return int(session_id)
    except (TypeError, ValueError):
        return session_id


class LivetalkingLocalBackend(DigitalHumanBackendBase):
    """LiveTalking backend(原生 HTTP 薄客户端)。"""

    name = _PROVIDER
    display_name = "LiveTalking 私有化(GPU 高保真档)"
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

    async def _post(self, path: str, json_body: Dict[str, Any],
                    timeout: float = _TIMEOUT_S) -> Dict[str, Any]:
        ep = self._endpoint()
        if not ep:
            return {"ok": False, "data": {}, "error": _NO_ENDPOINT_MSG}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{ep}{path}", json=json_body)
            try:
                data = resp.json() if resp.content else {}
            except ValueError:
                data = {"raw_text": resp.text[:200]}
            if resp.status_code >= 400:
                return {"ok": False, "data": data,
                        "error": f"LiveTalking HTTP {resp.status_code}: {resp.text[:200]}"}
            # LiveTalking 惯例:{"code":0,...} 为成功
            code = data.get("code") if isinstance(data, dict) else None
            if code not in (None, 0):
                return {"ok": False, "data": data,
                        "error": f"LiveTalking code={code}: {data.get('msg') or data}"}
            return {"ok": True, "data": data if isinstance(data, dict) else {}, "error": ""}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "data": {},
                    "error": f"LiveTalking 连接失败({ep}): {exc}——请确认运行时已启动(GPU 服务器)"}

    async def synthesize(
        self, script: str, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanResult:
        return DigitalHumanResult(
            success=False, provider=self.name, status="failed",
            error_message="livetalking_local 仅实时互动,不支持离线合成(离线请用云厂商 provider)")

    # ── 实时 ─────────────────────────────────────────────────────
    async def start_session(
        self, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanSession:
        """LiveTalking 会话在 WebRTC /offer 协商时诞生(前端完成)。

        这里做可达性探测并下发 offer_url;前端从 /offer 响应拿 sessionid,
        后续 speak/session_status 用它。单路默认部署 sessionid=0。
        """
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=reason)
        ep = self._endpoint()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.get(ep + "/")  # 探活:任何 HTTP 响应都算服务在
        except Exception as exc:  # noqa: BLE001
            return DigitalHumanSession(
                success=False, provider=self.name,
                error_message=f"LiveTalking 不可达({ep}): {exc}")
        opt = options or DigitalHumanOptions()
        default_sid = str(opt.extra.get("sessionid", "0"))
        render = {
            "type": "rtc",
            "protocol": "webrtc-offer",
            "offer_url": f"{ep}/offer",
            "note": "前端 POST SDP offer 到 offer_url 完成协商;响应含 sessionid",
        }
        self._sessions[default_sid] = {"render": render}
        return DigitalHumanSession(success=True, provider=self.name,
                                   session_id=default_sid, render=render)

    async def speak(
        self, session_id: str, text: str, *,
        stream: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        stream = stream or {}
        r = await self._post("/human", {
            "sessionid": _to_sessionid(session_id),
            "type": "echo",  # echo=原样播报我们 LLM 的文本
            "text": text,
            "interrupt": bool(stream.get("interrupt", False)),
        }, timeout=_SPEAK_TIMEOUT_S)
        return {"success": r["ok"], "provider": self.name, "session_id": session_id,
                **({"error": r["error"]} if not r["ok"] else {})}

    async def interrupt(self, session_id: str) -> Dict[str, Any]:
        # 默认走 /human 空文本 + interrupt;部署版本若有独立打断口,config interrupt_path 覆盖
        path = resolve(_PROVIDER, "interrupt_path", "", "/human")
        body: Dict[str, Any] = {"sessionid": _to_sessionid(session_id)}
        if path == "/human":
            body.update({"type": "echo", "text": "", "interrupt": True})
        r = await self._post(path, body)
        return {"success": r["ok"], "provider": self.name, "session_id": session_id,
                **({"error": r["error"]} if not r["ok"] else {})}

    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        # LiveTalking 无服务端关会话 REST:连接随前端 WebRTC 断开释放
        self._sessions.pop(str(session_id), None)
        return {"success": True, "provider": self.name, "session_id": session_id,
                "note": "LiveTalking 会话随前端 WebRTC 断开释放;本地运行时无按分钟计费"}

    async def session_status(self, session_id: str) -> Dict[str, Any]:
        r = await self._post("/is_speaking", {"sessionid": _to_sessionid(session_id)})
        if not r["ok"]:
            return {"success": False, "provider": self.name, "error": r["error"]}
        return {"success": True, "provider": self.name, "session_id": session_id,
                "running": True, "speaking": bool(r["data"].get("data")),
                "raw": r["data"]}

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return [{"provider": self.name, "session_id": sid} for sid in self._sessions]
