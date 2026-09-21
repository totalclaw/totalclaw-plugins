# 泰途智脑 2.0 运行时包

本目录是**运行时包渠道**，与同仓 `registry.json` 的插件市场渠道并行，互不替代。

| 渠道 | 装什么 | 入口 |
| --- | --- | --- |
| 插件市场（`registry.json`） | KB 级插件薄壳 | `totalclaw plugin install <name>` |
| 运行时包（本目录） | 智脑 2.0 运行时 wheel | `totalclaw get cerebellum`、企业版「通用设置 → 泰途智脑 2.0 → 升级」 |

## 目录

```
cerebellum/
├── index.json                # 运行时版本索引：version / sha256 / size / cn+intl 源
├── models.json               # Router-1 可选路由模型清单（当前为空，不提供模型）
└── releases/<version>/*.whl  # 运行时 wheel（纯 Python，百 KB 级）
```

SPEC §7 的「重运行时永不进仓」针对的是 GB 级镜像与模型权重。本目录只放百 KB 级的
纯 Python wheel，权重仍然不进仓。

## 发新版

索引里的 sha256 必须从磁盘上真实的 wheel 算出，**不手写**（手写的摘要必然过期）：

```bash
# 在 totalclaw-agent-cerebellum 仓
python -m pip wheel . --no-deps -w dist/
cerebellum-build-release-index dist/totalclaw_agent_cerebellum-<版本>-py3-none-any.whl \
  --merge <本仓>/cerebellum/index.json > /tmp/index.json

# 回到本仓
cp /tmp/index.json cerebellum/index.json
cp dist/*.whl cerebellum/releases/<版本>/
```

`--merge` 会保留已发布的历史版本并把 `latest` 指到最新的那个。

## 消费方怎么用

客户端读 `index.json`，按区域挑源下载，**sha256 固定校验**，解包到独立代次，
用真解释器跑一次冒烟，过了才原子切换；旧代次原地保留可回滚。实现只有一份，在
agent 的 `totalclaw_core/cerebellum_runtime.py`，CLI 与企业版升级按钮共用。

覆盖默认源：`TOTALCLAW_CEREBELLUM_INDEX` / `TOTALCLAW_CEREBELLUM_MODELS`。
