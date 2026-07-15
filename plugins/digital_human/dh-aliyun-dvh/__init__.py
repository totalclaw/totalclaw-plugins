"""阿里云数字人(DVH) — TotalClaw 数字人 provider 插件(自包含,仅 import 契约面)。"""


def register(ctx):
    from .provider import AliyunDvhBackend

    from totalclaw_core.plugins.digital_human import register_backend

    register_backend(AliyunDvhBackend())
    ctx.logger.info("digital_human provider registered: aliyun_dvh")
