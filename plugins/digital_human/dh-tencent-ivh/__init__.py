"""腾讯云智能数智人(IVH) — TotalClaw 数字人 provider 插件(自包含,仅 import 契约面)。"""


def register(ctx):
    from .provider import TencentIvhBackend

    from totalclaw_core.plugins.digital_human import register_backend

    register_backend(TencentIvhBackend())
    ctx.logger.info("digital_human provider registered: tencent_ivh")
