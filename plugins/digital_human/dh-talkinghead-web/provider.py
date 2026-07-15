"""TalkingHead 浏览器渲染 provider:渲染完全在 qiye-app 前端 WebGL。

met4citizen/TalkingHead:Ready Player Me 3D 形象(glb)+ 前端 TTS/口型驱动,
服务端零 GPU、零进程——本 provider 只产出**渲染资产清单与 TTS 桥配置**
(render type=webgl),speak 返回给前端的播报指令信封,不做任何服务端网络调用。

配置(config `digital_human.providers.talkinghead_web`):
  enabled: true            # 打开即可用(无凭据、无 endpoint)
  avatar_url: "...glb"     # Ready Player Me 形象;缺省用公开示例形象
  tts: {...}               # 前端 TTS 桥配置(引擎/voice/语速),原样透传
  lipsync_lang: "en"       # 口型语言模块(en/fi/...;中文场景配 en 近似)
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from totalclaw_core.plugins.digital_human import (
    DigitalHumanBackendBase,
    DigitalHumanOptions,
    DigitalHumanResult,
    DigitalHumanSession,
)

from ._config import provider_block, resolve

_PROVIDER = "talkinghead_web"
# TalkingHead 官方 README 的示例形象(Ready Player Me,公开 CDN)
_DEFAULT_AVATAR_URL = "https://models.readyplayer.me/64bfa15f0e72c63d7c3934a6.glb"

_DISABLED_MSG = (
    "talkinghead_web 未启用——在 qiye-app 设置页打开"
    "(config digital_human.providers.talkinghead_web.enabled: true;"
    "可选配置 Ready Player Me 形象 avatar_url 与 TTS 桥)"
)


class TalkingheadWebBackend(DigitalHumanBackendBase):
    """TalkingHead 前端 WebGL 渲染 backend(服务端零依赖)。"""

    name = _PROVIDER
    display_name = "TalkingHead 浏览器渲染(海外轻量档)"
    region = "local"
    kind = "selfhosted"
    modes = ("realtime",)
    require_env = ()

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _enabled(self) -> bool:
        block = provider_block(_PROVIDER)
        return bool(block.get("enabled"))

    def is_available(self) -> bool:
        return self._enabled()

    def unavailable_reason(self) -> str:
        return "" if self.is_available() else _DISABLED_MSG

    def _render(self, opt: DigitalHumanOptions) -> Dict[str, Any]:
        block = provider_block(_PROVIDER)
        avatar_url = (opt.avatar_id
                      or resolve(_PROVIDER, "avatar_url")
                      or _DEFAULT_AVATAR_URL)
        tts = block.get("tts") if isinstance(block.get("tts"), dict) else {}
        return {
            "type": "webgl",
            "lib": "talkinghead",
            "avatar_url": avatar_url,
            "tts": tts,
            "lipsync_lang": str(block.get("lipsync_lang") or "en"),
            "mood": str(opt.extra.get("mood", "") or block.get("mood") or "neutral"),
        }

    async def synthesize(
        self, script: str, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanResult:
        return DigitalHumanResult(
            success=False, provider=self.name, status="failed",
            error_message="talkinghead_web 为前端实时渲染,不支持离线视频合成(离线请用云厂商 provider)")

    async def start_session(
        self, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanSession:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=reason)
        opt = options or DigitalHumanOptions()
        session_id = uuid.uuid4().hex
        render = self._render(opt)
        self._sessions[session_id] = {"render": render}
        return DigitalHumanSession(success=True, provider=self.name,
                                   session_id=session_id, render=render)

    async def speak(
        self, session_id: str, text: str, *,
        stream: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        reason = self.unavailable_reason()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        if session_id not in self._sessions:
            return {"success": False, "provider": self.name,
                    "error": f"会话不存在: {session_id}(先 start_session)"}
        # 渲染在前端:speak 产出前端指令信封,由 qiye 组件驱动 TalkingHead.speakText
        return {
            "success": True,
            "provider": self.name,
            "session_id": session_id,
            "directive": {"op": "speak", "text": text, "stream": stream or {}},
        }

    async def interrupt(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self._sessions:
            return {"success": False, "provider": self.name,
                    "error": f"会话不存在: {session_id}"}
        return {"success": True, "provider": self.name, "session_id": session_id,
                "directive": {"op": "interrupt"}}

    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        existed = self._sessions.pop(session_id, None) is not None
        return {"success": existed, "provider": self.name, "session_id": session_id,
                **({} if existed else {"error": f"会话不存在: {session_id}"})}

    async def session_status(self, session_id: str) -> Dict[str, Any]:
        return {"success": True, "provider": self.name, "session_id": session_id,
                "running": session_id in self._sessions}

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return [{"provider": self.name, "session_id": sid} for sid in self._sessions]
