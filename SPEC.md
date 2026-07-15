# 插件工程规范 v1

> 适用:本仓所有插件。违反任一"硬规则"的 PR 不合并。

## 1. 目录与命名

- 布局:`plugins/<category>/<name>/`,安装后落 `<TOTALCLAW_HOME>/plugins/<name>/`(扁平)。
- `name` = 全仓唯一 ID,仅 `[a-z0-9_-]`,带品类前缀防撞名(数字人用 `dh-` 前缀,如 `dh-aliyun-dvh`)。
- 每插件必含:`plugin.yaml`、`__init__.py`、`README.md`;可选 `provider.py` 等实现文件、`after-install.md`。

## 2. plugin.yaml 必填面

```yaml
manifest_version: 1                  # 安装器兼容检查(硬性)
requires_protocol_version: ">=1"     # SDK 协议版本(安装期 strict 校验)
name: dh-aliyun-dvh                  # 唯一 ID(与目录名一致)
display_name: 阿里云数字人(DVH)
version: 0.1.0                       # semver;改动必须递增
description: 一句话说清能力与边界
author: totalclaw
kind: backend                        # 数字人 provider 一律 backend
requires_env:                        # 富对象:qiye-app 设置向导据此渲染表单
  - name: ALIBABA_CLOUD_ACCESS_KEY_ID
    description: 阿里云 AccessKey ID
    prompt: 请输入阿里云 AccessKey ID
optional_env: []
```

## 3. 自包含铁律(下载插件与 bundled 插件的本质区别)

1. **代码全在插件目录内**——不得依赖 agent 仓库中"恰好存在"的内部模块。
2. **只准 import 稳定契约面**:
   - `totalclaw_plugin_sdk.*`(SDK 面);
   - `totalclaw_core.plugins.digital_human`(数字人品类契约:`DigitalHumanBackendBase`/`register_backend`);
   - Python 标准库 + httpx。
   禁止 import `totalclaw_core` 其余内部模块、`totalclaw_cli*`、`run_agent` ——那些不是契约,随时会变。
3. **零重依赖**:不得引入 torch/CUDA/ffmpeg/opencv 等重运行时;私有化 provider 只写薄适配器
   (HTTP/WS 客户端),重活在独立 Runtime 部署包(客户自部署,插件只对接 endpoint)。
   若确需轻量三方包,写进 plugin.yaml `requires_env` 说明并在 README 声明,由 agent 的
   runtime-deps doctor 透出——插件自身 import 必须惰性(方法内 import)且缺包时给引导文案。
4. **注册期零副作用**:`register(ctx)` 只做注册;绝不发网络请求、绝不拉起进程、绝不读写
   registry 之外的全局状态。可用性判断放 `is_available()`(读配置/env,仍然零 IO 副作用)。

## 4. 数字人 provider 插件契约

```python
# __init__.py 骨架(见 plugins/digital_human/_TEMPLATE/)
def register(ctx):
    from totalclaw_core.plugins.digital_human import register_backend
    from .provider import MyBackend
    register_backend(MyBackend())
```

- 继承 `DigitalHumanBackendBase`;声明 `name`(与插件 name 的 provider 段一致,如 `aliyun_dvh`)、
  `require_env`、元数据 `region`("cn"/"overseas"/"local")、`kind`("cloud"/"selfhosted")、
  `modes`(["offline","realtime"] 子集)。
- 离线合成实现 `synthesize/query_task`;实时实现 session 接口族(agent 侧抽象扩展后按版本适配,
  未支持的方法返回 not-supported,禁止抛裸异常)。
- 私有化 provider:`is_available()` = endpoint 配置存在;**绝不自动拉起本地服务**。
- 凭据解析:config `digital_human.providers.<provider>` 优先,厂商标准 env 兜底;缺凭据时
  方法返回带"请在 qiye-app 配置 X"的引导文案,不抛异常。

## 5. 安全要求

- registry.json 由 `scripts/gen_registry.py` 生成,含逐文件 sha256——**手改 registry 无效且视为投毒**;
- 不得包含任何形式的自更新/远程代码加载(`exec` 远程内容、动态 pip install);
- 网络访问只许指向 provider 官方 endpoint 或用户配置的 endpoint;
- 秘钥只从 ctx.config/env 读,绝不落日志。

## 6. 发布检查清单

- [ ] plugin.yaml 必填面齐全,version 已递增
- [ ] 只 import 契约面(§3.2),重依赖为零(§3.3)
- [ ] register 零副作用;is_available 正确反映凭据/endpoint 状态
- [ ] 缺凭据路径返回引导文案(人肉跑一遍)
- [ ] README 写清:能力/凭据获取方式/(私有化)Runtime 部署指引链接
- [ ] `python scripts/gen_registry.py` 通过且 registry.json 已更新

## 7. runtime.yaml 规范(selfhosted 插件的运行时部署清单)

私有化 provider 插件必须附带 `runtime.yaml`——**重运行时(GB 级镜像/模型权重)仍然永不进仓**,
进仓的只是这份部署清单;agent 的 runtime deployer 按清单代用户下载、部署、启动、写回 endpoint。

```yaml
runtime_version: 1
name: duix-runtime
display_name: DUIX 数字人运行时(CPU 轻量档)
deploy_modes: [local, remote, existing]  # 本机代部署 / 生成远程服务器部署包 / 已有部署直填 endpoint
default_mode: local                      # 安装插件后向导默认选中项
requirements:
  os: [windows, linux, macos]
  gpu: false
  min_memory_gb: 4
  disk_gb: 8
  docker: preferred                      # required | preferred | none(裸进程脚本)
artifacts:                               # 每个工件:多源(按 region)+ sha256/digest 固定
  - id: server-image
    kind: docker_image                   # docker_image | archive | model_weights
    size_mb: 3200
    sources:
      cn:   ["<国内镜像源>@sha256:<digest>"]
      intl: ["<dockerhub 源>@sha256:<digest>"]
  - id: avatar-assets
    kind: archive
    target: assets/
    size_mb: 800
    sha256: "<sha256>"
    sources:
      cn:   ["https://modelscope.cn/..."]
      intl: ["https://huggingface.co/..."]
deploy:
  compose: docker-compose.yml            # 插件目录内模板(轻文本)
  bare: scripts/start.sh                 # 可选:无 docker 兜底
health:
  endpoint: "http://127.0.0.1:{port}/health"
  ready_timeout_s: 180
service:
  default_port: 18080
  config_key: digital_human.providers.duix_local.endpoint   # 部署成功自动写回 agent 配置
```

硬规则:
- artifacts 的 sha256/镜像 digest **必须固定**(供应链底线,deployer 校验不过整体拒绝);
- sources 按 region 提供 cn/intl 双源(agent 用 resolve_region() 选源,可 failover);
- `remote` 模式 = 生成自包含部署包/命令供用户拷去 GPU 服务器执行,不做 SSH 代操作(期权);
- 部署/启动永远由用户在向导里显式触发——插件注册期零副作用铁律不变。
