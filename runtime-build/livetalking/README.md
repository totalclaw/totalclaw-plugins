# LiveTalking Runtime 包制作(R-11②)

产出物:`livetalking-runtime` GPU 镜像(CUDA 基座 + LiveTalking pin 版)+ musetalk
权重工件包。适配器直连 LiveTalking 原生 API(/offer /human /is_speaking),**无桥接层**。

## 组成

```
镜像: CUDA 基座 + LiveTalking(github.com/lipku/LiveTalking,pin LIVETALKING_REF)
      启动: app.py --transport webrtc --model musetalk(rtmp/virtualcam 为直播层选项,A-18)
权重: musetalk 模型权重(GB 级)→ 独立 archive 工件,部署时挂载 models/
      双源: ModelScope(cn)/ HuggingFace(intl)——上游权重本就发布在两处,pin revision
监听: 8010(LiveTalking 默认;runtime.yaml service.default_port 保持一致)
```

## 构建与发布

```bash
VERSION=0.1.0 LIVETALKING_REF=<commit> ./build.sh
docker push registry.cn-hangzhou.aliyuncs.com/totalclaw/livetalking-runtime:<v>  # cn
docker push docker.io/totalclaw/livetalking-runtime:<v>                           # intl
python3 ../../scripts/backfill_runtime_digest.py dh-livetalking-local \
  --artifact server-image --cn <ref@sha256:...> --intl <ref@sha256:...> --size-mb <n>
python3 ../../scripts/backfill_runtime_digest.py dh-livetalking-local \
  --artifact musetalk-weights --sha256 <sha256> --cn <modelscope url> --intl <hf url> --size-mb <n>
```

## remote 部署包(GPU 服务器是主流场景,R-11 子项)

agent A-25 生成自包含部署包,内容 = `docker-compose.yml`(镜像 digest 钉扎)+
权重下载脚本(按服务器地域选源+sha256 校验)+ `README`(一条命令:`docker compose up -d`,
完成后把 `http://<server>:8010` 回填 qiye 向导)。**runtime.yaml deploy_modes 已含
remote**;包生成逻辑在 agent 侧,本仓验证项:compose 模板可独立运行(不依赖 agent 在场)。

## 待外部动作(需凭据/GPU 机,做完勾选)

- [ ] GPU 构建机(CUDA)+ cn/intl 镜像仓账号
- [ ] musetalk 权重双源上传(pin revision + sha256)
- [ ] GPU 服务器实测:/offer 协商→/human echo→打断→多路并发压测
- [ ] digest 回填 → gen_registry → commit(与插件版本递增同 commit)
