# DUIX Runtime 包制作(R-10②)

产出物:`duix-runtime` Docker 镜像(CPU 版服务 + 协议 v1 桥接层)+ 形象资产包。
**工件永不进本仓**——本目录只有构建工程;发布后用 `scripts/backfill_runtime_digest.py`
把 digest/sha256 回填 `plugins/digital_human/dh-duix-local/runtime.yaml`(TBD 清零)。

## 镜像组成

```
基座: python:3.11-slim(CPU 档,无 CUDA)
+ DUIX 开源服务(github.com/GuijiAI/duix.ai,pin 到指定 commit——见 build.sh DUIX_REF)
+ bridge/:TotalClaw Local Avatar Runtime 协议 v1 → DUIX API 翻译层
  (协议规范:docs/LOCAL_RUNTIME_PROTOCOL.md;/health /v1/sessions 全族)
监听: 18080(与 runtime.yaml service.default_port 一致)
```

## 构建与发布

```bash
./build.sh                # 构建 totalclaw/duix-runtime:<version>(见脚本内 pin)
# 双源发布(需要相应仓库凭据,外部动作):
docker push registry.cn-hangzhou.aliyuncs.com/totalclaw/duix-runtime:<v>   # cn 源
docker push docker.io/totalclaw/duix-runtime:<v>                            # intl 源
# 形象资产包(tar.gz):ModelScope(cn)+ HuggingFace(intl)
# 回填 digest(把 TBD 换成真值,自动跑 gen_registry):
python3 ../../scripts/backfill_runtime_digest.py dh-duix-local \
  --artifact server-image --cn <cn镜像@sha256:...> --intl <dockerhub@sha256:...> --size-mb <n>
```

## Windows 无 Docker 场景:裸进程 `deploy.bare` 方案评估(R-10 子项,2026-07-15)

客户桌面机多为 Windows,Docker Desktop 不可假设。结论:**可行但后置**,理由与设计:

| 维度 | 评估 |
|---|---|
| 技术可行性 | DUIX CPU 档为 Python 服务,可 PyInstaller/embedded-python 打包为 zip(免装环境);bridge 同包 |
| 体积 | 与镜像同量级(~3GB,模型占大头),分发走同一双源(archive 工件) |
| 生命周期 | 无容器隔离:用 Windows 计划任务/NSSM 注册服务;deployer 需实现 bare 启停(A-22 的 deploy.bare 分支) |
| 风险 | 依赖冲突(嵌入式 Python 缓解)、杀软误报(需签名)、端口占用探测 |
| 决策 | runtime.yaml 已留 `deploy.bare` 口;**首发只做 docker(preferred),bare 在首个 Windows 无 Docker 客户落单时启动**,工期 ~2 人日 |

## 待外部动作(需凭据/基础设施,做完勾选)

- [ ] 阿里云镜像仓 + DockerHub 组织账号(cn/intl 双源)
- [ ] ModelScope/HuggingFace 资产仓(形象包)
- [ ] 构建→推送→digest 回填→`gen_registry.py`→commit(与插件版本递增同 commit)
