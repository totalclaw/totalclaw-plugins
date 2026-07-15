# LiveTalking 私有化(GPU 高保真档)

对接用户自部署的 LiveTalking 运行时(musetalk/wav2lip,WebRTC,多路并发,需 GPU)

- provider 名:`livetalking_local` · 区域:`local` · 类型:`selfhosted` · 形态:`['realtime']`
- 状态:**脚手架**(plugin.yaml/注册骨架就位,provider 实现分批落地)

## 凭据/配置

- `TOTALCLAW_DH_LIVETALKING_ENDPOINT`:自部署 LiveTalking 服务地址
重运行时不在插件内;默认不启用,配置 endpoint 后生效

配置优先级:config `digital_human.providers.livetalking_local` > 环境变量。
装完默认不启用:`totalclaw plugins enable dh-livetalking-local` 或在 qiye-app 设置页开启。
