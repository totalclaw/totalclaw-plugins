# TotalClaw Local Avatar Runtime 协议 v1

私有化数字人插件(dh-duix-local / dh-nvidia-ace)的适配器不直接绑定上游开源项目的
私有 API,而是对本协议编程;**Runtime 部署包**(R-10/R-13 制作,工件不进仓)内含一个
轻量桥接层,把本协议翻译到上游(DUIX 服务/ACE·Tokkio 微服务)。好处:

1. 适配器永远不随上游 API 漂移而破坏(桥接层随 Runtime 包版本走);
2. 新私有化引擎入仓只需实现同一协议,插件代码即模板化;
3. 协议面极小,便于 runtime deployer 健康检查与 qiye 渲染契约对齐。

(例外:dh-livetalking-local 直接说 LiveTalking 原生 API——它的 HTTP 面本就稳定
且社区标准,包一层反而增加维护面。)

## 端点

Base = 插件配置的 endpoint(如 `http://127.0.0.1:18080`),全部 JSON。

| 方法/路径 | 入参 | 出参 | 说明 |
|---|---|---|---|
| `GET /health` | — | `{"status":"ok","engine":"duix","version":"..."}` | deployer 就绪探测(runtime.yaml health.endpoint) |
| `POST /v1/sessions` | `{"avatar_id":"","voice_id":"","extra":{}}` | `{"session_id":"...","render":{...}}` | 开实时会话;render 按 agent 契约五型之一(引擎自决,DUIX CPU 档常为 `rtc` WebRTC offer 或 `iframe` 本地页) |
| `POST /v1/sessions/{sid}/speak` | `{"text":"...","stream":{"is_stream":bool,"index":int,"position":"start\|mid\|end","interrupt":bool}}` | `{"success":true}` | 文本驱动开口(BYO-LLM);流式切句字段与云厂商语义对齐 |
| `POST /v1/sessions/{sid}/interrupt` | `{}` | `{"success":true}` | 打断当前播报 |
| `DELETE /v1/sessions/{sid}` | — | `{"success":true}` | 关会话(本地运行时无按分钟计费,但要释放算力) |
| `GET /v1/sessions/{sid}` | — | `{"session_id":"...","running":bool}` | 会话状态 |
| `GET /v1/sessions` | — | `{"sessions":[{"session_id":"..."}]}` | 会话对账 |

## 错误约定

- HTTP 4xx/5xx + `{"error":"...","message":"人话"}`;
- 会话不存在:404;引擎忙(并发满):429 + `{"message":"并发已满,当前 N 路"}`。

## 版本协商

`GET /health` 返回 `protocol_version`(整数,当前 1);适配器对不认识的高版本
降级只用 v1 面。桥接层新增能力走 `extra` 透传,不破坏 v1 字段。
