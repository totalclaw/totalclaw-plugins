# NVIDIA ACE Runtime 引用清单(R-13②)

**不自建 ACE 镜像**——runtime.yaml 的工件直接引用 NVIDIA 官方 NIM/Tokkio 分发
(digest 钉扎),本目录只维护:①引用清单的核准记录;②协议 v1 桥接容器(轻量,
随我方源分发,把协议 v1 翻译到 Tokkio/ACE 微服务)。

## 组成(按客户需求触发时核准)

| 工件 | 来源 | 说明 |
|---|---|---|
| Tokkio/ACE 微服务 | nvcr.io 官方 NIM(需客户 NGC 凭据) | digest 钉扎进 runtime.yaml;cn 侧无官方镜像源,清单标注"需可达 nvcr.io 或客户自建代理仓" |
| 协议桥接容器 | 我方构建(复用 duix/bridge 骨架,upstream 换 ACE 调用) | cn/intl 双源同 DUIX 流程 |

## 决策记录

- ACE/Tokkio 是全托管 pipeline(ASR/TTS/A2F/渲染),部署重(GPU 多卡);**按客户
  需求触发**制作,不进默认交付节奏(PLUGINS_REPO_TODO R-13 原文)。
- NGC 凭据属客户资产:runtime deployer 部署前置检查需提示配置 NGC_API_KEY
  (agent A-22 前置检查项)。

## 待外部动作(客户落单触发)

- [ ] 与客户确认 Tokkio 版本 → 官方 NIM digest 核准回填 runtime.yaml
- [ ] 桥接容器实现(ACE 会话 API 接线)+ 双源发布
