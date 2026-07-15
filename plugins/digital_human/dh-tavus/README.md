# Tavus CVI

Tavus 对话式视频接口:BYO-LLM 原生设计,端到端 <500ms

- provider 名:`tavus` · 区域:`overseas` · 类型:`cloud` · 形态:`['realtime']`
- 状态:**已实现(REST 直连 httpx;真实 key 实测待账号)**

## 能力

- 实时:`start_session`(POST /v2/conversations,render type=iframe 直嵌 conversation_url)→ `stop_session`(/end,**按分钟计费,必须显式停**);speak/interrupt 走前端 Daily Interactions Protocol(服务端 REST 无此口,方法返回结构化引导);BYO-LLM 在 Tavus persona 配置指向我们 API
- 离线:`synthesize`(POST /v2/videos,replica_id+script)→ `query_task`(GET /v2/videos/{id})

## 凭据/配置

- `TAVUS_API_KEY`:Tavus API Key


凭据解析优先级(与 agent 既有一致):环境变量 → config `digital_human.providers.tavus`。
装完默认不启用:`totalclaw plugins enable dh-tavus` 或在 qiye-app 设置页开启。
