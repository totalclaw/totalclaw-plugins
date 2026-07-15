# 插件工程规范 v1

> 适用:本仓所有插件。违反任一"硬规则"的 PR 不合并。

## 1. 目录与命名

- 布局:`plugins/<category>/<name>/`,安装后落 `<TOTALCLAW_HOME>/plugins/<name>/`(扁平)。
- `name` = 全仓唯一短 ID,仅 `[a-z0-9_-]`(字母数字开头),带品类前缀防撞名(数字人用 `dh-` 前缀,如 `dh-aliyun-dvh`)。
- 每个插件另有**系统唯一 ID** `id = <registry>/<category>/<name>`(如
  `totalclaw-plugins/digital_human/dh-aliyun-dvh`),由 gen_registry.py 自动派生写入
  registry——不进 plugin.yaml、不许手填;寻址与安装协议见 §8。
- **发布后永不改名**:name/id 一经进入 master 的 registry.json 即冻结;确需改名 =
  新建插件(新 name)+ 旧条目走弃用流程,绝不复用旧 name 指向不同插件。
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

## 8. 寻址与安装协议(name / 唯一 ID / 版本钉扎)

agent(及任何安装器)对本仓插件的寻址坐标,**双坐标 + 可选版本钉扎**:

| 坐标 | 形态 | 例 | 唯一域 |
|---|---|---|---|
| `name` | `[a-z0-9_-]` 短 ID | `dh-aliyun-dvh` | 本仓唯一 |
| `id` | `<registry>/<category>/<name>` | `totalclaw-plugins/digital_human/dh-aliyun-dvh` | 跨仓全局唯一 |

安装 spec 字符串文法:

```
spec := (id | name) ["@" version]
```

**解析规则(安装器必须实现,无歧义)**:

1. 先剥离可选 `@<version>` 后缀;
2. 剩余部分**含 `/`** → 按 `id` 字段精确匹配(name 字符集禁 `/`,故无歧义);
   不含 `/` → 按 `name` 字段精确匹配;
3. 只做大小写敏感的精确匹配,**不做模糊/前缀匹配**;未命中时可在错误信息里
   列近似候选,但绝不自动替用户选;
4. 带 `@version` 钉扎时:与 registry 当前 version 逐字比对,不一致即报错
   "registry 仅分发最新版 X,请去掉钉扎或等待发布"——本仓 raw/master 只 serve
   最新版,历史版本回溯是期权(git tag `<name>/v<version>`);
5. 完整性锚点:命中条目后以 `files[].sha256` 逐文件校验 + `bundle_sha256`
   整体校验(下载协议见 README),不是以 URL 为信任根。

**ID 稳定性契约**(为什么 agent 可以放心把 id 存进配置/会话/工单):

- `id` 由 gen_registry.py 从目录结构派生,人手不可篡改(手改 registry 视为投毒,§5);
- name/category 发布后冻结(§1)→ id 终身不变;插件下架时条目移除,id 永不复用;
- registry 顶层 `id_scheme` 字段自描述派生规则,多仓共存时以 `registry` 字段区分命名空间。
