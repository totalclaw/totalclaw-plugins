#!/bin/sh
# DUIX Runtime 镜像构建(R-10②)。工件不进仓;digest 用 backfill_runtime_digest.py 回填。
set -eu

DUIX_REF="${DUIX_REF:?请设置 DUIX_REF=上游 pin 的 commit/tag(供应链要求:禁 latest)}"
VERSION="${VERSION:?请设置 VERSION=运行时包版本,如 0.1.0}"
IMAGE="totalclaw/duix-runtime:${VERSION}"

cd "$(dirname "$0")"
docker build \
  --build-arg DUIX_REF="${DUIX_REF}" \
  -t "${IMAGE}" .
echo "构建完成:${IMAGE}"
echo "下一步:docker push 到 cn/intl 双源,然后 backfill_runtime_digest.py 回填 runtime.yaml"
