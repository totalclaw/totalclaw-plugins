"""DUIX 私有化(CPU 轻量档) — TotalClaw 数字人 provider 插件(自包含,仅 import 契约面)。"""


def register(ctx):
    from .provider import DuixLocalBackend

    from totalclaw_core.plugins.digital_human import register_backend

    register_backend(DuixLocalBackend())
    ctx.logger.info("digital_human provider registered: duix_local")
