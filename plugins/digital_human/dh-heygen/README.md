# HeyGen LiveAvatar

HeyGen:实时 LiveAvatar(WebRTC/iframe)与离线视频生成,按分钟计费

- provider 名:`heygen` · 区域:`overseas` · 类型:`cloud` · 形态:`['offline', 'realtime']`
- 状态:**脚手架**(plugin.yaml/注册骨架就位,provider 实现分批落地)

## 凭据/配置

- `HEYGEN_API_KEY`:HeyGen API Key


配置优先级:config `digital_human.providers.heygen` > 环境变量。
装完默认不启用:`totalclaw plugins enable dh-heygen` 或在 qiye-app 设置页开启。
