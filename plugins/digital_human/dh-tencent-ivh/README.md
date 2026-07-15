# 腾讯云智能数智人(IVH)

腾讯云智能数智人:形象类型最全(2D精品/小样本/3D写实/半写实/卡通)

- provider 名:`tencent_ivh` · 区域:`cn` · 类型:`cloud` · 形态:`['offline', 'realtime']`
- 状态:**链路已实现(TC3-HMAC-SHA256 签名直连,零厂商 SDK)——**action 面与实测待商务开白****

## 能力

- 离线:`synthesize`/`query_task` 走腾讯云标准 API(action 默认 SubmitVideoMakeJob/DescribeVideoMakeJob,开白后按官方文档核准;可 config `digital_human.providers.tencent_ivh.actions` 覆盖,无须改代码)
- 实时:接口族已就位,开白拿到实时会话文档后接线(当前返回结构化引导)
- 签名器:TC3-HMAC-SHA256 标准实现(stdlib hmac/hashlib),host/service/version/region 全可配

## 凭据/配置

- `TENCENTCLOUD_SECRET_ID`:腾讯云 SecretId
- `TENCENTCLOUD_SECRET_KEY`:腾讯云 SecretKey
部分能力需商务开白

凭据解析优先级(与 agent 既有一致):环境变量 → config `digital_human.providers.tencent_ivh`。
装完默认不启用:`totalclaw plugins enable dh-tencent-ivh` 或在 qiye-app 设置页开启。
