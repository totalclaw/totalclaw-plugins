"""TopView provider 适配器:离线数字人口播(Video Avatar)。

REST 直连(httpx,无厂商 SDK),接口依据 TopView OpenAPI(apifox 中/英文版,2026-10 核对):
  POST /v1/video_avatar/task/submit → GET /v1/video_avatar/task/query 轮询
  GET  /v1/aiavatar/query(公模/私模列表)
鉴权两个头:Authorization: Bearer <API Key> + Topview-Uid;信封 {code:"200", message, result}。

只做离线:TopView 没有实时流式数字人接口。商品链接一键出带货视频(m2v)不属于数字人
契约(synthesize 只有 script),由 totalclaw-mcp 的 topview MCP 服务器提供。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from totalclaw_core.plugins.digital_human import (
    DigitalHumanBackendBase,
    DigitalHumanOptions,
    DigitalHumanResult,
)

from ._config import resolve

_PROVIDER = "topview"
_BASE = "https://api.topview.ai"
_TIMEOUT_S = 30.0

# task/query 的 status(文档:init/running/success/fail)→ 契约 status
_STATUS_MAP = {
    "init": "submitted",
    "running": "processing",
    "success": "done",
    "fail": "failed",
    "failed": "failed",
}

# extra.mode → modeType;avatar1 只改口型(不支持图片),avatar2/4 以首帧驱动动作
_MODES = {"avatar1": 0, "avatar2": 1, "avatar4": 2, "avatar4_fast": 3}

# 业务码 → 人话(官方错误码表节选)
_CODES = {
    "4004": "资源不存在(avatar_id / fileId / taskId 不对)",
    "4007": "已有未完成的任务,请等上一个任务结束",
    "4100": "积分不足,请到 topview.ai 充值",
    "5003": "TopView 服务繁忙,请稍后重试",
    "6001": "内容触发安全审核",
}


class TopviewBackend(DigitalHumanBackendBase):
    """TopView backend:脚本 → 数字人口播视频(离线)。"""

    name = _PROVIDER
    display_name = "TopView 数字人口播"
    region = "overseas"
    kind = "cloud"
    modes = ("offline",)
    require_env = ()

    # ── 凭据(env 优先,config digital_human.providers.topview 兜底)──
    def _api_key(self) -> str:
        return resolve(_PROVIDER, "api_key", "TOPVIEW_API_KEY")

    def _uid(self) -> str:
        return resolve(_PROVIDER, "uid", "TOPVIEW_UID")

    def is_available(self) -> bool:
        return bool(self._api_key() and self._uid())

    def unavailable_reason(self) -> str:
        if self.is_available():
            return ""
        missing = [n for n, v in (("TOPVIEW_API_KEY", self._api_key()),
                                  ("TOPVIEW_UID", self._uid())) if not v]
        reason = (f"TopView 凭据未配置——请在 ~/.totalclaw/.env 填 {'、'.join(missing)}"
                  "(www.topview.ai/api-settings,旧版 API 仅 Pro / Business 会员可开通)")
        # 新版 API Router 与旧版余额、Key 互不相通,且只有生图生视频模型、没有数字人
        if resolve(_PROVIDER, "platform_key", "TOPVIEW_API_PLATFORM_KEY"):
            reason += (";已配置的 TOPVIEW_API_PLATFORM_KEY 属于新版 API Router,"
                       "它没有数字人模型,数字人口播只能用旧版 API")
        return reason

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key()}",
                "Topview-Uid": self._uid(), "Content-Type": "application/json"}

    async def _request(self, method: str, path: str,
                       json_body: Optional[Dict[str, Any]] = None,
                       params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """统一 HTTP;返回 {"ok","data","error"} 信封,不抛异常。

        TopView 失败时常是 HTTP 200 + code!="200",必须拆信封判定。
        """
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                resp = await client.request(method, f"{_BASE}{path}",
                                            headers=self._headers(),
                                            json=json_body, params=params)
            if resp.status_code in (401, 403):
                return {"ok": False, "data": {},
                        "error": "TopView 鉴权失败——API Key 或 UID 不对,请到 API Settings 重新复制"}
            if resp.status_code >= 400:
                return {"ok": False, "data": {},
                        "error": f"TopView HTTP {resp.status_code}: {resp.text[:200]}"}
            payload = resp.json() if resp.content else {}
            code = str(payload.get("code", "")) if isinstance(payload, dict) else ""
            if code != "200":
                msg = payload.get("message", "") if isinstance(payload, dict) else ""
                hint = _CODES.get(code, "")
                return {"ok": False, "data": {},
                        "error": f"TopView 错误 code={code}: {msg} {hint}".strip()}
            result = payload.get("result")
            return {"ok": True, "data": result if isinstance(result, dict) else {"result": result},
                    "error": ""}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "data": {}, "error": f"TopView 请求失败: {type(exc).__name__}"}

    # ── 离线合成 ──────────────────────────────────────────────────
    async def synthesize(
        self, script: str, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanResult:
        opt = options or DigitalHumanOptions()
        extra = opt.extra or {}
        audio_file_id = str(extra.get("audio_file_id", "") or "")
        if not script.strip() and not audio_file_id:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message="script 不能为空")
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=reason)
        if opt.audio_url and not audio_file_id:
            return DigitalHumanResult(
                success=False, provider=self.name,
                error_message="TopView 不收音频 URL——先用 topview MCP 的 upload_file 上传,"
                              "再把 fileId 放进 options.extra.audio_file_id")

        image_file_id = str(extra.get("image_file_id", "") or "")
        video_file_id = str(extra.get("video_file_id", "") or "")
        avatar_id = opt.avatar_id or resolve(_PROVIDER, "default_avatar_id")
        if image_file_id:
            avatar_from = 3
        elif video_file_id:
            avatar_from = 0
        elif avatar_id:
            avatar_from = 2 if extra.get("custom_avatar") else 1
        else:
            return DigitalHumanResult(
                success=False, provider=self.name,
                error_message="缺 avatar_id——用 list_avatars 选形象,或在 qiye-app 配默认形象"
                              "(也可在 options.extra 给 image_file_id / video_file_id)")

        mode = str(extra.get("mode", "") or resolve(_PROVIDER, "default_mode", default="avatar1"))
        if mode not in _MODES:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=f"extra.mode 只能是 {', '.join(_MODES)}")
        if avatar_from == 3 and mode == "avatar1":
            mode = "avatar2"  # avatar1 不支持图片输入,自动升到以首帧驱动的 avatar2

        voice_id = opt.voice_id or resolve(_PROVIDER, "default_voice_id")
        use_tts = not audio_file_id
        # 公模 + TTS 可不传音色(用数字人默认音色);其余 TTS 组合必须有音色
        if use_tts and not voice_id and avatar_from != 1:
            return DigitalHumanResult(
                success=False, provider=self.name,
                error_message="私模/图片/视频驱动配合文本时必须给 voice_id(TopView Voice Query 可查)")

        try:
            speed = min(max(float(extra.get("voice_speed", 1.0)), 0.8), 1.2)
        except (TypeError, ValueError):
            speed = 1.0
        body: Dict[str, Any] = {
            "avatarSourceFrom": avatar_from,
            "audioSourceFrom": 1 if use_tts else 0,
            "modeType": _MODES[mode],
            "voiceSpeed": speed,
        }
        if avatar_from in (1, 2):
            body["aiAvatarId"] = avatar_id
        if image_file_id:
            body["imageFileId"] = image_file_id
        if video_file_id:
            body["videoFileId"] = video_file_id
        if use_tts:
            body["ttsText"] = script
            if voice_id:
                body["voiceoverId"] = voice_id
        else:
            body["audioFileId"] = audio_file_id
        caption_id = str(extra.get("caption_id", "") or resolve(_PROVIDER, "default_caption_id"))
        if opt.subtitle and caption_id and avatar_from == 1:  # 字幕暂只支持公模
            body["captionId"] = caption_id

        r = await self._request("POST", "/v1/video_avatar/task/submit", json_body=body)
        if not r["ok"]:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=r["error"])
        task_id = str(r["data"].get("taskId", "") or "")
        return DigitalHumanResult(
            success=bool(task_id), provider=self.name, task_id=task_id,
            status="submitted" if task_id else "failed",
            error_message=None if task_id else "未拿到 taskId",
            raw=r["data"],
        )

    async def query_task(self, task_id: str) -> DigitalHumanResult:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=reason)
        r = await self._request("GET", "/v1/video_avatar/task/query",
                                params={"taskId": task_id, "needCloudFrontUrl": "true"})
        if not r["ok"]:
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=r["error"])
        data = r["data"]
        status = _STATUS_MAP.get(str(data.get("status", "")).lower(), "processing")
        video_url = str(data.get("outputVideoUrl", "") or "")
        # 完成判定以 video_url 为权威:状态写 success 但还没出 URL 时仍算处理中
        if status == "done" and not video_url:
            status = "processing"
        err = data.get("errorMsg")
        cost = data.get("costCredit")
        return DigitalHumanResult(
            success=status == "done",
            provider=self.name,
            task_id=task_id,
            status=status,
            video_url=video_url,
            cost=float(cost) if isinstance(cost, (int, float)) else None,
            error_message=(str(err) if err else "任务失败") if status == "failed" else None,
            raw=data,
        )

    async def list_avatars(self) -> List[Dict[str, Any]]:
        reason = self.unavailable_reason()
        if reason:
            return [{"success": False, "provider": self.name, "error": reason}]
        r = await self._request("GET", "/v1/aiavatar/query",
                                params={"pageNo": 1, "pageSize": 50})
        if not r["ok"]:
            return [{"success": False, "provider": self.name, "error": r["error"]}]
        return [
            {k: a.get(k) for k in ("aiavatarId", "aiavatarName", "gender", "coverUrl",
                                   "previewVideoUrl", "voiceoverIdDefault")}
            for a in (r["data"].get("data") or []) if isinstance(a, dict)
        ]

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return []
