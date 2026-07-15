# NVIDIA ACE/Tokkio 私有化

对接用户自部署的 NVIDIA ACE/Tokkio 微服务(照片级,GPU,最重)

- provider 名:`nvidia_ace` · 区域:`local` · 类型:`selfhosted` · 形态:`['realtime']`
- 状态:**已实现(Local Avatar Runtime 协议 v1 薄客户端);Runtime 引用 NVIDIA 官方 NIM(需 NGC 凭据),按客户需求触发包制作**

## 能力

- 实时:全接口族对接 [Local Avatar Runtime 协议 v1](../../../docs/LOCAL_RUNTIME_PROTOCOL.md)(Tokkio/ACE 微服务翻译在 Runtime 桥接层;运行时清单指向 NVIDIA 官方 NIM 分发,不自建镜像)
- 离线合成不支持

## 凭据/配置

- `TOTALCLAW_DH_ACE_ENDPOINT`:自部署 ACE 服务地址
重运行时不在插件内;默认不启用,配置 endpoint 后生效

凭据解析优先级(与 agent 既有一致):环境变量 → config `digital_human.providers.nvidia_ace`。
装完默认不启用:`totalclaw plugins enable dh-nvidia-ace` 或在 qiye-app 设置页开启。

## Runtime 部署(由系统代办,无需手动)

安装本插件后,qiye-app 会引导进入 **Runtime 部署向导**(默认"本机部署"):
1. 本机部署:agent 按 `runtime.yaml` 清单代下载运行时工件(按地域选国内/国外源,sha256 校验),
   docker-compose 拉起服务,健康检查通过后自动写回 endpoint 配置——全程无需手动操作;
2. 远程服务器:生成自包含部署包/命令,拷贝到 GPU 服务器执行后回填地址;
3. 已有部署:直接填 endpoint。

资源要求:GPU 必需,内存 ≥32GB,磁盘 ≥80GB。
