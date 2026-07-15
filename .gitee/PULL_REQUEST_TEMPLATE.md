## 变更说明

<!-- 一句话:这个 PR 做了什么;新插件请写清能力与边界 -->

## 检查清单(投稿必填,CONTRIBUTING.md 有详细说明)

- [ ] `python3 scripts/gen_registry.py` 已跑,registry.json 与插件改动同 commit
- [ ] `python3 scripts/ci_check.py` 全绿(manifest/version 递增/禁 import 面/危险模式)
- [ ] `python3 tests/conformance.py` 全绿(零配置全接口族无裸异常)
- [ ] 只 import 契约面(SPEC §3.2);三方 SDK 惰性 import 且缺包有引导文案
- [ ] register(ctx) 零副作用;is_available() 正确反映凭据/endpoint 状态
- [ ] 网络访问只指向 provider 官方 endpoint 或用户配置的 endpoint;秘钥不落日志
- [ ] README 写清:能力/凭据获取方式/(私有化)Runtime 部署指引
- [ ] (改既有插件)version 已递增;(引第三方代码)README 已逐项声明来源与许可

## 实测情况

<!-- 哪些路径真实调过厂商 API/运行时?哪些是待联调?诚实标注 -->
