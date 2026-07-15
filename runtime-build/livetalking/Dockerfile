# LiveTalking Runtime(GPU 高保真档)。权重为独立工件(部署时挂载 /app/models)。
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ARG LIVETALKING_REF
RUN test -n "${LIVETALKING_REF}" || (echo "必须指定 LIVETALKING_REF(pin 上游 commit,禁 latest)" && exit 1)

RUN apt-get update && apt-get install -y --no-install-recommends \
      git python3 python3-pip ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN git clone https://github.com/lipku/LiveTalking.git . \
    && git checkout "${LIVETALKING_REF}" \
    && pip3 install --no-cache-dir -r requirements.txt

EXPOSE 8010
# 权重目录由部署层挂载(runtime.yaml musetalk-weights 工件 → /app/models)
CMD ["python3", "app.py", "--transport", "webrtc", "--model", "musetalk", "--listenport", "8010"]
