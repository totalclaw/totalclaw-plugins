#!/bin/sh
# registry 签名 v2(R-14,期权):cosign 对 registry.json 签名,防仓库被篡改的纵深。
# agent 侧验签:tirith_security 已有完整验签模板(公钥随 agent 分发,验签失败拒绝解析)。
#
# 一次性(维护者,产出的 cosign.key 绝不进仓):
#   cosign generate-key-pair          # 私钥安全保管;cosign.pub 提交进仓
# 每次发布(gen_registry 之后):
#   ./scripts/sign_registry.sh        # 产出 registry.json.sig(与 registry 同 commit)
set -eu

cd "$(git rev-parse --show-toplevel)"
command -v cosign >/dev/null || { echo "需要 cosign:brew install cosign"; exit 2; }
KEY="${COSIGN_KEY:-cosign.key}"
[ -f "$KEY" ] || { echo "找不到签名私钥 $KEY(设 COSIGN_KEY 指定;私钥绝不进仓)"; exit 2; }

cosign sign-blob --key "$KEY" --output-signature registry.json.sig registry.json
echo "已签名:registry.json.sig(与 registry.json 同 commit 提交)"
echo "验签(客户端参考):cosign verify-blob --key cosign.pub --signature registry.json.sig registry.json"
