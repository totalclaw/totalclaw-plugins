#!/usr/bin/env python3
"""DUIX Runtime 桥接层:TotalClaw Local Avatar Runtime 协议 v1 服务端。

协议规范:仓内 docs/LOCAL_RUNTIME_PROTOCOL.md。
本文件随 Runtime 镜像分发(不进插件安装包);上游 DUIX 调用点集中在
`DuixUpstream`——R-10 联调时按 pin 的 DUIX_REF 实际 API 填充。
"""
from __future__ import annotations

import argparse
import uuid
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
import uvicorn

PROTOCOL_VERSION = 1
ENGINE = "duix"

app = FastAPI(title="totalclaw-duix-runtime")
_sessions: Dict[str, Dict[str, Any]] = {}


class DuixUpstream:
    """DUIX 上游调用面(R-10 联调填充;当前为结构化未实现响应)。"""

    def start(self, avatar_id: str, voice_id: str, extra: dict) -> Dict[str, Any]:
        # TODO(R-10): 拉起/复用 DUIX 会话,返回 render(WebRTC offer 或本地页)
        raise HTTPException(501, detail={"error": "not-wired",
                            "message": "DUIX 上游接线在 Runtime 包联调阶段完成(R-10)"})

    def speak(self, upstream_ref: Any, text: str, stream: dict) -> None:
        raise HTTPException(501, detail={"error": "not-wired",
                            "message": "DUIX 上游接线在 Runtime 包联调阶段完成(R-10)"})

    def interrupt(self, upstream_ref: Any) -> None:
        raise HTTPException(501, detail={"error": "not-wired",
                            "message": "DUIX 上游接线在 Runtime 包联调阶段完成(R-10)"})

    def stop(self, upstream_ref: Any) -> None:
        pass


upstream = DuixUpstream()


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "engine": ENGINE,
            "protocol_version": PROTOCOL_VERSION, "sessions": len(_sessions)}


@app.post("/v1/sessions")
def create_session(body: Dict[str, Any]) -> Dict[str, Any]:
    ref = upstream.start(str(body.get("avatar_id", "")),
                         str(body.get("voice_id", "")),
                         dict(body.get("extra") or {}))
    session_id = uuid.uuid4().hex
    _sessions[session_id] = {"upstream": ref}
    return {"session_id": session_id, "render": ref.get("render", {})}


def _session(sid: str) -> Dict[str, Any]:
    if sid not in _sessions:
        raise HTTPException(404, detail={"error": "not-found",
                                         "message": f"会话不存在: {sid}"})
    return _sessions[sid]


@app.post("/v1/sessions/{sid}/speak")
def speak(sid: str, body: Dict[str, Any]) -> Dict[str, Any]:
    s = _session(sid)
    upstream.speak(s["upstream"], str(body.get("text", "")),
                   dict(body.get("stream") or {}))
    return {"success": True}


@app.post("/v1/sessions/{sid}/interrupt")
def interrupt(sid: str) -> Dict[str, Any]:
    s = _session(sid)
    upstream.interrupt(s["upstream"])
    return {"success": True}


@app.delete("/v1/sessions/{sid}")
def close_session(sid: str) -> Dict[str, Any]:
    s = _sessions.pop(sid, None)
    if s:
        upstream.stop(s["upstream"])
    return {"success": s is not None}


@app.get("/v1/sessions/{sid}")
def session_status(sid: str) -> Dict[str, Any]:
    _session(sid)
    return {"session_id": sid, "running": True}


@app.get("/v1/sessions")
def list_sessions() -> Dict[str, Any]:
    return {"sessions": [{"session_id": sid} for sid in _sessions]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
