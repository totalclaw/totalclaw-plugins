# LiveTalking 私有化(GPU 高保真档)

对接用户自部署的 LiveTalking 运行时(musetalk/wav2lip,WebRTC,多路并发,需 GPU)

- provider 名:`livetalking_local` · 区域:`local` · 类型:`selfhosted` · 形态:`['realtime']`
- 状态:**脚手架**(plugin.yaml/注册骨架就位,provider 实现分批落地)

## 凭据/配置

- `TOTALCLAW_DH_LIVETALKING_ENDPOINT`:自部署 LiveTalking 服务地址
重运行时不在插件内;默认不启用,配置 endpoint 后生效

配置优先级:config `digital_human.providers.livetalking_local` > 环境变量。
装完默认不启用:`totalclaw plugins enable dh-livetalking-local` 或在 qiye-app 设置页开启。

## Runtime 部署(由系统代办,无需手动)

安装本插件后,qiye-app 会引导进入 **Runtime 部署向导**(默认"本机部署"):
1. 本机部署:agent 按 `runtime.yaml` 清单代下载运行时工件(按地域选国内/国外源,sha256 校验),
   docker-compose 拉起服务,健康检查通过后自动写回 endpoint 配置——全程无需手动操作;
2. 远程服务器:生成自包含部署包/命令,拷贝到 GPU 服务器执行后回填地址;
3. 已有部署:直接填 endpoint。

资源要求:GPU 必需,内存 ≥16GB,磁盘 ≥30GB。
