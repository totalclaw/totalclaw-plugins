# NVIDIA ACE/Tokkio 私有化

对接用户自部署的 NVIDIA ACE/Tokkio 微服务(照片级,GPU,最重)

- provider 名:`nvidia_ace` · 区域:`local` · 类型:`selfhosted` · 形态:`['realtime']`
- 状态:**脚手架**(plugin.yaml/注册骨架就位,provider 实现分批落地)

## 凭据/配置

- `TOTALCLAW_DH_ACE_ENDPOINT`:自部署 ACE 服务地址
重运行时不在插件内;默认不启用,配置 endpoint 后生效

配置优先级:config `digital_human.providers.nvidia_ace` > 环境变量。
装完默认不启用:`totalclaw plugins enable dh-nvidia-ace` 或在 qiye-app 设置页开启。
