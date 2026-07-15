# Tavus CVI

Tavus 对话式视频接口:BYO-LLM 原生设计,端到端 <500ms

- provider 名:`tavus` · 区域:`overseas` · 类型:`cloud` · 形态:`['realtime']`
- 状态:**脚手架**(plugin.yaml/注册骨架就位,provider 实现分批落地)

## 凭据/配置

- `TAVUS_API_KEY`:Tavus API Key


配置优先级:config `digital_human.providers.tavus` > 环境变量。
装完默认不启用:`totalclaw plugins enable dh-tavus` 或在 qiye-app 设置页开启。
