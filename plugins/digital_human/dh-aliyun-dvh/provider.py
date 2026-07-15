"""阿里云数字人(DVH,OpenAPI avatar 2022-01-30)provider 适配器。

离线合成:SubmitTextTo2D/3DAvatarVideoTask → QueryVideoTaskInfo 轮询。
实时互动:StartInstance(拿 RTC channel/token)→ SendText(StreamExtension 流式)
→ SendCommand(INTERRUPT 打断)→ StopInstance(必须显式停,平台不自动停机)。

接入依据:《阿里数字人接入方案.md》路线 A/B;SDK 字段面已对
alibabacloud_avatar20220130 实包 introspection 核实(2026-07-15)。
SDK 惰性 import(SPEC §3.3);缺包/缺凭据返回引导文案,不抛裸异常。
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional

from totalclaw_core.plugins.digital_human import (
    DigitalHumanBackendBase,
    DigitalHumanOptions,
    DigitalHumanResult,
    DigitalHumanSession,
)

from ._config import resolve

_PROVIDER = "aliyun_dvh"
_DEFAULT_ENDPOINT = "avatar.cn-zhangjiakou.aliyuncs.com"
_SDK_MISSING_MSG = (
    "阿里云数字人(DVH)需要官方 SDK —— pip install alibabacloud_avatar20220130"
)
_SENDTEXT_MAX_CHARS = 1000  # 官方单条上限

# QueryVideoTaskInfo 的 status 枚举(官方文档;联调时按实际响应复核)
_TASK_STATUS_MAP = {0: "submitted", 1: "processing", 2: "done", 3: "failed"}


def _cred(key: str, env_var: str) -> str:
    return resolve(_PROVIDER, key, env_var)


class AliyunDvhBackend(DigitalHumanBackendBase):
    """阿里云虚拟数字人(DVH)backend:离线合成 + 3D 流媒体实时互动。"""

    name = _PROVIDER
    display_name = "阿里云数字人(DVH)"
    region = "cn"
    kind = "cloud"
    modes = ("offline", "realtime")
    require_env = ()  # 凭据走 env→config 双源,可用性由 is_available 统一判定

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    # ── 凭据/可用性 ────────────────────────────────────────────────
    def _credentials(self) -> Dict[str, str]:
        return {
            "access_key_id": _cred("access_key_id", "ALIBABA_CLOUD_ACCESS_KEY_ID"),
            "access_key_secret": _cred("access_key_secret", "ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
            "tenant_id": _cred("tenant_id", "ALIYUN_AVATAR_TENANT_ID"),
            "app_id": _cred("app_id", "ALIYUN_AVATAR_APP_ID"),
        }

    def is_available(self) -> bool:
        return all(self._credentials().values())

    def unavailable_reason(self) -> str:
        missing = [k for k, v in self._credentials().items() if not v]
        if not missing:
            return ""
        return (
            f"阿里云数字人凭据未配置(缺 {', '.join(missing)})——"
            "请在 qiye-app 设置页填 AccessKey 与数字人平台的 TenantId/AppId"
        )

    def _guard(self) -> Optional[str]:
        """缺凭据时返回引导文案;可用返回 None。"""
        return self.unavailable_reason() or None

    # ── SDK client(惰性)────────────────────────────────────────────
    def _client(self):
        try:
            from alibabacloud_avatar20220130.client import Client
            from alibabacloud_tea_openapi import models as open_api_models
        except ImportError as exc:
            raise RuntimeError(_SDK_MISSING_MSG) from exc
        creds = self._credentials()
        endpoint = resolve(_PROVIDER, "endpoint", "ALIYUN_AVATAR_ENDPOINT", _DEFAULT_ENDPOINT)
        cfg = open_api_models.Config(
            access_key_id=creds["access_key_id"],
            access_key_secret=creds["access_key_secret"],
            endpoint=endpoint,
        )
        return Client(cfg)

    def _tenant_id(self) -> int:
        try:
            return int(self._credentials()["tenant_id"])
        except ValueError:
            return 0

    # ── 离线合成(路线 B)────────────────────────────────────────────
    async def synthesize(
        self, script: str, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanResult:
        opt = options or DigitalHumanOptions()
        if not script.strip():
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message="script 不能为空")
        reason = self._guard()
        if reason:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=reason)
        try:
            client = self._client()
            from alibabacloud_avatar20220130 import models as m
        except RuntimeError as exc:
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=str(exc))

        is_3d = str(opt.extra.get("avatar_type", "2d")).lower() == "3d"
        creds = self._credentials()
        common = dict(
            tenant_id=self._tenant_id(),
            text=script,
            title=str(opt.extra.get("title", "") or "totalclaw"),
        )
        try:
            if is_3d:
                req = m.SubmitTextTo3DAvatarVideoTaskRequest(
                    app=m.SubmitTextTo3DAvatarVideoTaskRequestApp(app_id=creds["app_id"]),
                    avatar_info=(m.SubmitTextTo3DAvatarVideoTaskRequestAvatarInfo(
                        code=opt.avatar_id) if opt.avatar_id else None),
                    audio_info=(m.SubmitTextTo3DAvatarVideoTaskRequestAudioInfo(
                        voice=opt.voice_id) if opt.voice_id else None),
                    **common,
                )
                resp = await asyncio.to_thread(
                    client.submit_text_to_3davatar_video_task, req)
            else:
                req = m.SubmitTextTo2DAvatarVideoTaskRequest(
                    app=m.SubmitTextTo2DAvatarVideoTaskRequestApp(app_id=creds["app_id"]),
                    avatar_info=(m.SubmitTextTo2DAvatarVideoTaskRequestAvatarInfo(
                        code=opt.avatar_id) if opt.avatar_id else None),
                    video_info=m.SubmitTextTo2DAvatarVideoTaskRequestVideoInfo(
                        is_subtitles=opt.subtitle,
                        background_image_url=opt.background or None),
                    audio_info=(m.SubmitTextTo2DAvatarVideoTaskRequestAudioInfo(
                        voice=opt.voice_id) if opt.voice_id else None),
                    **common,
                )
                resp = await asyncio.to_thread(
                    client.submit_text_to_2davatar_video_task, req)
        except Exception as exc:  # noqa: BLE001
            return DigitalHumanResult(success=False, provider=self.name,
                                      error_message=f"阿里云 DVH 合成提交失败: {exc}")

        body = getattr(resp, "body", None)
        data = getattr(body, "data", None)
        task_uuid = str(getattr(data, "task_uuid", "") or "")
        ok = bool(getattr(body, "success", False) and task_uuid)
        return DigitalHumanResult(
            success=ok,
            provider=self.name,
            task_id=task_uuid,
            status="submitted" if ok else "failed",
            error_message=None if ok else str(getattr(body, "message", "") or "未拿到 task_uuid"),
            raw=getattr(body, "to_map", lambda: {})(),
        )

    async def query_task(self, task_id: str) -> DigitalHumanResult:
        reason = self._guard()
        if reason:
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=reason)
        try:
            client = self._client()
            from alibabacloud_avatar20220130 import models as m

            req = m.QueryVideoTaskInfoRequest(
                tenant_id=self._tenant_id(),
                app=m.QueryVideoTaskInfoRequestApp(app_id=self._credentials()["app_id"]),
                task_uuid=task_id,
            )
            resp = await asyncio.to_thread(client.query_video_task_info, req)
        except Exception as exc:  # noqa: BLE001
            return DigitalHumanResult(success=False, provider=self.name,
                                      task_id=task_id, error_message=f"查询失败: {exc}")

        body = getattr(resp, "body", None)
        data = getattr(body, "data", None)
        items = list(getattr(data, "list", None) or [])
        if not items:
            return DigitalHumanResult(success=False, provider=self.name, task_id=task_id,
                                      status="failed", error_message="任务不存在",
                                      raw=getattr(body, "to_map", lambda: {})())
        item = items[0]
        try:
            status_code = int(getattr(item, "status", -1))
        except (TypeError, ValueError):
            status_code = -1
        status = _TASK_STATUS_MAP.get(status_code, "processing")
        result = getattr(item, "task_result", None)
        video_url = str(getattr(result, "video_url", "") or "")
        duration = getattr(result, "video_duration", None)
        try:
            duration_s = float(duration) if duration is not None else None
        except (TypeError, ValueError):
            duration_s = None
        if video_url and status != "failed":
            status = "done"
        return DigitalHumanResult(
            success=status == "done",
            provider=self.name,
            task_id=task_id,
            status=status,
            video_url=video_url,
            duration_s=duration_s,
            error_message=(str(getattr(result, "fail_reason", "") or "") or None)
            if status == "failed" else None,
            raw=getattr(item, "to_map", lambda: {})(),
        )

    # ── 实时互动(路线 A)────────────────────────────────────────────
    async def start_session(
        self, *, options: Optional[DigitalHumanOptions] = None,
    ) -> DigitalHumanSession:
        reason = self._guard()
        if reason:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=reason)
        opt = options or DigitalHumanOptions()
        try:
            client = self._client()
            from alibabacloud_avatar20220130 import models as m

            req = m.StartInstanceRequest(
                tenant_id=self._tenant_id(),
                app=m.StartInstanceRequestApp(app_id=self._credentials()["app_id"]),
                user=m.StartInstanceRequestUser(
                    user_id=str(opt.extra.get("user_id", "") or "totalclaw"),
                ),
                biz_id=str(opt.extra.get("biz_id", "") or uuid.uuid4().hex),
            )
            resp = await asyncio.to_thread(client.start_instance, req)
        except RuntimeError as exc:
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=str(exc))
        except Exception as exc:  # noqa: BLE001
            return DigitalHumanSession(success=False, provider=self.name,
                                       error_message=f"StartInstance 失败: {exc}")

        body = getattr(resp, "body", None)
        data = getattr(body, "data", None)
        session_id = str(getattr(data, "session_id", "") or "")
        if not (getattr(body, "success", False) and session_id):
            return DigitalHumanSession(
                success=False, provider=self.name,
                error_message=str(getattr(body, "message", "") or "未拿到 session_id"),
                raw=getattr(body, "to_map", lambda: {})(),
            )
        ch = getattr(data, "channel", None)
        render = {
            "type": "rtc",
            "app_id": str(getattr(ch, "app_id", "") or ""),
            "channel": str(getattr(ch, "channel_id", "") or ""),
            "token": str(getattr(ch, "token", "") or ""),
            "user_id": str(getattr(ch, "user_id", "") or ""),
            "gslb": getattr(ch, "gslb", None),
            "nonce": str(getattr(ch, "nonce", "") or ""),
            "expired_time": getattr(ch, "expired_time", None),
            "session_token": str(getattr(data, "token", "") or ""),
        }
        self._sessions[session_id] = {"render": render}
        return DigitalHumanSession(
            success=True, provider=self.name, session_id=session_id,
            render=render, raw=getattr(body, "to_map", lambda: {})(),
        )

    async def speak(
        self, session_id: str, text: str, *,
        stream: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        reason = self._guard()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        if len(text) > _SENDTEXT_MAX_CHARS:
            return {"success": False, "provider": self.name,
                    "error": f"SendText 单条上限 {_SENDTEXT_MAX_CHARS} 字,请上游切句后分片下发"}
        try:
            client = self._client()
            from alibabacloud_avatar20220130 import models as m

            stream = stream or {}
            ext = None
            if stream.get("is_stream"):
                ext = m.SendTextRequestStreamExtension(
                    is_stream=True,
                    index=int(stream.get("index", 0)),
                    position=str(stream.get("position", "mid")),
                )
            req = m.SendTextRequest(
                tenant_id=self._tenant_id(),
                session_id=session_id,
                text=text,
                unique_code=str(stream.get("unique_code", "") or uuid.uuid4().hex),
                stream_extension=ext,
                interrupt=stream.get("interrupt"),
            )
            resp = await asyncio.to_thread(client.send_text, req)
        except RuntimeError as exc:
            return {"success": False, "provider": self.name, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "provider": self.name, "error": f"SendText 失败: {exc}"}
        body = getattr(resp, "body", None)
        return {
            "success": bool(getattr(body, "success", False)),
            "provider": self.name,
            "session_id": session_id,
            "raw": getattr(body, "to_map", lambda: {})(),
        }

    async def interrupt(self, session_id: str) -> Dict[str, Any]:
        reason = self._guard()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        try:
            client = self._client()
            from alibabacloud_avatar20220130 import models as m

            req = m.SendCommandRequest(
                tenant_id=self._tenant_id(),
                session_id=session_id,
                code="INTERRUPT",
                unique_code=uuid.uuid4().hex,
            )
            resp = await asyncio.to_thread(client.send_command, req)
        except RuntimeError as exc:
            return {"success": False, "provider": self.name, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "provider": self.name, "error": f"打断失败: {exc}"}
        body = getattr(resp, "body", None)
        return {"success": bool(getattr(body, "success", False)),
                "provider": self.name, "session_id": session_id}

    async def stop_session(self, session_id: str) -> Dict[str, Any]:
        reason = self._guard()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        try:
            client = self._client()
            from alibabacloud_avatar20220130 import models as m

            req = m.StopInstanceRequest(tenant_id=self._tenant_id(), session_id=session_id)
            resp = await asyncio.to_thread(client.stop_instance, req)
        except RuntimeError as exc:
            return {"success": False, "provider": self.name, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "provider": self.name,
                    "error": f"StopInstance 失败: {exc}(注意:实例不停会持续计费,请重试或到控制台停)"}
        self._sessions.pop(session_id, None)
        body = getattr(resp, "body", None)
        return {"success": bool(getattr(body, "success", False)),
                "provider": self.name, "session_id": session_id}

    async def session_status(self, session_id: str) -> Dict[str, Any]:
        reason = self._guard()
        if reason:
            return {"success": False, "provider": self.name, "error": reason}
        try:
            client = self._client()
            from alibabacloud_avatar20220130 import models as m

            req = m.QueryRunningInstanceRequest(
                tenant_id=self._tenant_id(),
                app=m.QueryRunningInstanceRequestApp(
                    app_id=self._credentials()["app_id"]),
                session_id=session_id,
            )
            resp = await asyncio.to_thread(client.query_running_instance, req)
        except RuntimeError as exc:
            return {"success": False, "provider": self.name, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "provider": self.name, "error": f"查询失败: {exc}"}
        body = getattr(resp, "body", None)
        running = [str(getattr(d, "session_id", "") or "")
                   for d in (getattr(body, "data", None) or [])]
        return {
            "success": True,
            "provider": self.name,
            "session_id": session_id,
            "running": session_id in running,
            "raw": getattr(body, "to_map", lambda: {})(),
        }

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return [{"provider": self.name, "session_id": sid} for sid in self._sessions]
