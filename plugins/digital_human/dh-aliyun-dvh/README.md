# 阿里云数字人(DVH)

阿里云虚拟数字人(OpenAPI `avatar 2022-01-30`):**离线视频合成 + 3D 流媒体实时互动**。
数字人只当"嘴和脸",说什么由 TotalClaw 的 LLM 决定(SendText 文本驱动,不碰阿里内置对话链路)。

- provider 名:`aliyun_dvh` · 区域:`cn` · 类型:`cloud` · 形态:`offline + realtime`
- 状态:**已实现**(SDK 字段面已对 alibabacloud_avatar20220130 实包核实;免费额度实测待账号,见下)

## 能力

| 形态 | 链路 | 说明 |
|---|---|---|
| 离线合成 | `synthesize` → `query_task` | SubmitTextTo2D/3DAvatarVideoTask(`options.extra.avatar_type: 2d/3d`)→ QueryVideoTaskInfo;按秒计费,10 分钟免费额度 |
| 实时互动 | `start_session/speak/interrupt/stop_session` | StartInstance 返回 RTC channel/token(render type `rtc`,前端 AliyunAvatarSDK for Web 拉流)→ SendText 流式(`stream: {is_stream,index,position}`,单条 ≤1000 字)→ SendCommand INTERRUPT → StopInstance |

**成本命门**:平台不自动停机——会话必须显式 `stop_session`(agent 有 idle 回收兜底,qiye 关窗仍应显式调)。

## 凭据/配置

依赖官方 SDK(惰性 import):`pip install alibabacloud_avatar20220130`

| 键 | env(优先) | config(`digital_human.providers.aliyun_dvh`) |
|---|---|---|
| AccessKey ID | `ALIBABA_CLOUD_ACCESS_KEY_ID` | `access_key_id` |
| AccessKey Secret | `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | `access_key_secret` |
| TenantId | `ALIYUN_AVATAR_TENANT_ID` | `tenant_id` |
| AppId | `ALIYUN_AVATAR_APP_ID` | `app_id` |
| endpoint(可选) | `ALIYUN_AVATAR_ENDPOINT` | `endpoint` |

开通:控制台开"虚拟数字人开放平台"→ 创建业务应用拿 TenantId/AppId → 资产中心选形象/音色。
凭据解析优先级(与 agent 既有一致):env → config。缺任一凭据时方法返回配置引导文案,不抛异常。

## 实测清单(需真实账号,联调时过一遍)

- [ ] 离线:10 分钟免费额度跑通 提交→轮询→video_url(QueryVideoTaskInfo status 枚举映射复核)
- [ ] 实时:StartInstance→前端拉流→SendText 流式→打断→StopInstance;停机后控制台确认无计费实例

装完默认不启用:`totalclaw plugins enable dh-aliyun-dvh` 或在 qiye-app 设置页开启。
