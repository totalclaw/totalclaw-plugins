"""NVIDIA ACE/Tokkio 私有化 — TotalClaw 数字人 provider 插件(自包含,仅 import 契约面)。"""


def register(ctx):
    from .provider import NvidiaAceBackend

    from totalclaw_core.plugins.digital_human import register_backend

    register_backend(NvidiaAceBackend())
    ctx.logger.info("digital_human provider registered: nvidia_ace")
