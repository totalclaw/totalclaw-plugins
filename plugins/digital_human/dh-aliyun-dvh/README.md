# 阿里云数字人(DVH)

阿里云虚拟数字人:离线视频合成 + 3D 流媒体实时互动(SendText 流式驱动)

- provider 名:`aliyun_dvh` · 区域:`cn` · 类型:`cloud` · 形态:`['offline', 'realtime']`
- 状态:**脚手架**(plugin.yaml/注册骨架就位,provider 实现分批落地)

## 凭据/配置

- `ALIBABA_CLOUD_ACCESS_KEY_ID`:阿里云 AccessKey ID
- `ALIBABA_CLOUD_ACCESS_KEY_SECRET`:阿里云 AccessKey Secret
另需 config 配置 tenant_id/app_id(数字人开放平台业务应用)

配置优先级:config `digital_human.providers.aliyun_dvh` > 环境变量。
装完默认不启用:`totalclaw plugins enable dh-aliyun-dvh` 或在 qiye-app 设置页开启。
