"""腾讯云智能数智人(IVH)provider 适配器。

腾讯云标准 API(TC3-HMAC-SHA256 签名,stdlib hmac/hashlib 实现,零厂商 SDK):
  离线合成:SubmitVideoMakeJob → DescribeVideoMakeJob 轮询(action 名与字段
  以商务开白后的官方文档为准——action/字段名全部集中在模块常量与 config
  `digital_human.providers.tencent_ivh.actions` 可覆盖,签名器与调用链路不变)。
  实时互动:数智人实时会话族随开白文档接线(方法已就位,当前返回结构化引导)。

商务开白状态:未开白——签名/调用/映射链路已完成并可配,实测与 action 核准
在开白后进行(PLUGINS_REPO_TODO R-7)。
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional

import httpx

from totalclaw_core.plugins.digital_human import (
    DigitalHumanBackendBase,
    DigitalHumanOptions,
    DigitalHumanResult,
    DigitalHumanSession,
)

from ._config import provider_block, resolve

_PROVIDER = "tencent_ivh"
_DEFAULT_HOST = "ivh.tencentcloudapi.com"
_DEFAULT_SERVICE = "ivh"
_DEFAULT_VERSION = "2023-07-30"
_DEFAULT_REGION = ""  # 数智人 API 多数 action 不分地域;需要时 config 覆盖
_TIMEOUT_S = 30.0

# ── action 面(开白后按官方文档核准;config actions.* 可覆盖,无须改代码)──
_ACTIONS_DEFAULT = {
    "submit_video": "SubmitVideoMakeJob",
    "query_video": "DescribeVideoMakeJob",
}

_PENDING_REALTIME_MSG = (
    "腾讯数智人实时互动待商务开白后按开放平台文档接线(签名与调用链路已就位;"
    "action 名可在 config digital_human.providers.tencent_ivh.actions 配置)"
)

# 任务状态 → 契约 status(开白联调时按实际枚举复核)
_VIDEO_STATUS_MAP = {
    "waiting": "submitted",
    "pending": "submitted",
    "making": "processing",
    "processing": "processing",
    "success": "done",
    "finished": "done",
    "fail": "failed",
    "failed": "failed",
}


def _tc3_sign(secret_id: str, secret_key: str, host: str, service: str,
              action: str, version: str, payload: str, region: str = "") -> Dict[str, str]:
    """腾讯云 TC3-HMAC-SHA256 签名(官方规范逐步实现),返回完整请求头。"""
    timestamp = int(time.time())
    date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))

    hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_headers = (f"content-type:application/json; charset=utf-8\n"
                         f"host:{host}\nx-tc-action:{action.lower()}\n")
    signed_headers = "content-type;host;x-tc-action"
    canonical_request = (f"POST\n/\n\n{canonical_headers}\n"
                         f"{signed_headers}\n{hashed_payload}")

    credential_scope = f"{date}/{service}/tc3_request"
    string_to_sign = (f"TC3-HMAC-SHA256\n{timestamp}\n{credential_scope}\n"
                      f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}")

    def _hmac(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _hmac(f"TC3{secret_key}".encode("utf-8"), date)
    k_service = _hmac(k_date, service)
    k_signing = _hmac(k_service, "tc3_request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"),
                         hashlib.sha256).hexdigest()

    headers = {
        "Authorization": (
            f"TC3-HMAC-SHA256 Credential={secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"),
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Version": version,
        "X-TC-Timestamp": str(timestamp),
    }
    if region:
        headers["X-TC-Region"] = region
    return headers


class TencentIvhBackend(DigitalHumanBackendBase):
    """腾讯云智能数智人(IVH)backend。"""

    name = _PROVIDER
    display_name = "腾讯云智能数智人(IVH)"
    region = "cn"
    kind = "cloud"
    modes = ("offline", "realtime")
    require_env = ()

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    # ── 凭据/可用性 ────────────────────────────────────────────────
    def _credentials(self) -> Dict[str, str]:
        return {
            "secret_id": resolve(_PROVIDER, "secret_id", "TENCENTCLOUD_SECRET_ID"),
            "secret_key": resolve(_PROVIDER, "secret_key", "TENCENTCLOUD_SECRET_KEY"),
        }

    def is_available(self) -> bool:
        return all(self._credentials().values())

    def unavailable_reason(self) -> str:
        missing = [k for k, v in self._credentials().items() if not v]
        if not missing:
            return ""
        return (f"腾讯云凭据未配置(缺 {', '.join(missing)})——"
                "请在 qiye-app 设置页填 SecretId/SecretKey(数智人需商务开白)")

    def _action(self, key: str) -> str:
        actions = provider_block(_PROVIDER).get("actions") or {}
        return str(actions.get(key) or _ACTIONS_DEFAULT.get(key, ""))

    async def _call(self, action_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """签名并调用一个云 API action;返回 {"ok","data","error"} 信封。"""
        action = self._action(action_key)
        if not action:
            return {"ok": False, "data": {}, "error": f"未知 action: {action_key}"}
        creds = self._credentials()
        host = resolve(_PROVIDER, "host", "TENCENT_IVH_HOST", _DEFAULT_HOST)
        service = resolve(_PROVIDER, "service", "", _DEFAULT_SERVICE)
        version = resolve(_PROVIDER, "version", "", _DEFAULT_VERSION)
        region = resolve(_PROVIDER, "region", "", _DEFAULT_REGION)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        headers = await asyncio.to_thread(
            _tc3_sign, creds["secret_id"], creds["secret_key"],
            host, service, action, version, body, region)
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
                resp = await client.post(f"https://{host}/", content=body.encode("utf-8"),
                                         headers=headers)
            data = resp.json() if resp.content else {}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "data": {}, "error": f"腾讯云请求失败: {exc}"}
        response = data.get("Response") if isinstance(data, dict) else None
        response = response if isinstance(response, dict) else {}
        err = response.get("Error")
        if err:
            code = err.get("Code", "")
            msg = err.get("Message", "")
            hint = ""
            if "AuthFailure" in str(code) or "Unsupported" in str(code):
                hint = "(数智人 API 需商务开白;action/版本名以开白后官方文档为准)"
            return {"ok": False, "data": response,
                    "error": f"腾讯云 {code}: {msg}{hint}"}
        return {"ok": True, "data": response, "error": ""}

    # ── 离线合成 ──────────────────────────────────────────────────
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
        payload: Dict[str, Any] = {
            "Text": script,
            "VirtualmanKey": opt.avatar_id or resolve(_PROVIDER, "default_virtualman_key"),
        }
        if opt.voice_id:
            payload["TimbreKey"] = opt.voice_id
        if opt.extra.get("driver_type"):
            payload["DriverType"] = opt.extra["driver_type"]
        r = await self._call("submit_video", payload)
        if not r["ok"]:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=r["error"])
        task_id = str(r["data"].get("JobId") or r["data"].get("TaskId") or "")
        return DigitalHumanResult(
            success=bool(task_id), provider=self.name, task_id=task_id,
            status="submitted" if task_id else "failed",
            error_message=None if task_id else "未拿到任务 ID(字段名随开白文档核准)",
            raw=r["data"],
        )

    async def query_task(self, task_id: str) -> DigitalHumanResult:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=reason)
        r = await self._call("query_video", {"JobId": task_id})
        if not r["ok"]:
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=r["error"])
        data = r["data"]
        raw_status = str(data.get("Status") or data.get("JobStatus") or "").lower()
        status = _VIDEO_STATUS_MAP.get(raw_status, "processing")
        video_url = str(data.get("VideoUrl") or data.get("MediaUrl") or "")
        if video_url and status != "failed":
            status = "done"
        return DigitalHumanResult(
            success=status == "done",
            provider=self.name, task_id=task_id, status=status,
            video_url=video_url,
            error_message=(str(data.get("ErrorMsg") or "") or None)
            if status == "failed" else None,
            raw=data,
        )

    # ── 实时互动(开白后接线;链路占位返回结构化引导)────────────────
    async def start_session(
        self, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanSession:
        reason = self.unavailable_reason()
        if reason:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=reason)
        return DigitalHumanSession(success=False, provider=self.name,
                                   error_message=_PENDING_REALTIME_MSG)

    async def speak(
        self, session_id: str, text: str, *,
        stream: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {"success": False, "provider": self.name,
                "error": "pending-verify", "message": _PENDING_REALTIME_MSG}

    async def interrupt(self, session_id: str) -> Dict[str, Any]:
        return {"success": False, "provider": self.name,
                "error": "pending-verify", "message": _PENDING_REALTIME_MSG}

    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        return {"success": False, "provider": self.name,
                "error": "pending-verify", "message": _PENDING_REALTIME_MSG}

    async def session_status(self, session_id: str) -> Dict[str, Any]:
        return {"success": False, "provider": self.name,
                "error": "pending-verify", "message": _PENDING_REALTIME_MSG}

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return [{"provider": self.name, "session_id": sid} for sid in self._sessions]
