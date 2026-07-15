# TalkingHead 浏览器渲染(海外轻量档)

渲染完全在 qiye-app 前端 WebGL(met4citizen/TalkingHead),服务端零 GPU;插件只出资产配置与 TTS 桥

- provider 名:`talkinghead_web` · 区域:`local` · 类型:`selfhosted` · 形态:`['realtime']`
- 状态:**已实现(服务端零依赖:只产出 render 资产清单与前端指令信封)**

## 能力

- `start_session` 返回 render type=webgl:`{avatar_url(.glb), lib:talkinghead, tts:{...}, lipsync_lang, mood}`,qiye 前端 TalkingHead 组件按此渲染(Ready Player Me 形象,缺省用官方示例形象)
- `speak/interrupt` 返回前端指令信封 `directive:{op,text}`(TTS 与口型全在前端);无 runtime.yaml——运行时就是 qiye 前端
- 启用:config `digital_human.providers.talkinghead_web.enabled: true`(无凭据无 endpoint)

## 凭据/配置

- 无需凭据(前端渲染型)
需 qiye-app 前端 TalkingHead 组件配合(render.type=webgl)

凭据解析优先级(与 agent 既有一致):环境变量 → config `digital_human.providers.talkinghead_web`。
装完默认不启用:`totalclaw plugins enable dh-talkinghead-web` 或在 qiye-app 设置页开启。
