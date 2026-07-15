# totalclaw-plugins — TotalClaw 官方插件仓

TotalClaw agent 与 qiye-app 的插件分发源。按**插件名称(name)或系统唯一 ID(id)**
下载安装单个插件,无需 clone 整仓。

## 寻址坐标(SPEC §8)

每个插件有两个等效寻址坐标,安装命令二者皆可:

- `name`:仓内唯一短 ID,如 `dh-aliyun-dvh`;
- `id`:跨仓全局唯一 ID `<registry>/<category>/<name>`,如
  `totalclaw-plugins/digital_human/dh-aliyun-dvh`(gen_registry 自动派生,发布后终身不变,
  适合 agent 写进配置/会话持久引用)。

解析规则:spec 含 `/` 走 id 精确匹配,否则走 name 精确匹配;可选 `@<version>` 钉扎
(与 registry 当前版本不符即报错,本仓只分发最新版)。

## 安装方式

```bash
# CLI(agent 已内置市场机制,TOTALCLAW_PLUGIN_REGISTRY 指向本仓 registry.json)
totalclaw plugins install dh-aliyun-dvh                                        # 按 name
totalclaw plugins install totalclaw-plugins/digital_human/dh-aliyun-dvh       # 按唯一 id
totalclaw plugins install dh-aliyun-dvh@0.0.2                                  # 版本钉扎
totalclaw plugins enable  dh-aliyun-dvh   # 装完默认不启用,显式启用才生效

# REST(qiye-app 用)
POST /v1/plugins/install   {"spec": "<name 或 id>[@version]"}
POST /v1/plugins/<name>/enable {"enabled": true}
```

注册表地址(供 `TOTALCLAW_PLUGIN_REGISTRY` 配置):

```
https://gitee.com/jlzdyx/totalclaw-plugins/raw/master/registry.json
```

## 仓库布局

```
registry.json                  # 市场索引(机器生成,勿手改)——name/id/版本/文件清单/sha256/依赖 env
SPEC.md                        # 插件工程规范(必读:自包含/契约 import 面/寻址协议/安全/发布)
CONTRIBUTING.md                # 第三方投稿流程(机检门槛/verified 审核标记)
scripts/
  gen_registry.py              # 索引生成器:遍历 plugins/ 计算逐文件 sha256 与 bundle hash
  ci_check.py                  # 一站机检(pre-push 钩子同款;scripts/hooks/pre-push)
  backfill_runtime_digest.py   # Runtime 工件发布后回填 digest/sha256
  sign_registry.sh             # registry 签名 v2(期权,cosign)
tests/conformance.py           # 插件契约符合性测试(零配置全接口族无裸异常)
docs/LOCAL_RUNTIME_PROTOCOL.md # 私有化运行时协议 v1(duix/ace 适配器对协议编程)
runtime-build/                 # Runtime 包构建工程(镜像/权重工件本体永不进仓)
plugins/
  digital_human/               # 品类目录(第一个品类:数字人 provider)
    _TEMPLATE/                 # 新 provider 插件模板(async 契约实现版)
    dh-aliyun-dvh/  dh-tencent-ivh/  dh-heygen/  dh-tavus/                    # 云厂商四家
    dh-duix-local/  dh-livetalking-local/  dh-talkinghead-web/  dh-nvidia-ace/ # 私有化四家
```

## 下载协议(客户端实现参考)

三级策略(与 totalclaw-skills 仓同款):

1. 读 `registry.json`(Gitee raw)→ 按 SPEC §8 解析 spec(name 或 id,可选 @version)
   命中条目,拿 `path` 与 `files[]`(相对路径+sha256);
2. 逐文件 Gitee raw 下载 → **sha256 校验**(任一不匹配即整体拒绝);
3. 兜底:`git clone --depth 1 --sparse` 只拉 `plugins/<category>/<name>/`。

安装落盘到 `<TOTALCLAW_HOME>/plugins/<name>/`,随后走 agent 既有流水线:
manifest 严格校验 → 内容安全扫描 → 落盘登记 → **默认禁用**,显式 enable 后由插件发现加载。

## 安全模型

- registry.json 声明每个文件的 sha256;客户端下载后必须校验;
- 插件代码在 agent 主进程执行——**默认禁用 + 安装前扫描 + 校验和**三关是底线;
- 私有化数字人 provider 插件只含**薄适配器**(HTTP/WS 客户端,几百行,零重依赖);
  模型权重/torch/CUDA 等重运行时**永不进本仓**,以独立 Runtime 部署包分发(见各插件 README)。

## 许可

本仓以 [Apache-2.0](LICENSE) 发布(宽松 + 显式专利授权,插件生态惯例;2026-07-15 已确认)。
插件若引入第三方代码,在该插件目录 README 内逐项声明来源与许可。

## 发布流程(维护者)

1. 首次 clone 后启用机检钩子(一次性):`git config core.hooksPath scripts/hooks`;
2. 在 `plugins/<category>/<name>/` 完成插件(照 `_TEMPLATE`,过 SPEC.md 检查清单);
3. `python3 scripts/gen_registry.py` 重新生成 registry.json(校验和/schema 自检);
4. `python3 scripts/ci_check.py` 机检全绿(registry 一致/manifest 校验/version 递增/
   禁 import 面/危险模式/runtime.yaml 结构;pre-push 钩子会自动跑同一套);
5. 提交 PR / push(registry 与插件同 commit);客户端 1 小时缓存 TTL 后可见。
