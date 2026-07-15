# 第三方插件投稿流程(R-15)

欢迎向 totalclaw-plugins 投稿插件。**下载即在 agent 主进程执行 Python**,所以审核是
硬门槛,不是流程装饰。

## 投稿步骤

1. 照 `plugins/<category>/_TEMPLATE/` 起步,通读 `SPEC.md`(硬规则:自包含/契约
   import 面/注册零副作用/零重依赖,违反任一不合并);
2. 本地过机检:`python3 scripts/gen_registry.py && python3 scripts/ci_check.py`
   + `python3 tests/conformance.py`(全绿才提 PR);
3. 提 PR(模板自动带出检查清单),标题格式 `plugin(<name>): <一句话>`;
4. 维护者审核(见下)→ 合并后随 registry 发布,客户端 1 小时缓存 TTL 后可见。

## 审核与 verified 标记

| 项 | 说明 |
|---|---|
| 机检 | CI 跑 ci_check + conformance,红灯不进入人审 |
| 人审 | 逐行审 provider 代码:网络目标只许官方/用户配置 endpoint、秘钥不落日志、无混淆代码 |
| verified 位 | **仅维护者可置**。官方仓内置插件 verified=true;第三方首次合并默认 **false**——agent 侧对非 verified 条目安装时默认 ask(用户确认);维护者对作者建立信任后(多次高质量投稿+实测)可升 true |
| 撤销 | 任何时候发现违规:条目移除(name/id 永不复用,SPEC §8),涉安全问题公告 |

## 发布纪律(投稿者同样适用)

改任何插件必递增其 `version` → 跑 `gen_registry.py` → registry 与插件改动**同一个
commit**;破坏性契约变更必须同时更新 `tested_with` 并在插件 README 标注最低 agent 版本。
