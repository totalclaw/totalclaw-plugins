# 腾讯云智能数智人(IVH)

腾讯云智能数智人:形象类型最全(2D精品/小样本/3D写实/半写实/卡通)

- provider 名:`tencent_ivh` · 区域:`cn` · 类型:`cloud` · 形态:`['offline', 'realtime']`
- 状态:**脚手架**(plugin.yaml/注册骨架就位,provider 实现分批落地)

## 凭据/配置

- `TENCENTCLOUD_SECRET_ID`:腾讯云 SecretId
- `TENCENTCLOUD_SECRET_KEY`:腾讯云 SecretKey
部分能力需商务开白

配置优先级:config `digital_human.providers.tencent_ivh` > 环境变量。
装完默认不启用:`totalclaw plugins enable dh-tencent-ivh` 或在 qiye-app 设置页开启。
