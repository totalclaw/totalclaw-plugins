# TalkingHead 浏览器渲染(海外轻量档)

渲染完全在 qiye-app 前端 WebGL(met4citizen/TalkingHead),服务端零 GPU;插件只出资产配置与 TTS 桥

- provider 名:`talkinghead_web` · 区域:`local` · 类型:`selfhosted` · 形态:`['realtime']`
- 状态:**脚手架**(plugin.yaml/注册骨架就位,provider 实现分批落地)

## 凭据/配置

- 无需凭据(前端渲染型)
需 qiye-app 前端 TalkingHead 组件配合(render.type=webgl)

配置优先级:config `digital_human.providers.talkinghead_web` > 环境变量。
装完默认不启用:`totalclaw plugins enable dh-talkinghead-web` 或在 qiye-app 设置页开启。
