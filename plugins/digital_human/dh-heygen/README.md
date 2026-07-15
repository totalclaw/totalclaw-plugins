# HeyGen LiveAvatar

HeyGen:实时 LiveAvatar(WebRTC/iframe)与离线视频生成,按分钟计费

- provider 名:`heygen` · 区域:`overseas` · 类型:`cloud` · 形态:`['offline', 'realtime']`
- 状态:**已实现(REST 直连 httpx,零厂商 SDK;真实 key 实测待账号)**

## 能力

- 离线:`synthesize`(POST /v2/video/generate,avatar_id 必填,可 `list_avatars` 拿)→ `query_task`(/v1/video_status.get)
- 实时:`start_session`(streaming.new+start,render type=rtc/livekit,前端 livekit-client 拉流)→ `speak`(streaming.task task_type=repeat,原样播报我们 LLM 文本=BYO-LLM)→ `interrupt`/`stop_session`(**按分钟计费,必须显式停**)

## 凭据/配置

- `HEYGEN_API_KEY`:HeyGen API Key


凭据解析优先级(与 agent 既有一致):环境变量 → config `digital_human.providers.heygen`。
装完默认不启用:`totalclaw plugins enable dh-heygen` 或在 qiye-app 设置页开启。
