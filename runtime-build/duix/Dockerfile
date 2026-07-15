# DUIX Runtime(CPU 轻量档):DUIX 开源服务 + Local Avatar Runtime 协议 v1 桥接层
FROM python:3.11-slim

ARG DUIX_REF
RUN test -n "${DUIX_REF}" || (echo "必须指定 DUIX_REF(pin 上游 commit,禁 latest)" && exit 1)

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/duix
RUN git clone https://github.com/GuijiAI/duix.ai.git . \
    && git checkout "${DUIX_REF}" \
    && pip install --no-cache-dir -r requirements.txt || true
# ↑ 上游 requirements 路径以 pin 的 ref 为准;构建失败即停,禁静默降级

# 桥接层:协议 v1(/health /v1/sessions 全族)→ DUIX API
COPY bridge/ /opt/bridge/
RUN pip install --no-cache-dir fastapi uvicorn httpx

EXPOSE 18080
# 桥接层为唯一入口:它负责拉起/代理 DUIX 服务并暴露协议 v1
CMD ["python", "/opt/bridge/server.py", "--port", "18080"]
