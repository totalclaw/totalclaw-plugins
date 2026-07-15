"""CHANGEME — TotalClaw 数字人 provider 插件(自包含,仅 import 契约面)。"""


def register(ctx):
    from .provider import ChangeMeBackend

    from totalclaw_core.plugins.digital_human import register_backend

    register_backend(ChangeMeBackend())
    ctx.logger.info("digital_human provider registered: changeme")
