# TopView 数字人口播

TopView(topview.ai):脚本 → 数字人口播视频(离线),按积分计费

- provider 名:`topview` · 区域:`overseas` · 类型:`cloud` · 形态:`['offline']`
- 状态:**已实现(REST 直连 httpx,零厂商 SDK;真实 key 实测待账号)**

## 能力

- 离线:`synthesize`(POST /v1/video_avatar/task/submit)→ `query_task`(GET /v1/video_avatar/task/query,
  `status=success` 且有 `outputVideoUrl` 才算完成)
- `list_avatars`:公模列表(GET /v1/aiavatar/query),拿 `aiavatarId` 填 `options.avatar_id`
- 实时:**不支持**(TopView 无实时流式数字人接口),实时请用 dh-heygen / dh-tavus / dh-aliyun-dvh

### options 映射

| 契约字段 | TopView |
|---|---|
| `avatar_id` | `aiAvatarId`(公模;私模加 `extra.custom_avatar=true`) |
| `voice_id` | `voiceoverId`;公模可不填,用数字人默认音色 |
| `subtitle` | 配了 `extra.caption_id` 或默认字幕样式时带 `captionId`(TopView 暂只支持公模字幕) |
| `extra.image_file_id` / `extra.video_file_id` | 用一张人像图 / 一段人像视频驱动(需先上传拿 fileId) |
| `extra.audio_file_id` | 用已上传的音频替代 TTS |
| `extra.mode` | `avatar1`(默认,只改口型)/ `avatar2` / `avatar4` / `avatar4_fast`;图片输入自动升到 avatar2 |
| `extra.voice_speed` | 0.8–1.2 |
| `aspect_ratio` / `resolution` / `background` | TopView 该接口不支持,忽略 |

素材上传(人像图、音频)与**商品链接一键出带货视频**不属于数字人契约,由 totalclaw-mcp 的
`topview` MCP 服务器提供(`upload_file` / `create_marketing_video`):`totalclaw mcp install topview`。

## 凭据/配置

TopView 有两套互不相通的 API(余额、Key 都不通用),**数字人只在旧版 API 里**:

| | 旧版 API(本插件使用) | 新版 API Router |
|---|---|---|
| 凭据 | `TOPVIEW_API_KEY` + `TOPVIEW_UID` | `TOPVIEW_API_PLATFORM_KEY` |
| 开通 | www.topview.ai/api-settings,仅 Pro / Business 会员 | platform.topview.ai → API 密钥,免费账号可开,美元余额计费 |
| 数字人 | 有(Video Avatar、公模库) | 没有,只有生图生视频模型 |

只配了新版 Key 时本插件显示"未就绪"并说明原因;新版的生图生视频请用 totalclaw-mcp 的
`topview` 服务器(`router_*` 工具)。

- `TOPVIEW_API_KEY`:www.topview.ai/api-settings 的 API Key
- `TOPVIEW_UID`:同页的 UID(也可点右上角头像复制)
- 可选(config `digital_human.providers.topview`):`default_avatar_id` / `default_voice_id` /
  `default_caption_id` / `default_mode`

凭据解析优先级(与 agent 既有一致):环境变量 → config `digital_human.providers.topview`。
装完默认不启用:`totalclaw plugins enable dh-topview` 或在 qiye-app 设置页开启。
qiye-app 数字人工作台目前没有 TopView 的凭据输入框,请写进 `~/.totalclaw/.env`。

免费档有水印、单条时长受限,以 TopView 官网为准。TopView 官方注明 Unlimited 套餐不支持
MCP / Plugin / Skill(不支持自动化工作流),OpenAPI 是否同样受限待实测。
