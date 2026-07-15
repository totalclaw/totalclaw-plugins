"""LiveTalking 私有化(GPU 高保真档) — TotalClaw 数字人 provider 插件(自包含,仅 import 契约面)。"""


def register(ctx):
    from .provider import LivetalkingLocalBackend

    from totalclaw_core.plugins.digital_human import register_backend

    register_backend(LivetalkingLocalBackend())
    ctx.logger.info("digital_human provider registered: livetalking_local")
