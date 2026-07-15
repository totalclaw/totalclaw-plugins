# totalclaw-plugins — TotalClaw 官方插件仓

TotalClaw agent 与 qiye-app 的插件分发源。按**插件名称(唯一 ID)**下载安装单个插件,
无需 clone 整仓。

## 安装方式

```bash
# CLI(agent 已内置市场机制,TOTALCLAW_PLUGIN_REGISTRY 指向本仓 registry.json)
totalclaw plugins install <name>          # 例:totalclaw plugins install dh-aliyun-dvh
totalclaw plugins enable  <name>          # 装完默认不启用,显式启用才生效

# REST(qiye-app 用)
POST /v1/plugins/install   {"spec": "<name>"}
POST /v1/plugins/<name>/enable {"enabled": true}
```

注册表地址(供 `TOTALCLAW_PLUGIN_REGISTRY` 配置):

```
https://gitee.com/jlzdyx/totalclaw-plugins/raw/master/registry.json
```

## 仓库布局

```
registry.json                  # 市场索引(机器生成,勿手改)——name/版本/文件清单/sha256/依赖 env
scripts/gen_registry.py        # 索引生成器:遍历 plugins/ 计算逐文件 sha256 与 bundle hash
SPEC.md                        # 插件工程规范(必读:自包含原则/契约 import 面/安全要求/发布流程)
plugins/
  digital_human/               # 品类目录(第一个品类:数字人 provider)
    _TEMPLATE/                 # 新 provider 插件模板
    aliyun_dvh/  tencent_ivh/  heygen/  tavus/            # 云厂商四家
    duix_local/  livetalking_local/  talkinghead_web/  nvidia_ace/   # 私有化四家
```

## 下载协议(客户端实现参考)

三级策略(与 totalclaw-skills 仓同款):

1. 读 `registry.json`(Gitee raw)→ 按 name 命中条目,拿 `path` 与 `files[]`(相对路径+sha256);
2. 逐文件 Gitee raw 下载 → **sha256 校验**(任一不匹配即整体拒绝);
3. 兜底:`git clone --depth 1 --sparse` 只拉 `plugins/<category>/<name>/`。

安装落盘到 `<TOTALCLAW_HOME>/plugins/<name>/`,随后走 agent 既有流水线:
manifest 严格校验 → 内容安全扫描 → 落盘登记 → **默认禁用**,显式 enable 后由插件发现加载。

## 安全模型

- registry.json 声明每个文件的 sha256;客户端下载后必须校验;
- 插件代码在 agent 主进程执行——**默认禁用 + 安装前扫描 + 校验和**三关是底线;
- 私有化数字人 provider 插件只含**薄适配器**(HTTP/WS 客户端,几百行,零重依赖);
  模型权重/torch/CUDA 等重运行时**永不进本仓**,以独立 Runtime 部署包分发(见各插件 README)。

## 发布流程(维护者)

1. 在 `plugins/<category>/<name>/` 完成插件(照 `_TEMPLATE`,过 SPEC.md 检查清单);
2. `python scripts/gen_registry.py` 重新生成 registry.json(校验和/schema 自检);
3. 提交 PR / push;客户端 1 小时缓存 TTL 后可见。
