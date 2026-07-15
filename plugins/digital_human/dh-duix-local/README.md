# DUIX 私有化(CPU 轻量档)

对接用户自部署的 DUIX 运行时(硅基智能开源,4核CPU+4G 可跑);插件仅为薄适配器

- provider 名:`duix_local` · 区域:`local` · 类型:`selfhosted` · 形态:`['realtime']`
- 状态:**脚手架**(plugin.yaml/注册骨架就位,provider 实现分批落地)

## 凭据/配置

- `TOTALCLAW_DH_DUIX_ENDPOINT`:自部署 DUIX 服务地址,如 http://127.0.0.1:18080
重运行时不在插件内:Runtime 部署包见插件 README;默认不启用,配置 endpoint 后生效

配置优先级:config `digital_human.providers.duix_local` > 环境变量。
装完默认不启用:`totalclaw plugins enable dh-duix-local` 或在 qiye-app 设置页开启。
