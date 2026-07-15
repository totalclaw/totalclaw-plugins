#!/bin/sh
# LiveTalking Runtime GPU 镜像构建(R-11②)。需 CUDA 构建环境。
set -eu

LIVETALKING_REF="${LIVETALKING_REF:?请设置 LIVETALKING_REF=上游 pin 的 commit/tag(禁 latest)}"
VERSION="${VERSION:?请设置 VERSION=运行时包版本,如 0.1.0}"
IMAGE="totalclaw/livetalking-runtime:${VERSION}"

cd "$(dirname "$0")"
docker build \
  --build-arg LIVETALKING_REF="${LIVETALKING_REF}" \
  -t "${IMAGE}" .
echo "构建完成:${IMAGE}(权重不在镜像内,部署时按 runtime.yaml 工件挂载 models/)"
