"""HeyGen LiveAvatar provider 适配器(薄客户端,零重依赖)。

自包含铁律(SPEC.md §3):只 import totalclaw_core.plugins.digital_human 契约面 +
标准库/httpx;重 SDK/运行时永不进插件,方法内惰性处理。
"""
from totalclaw_core.plugins.digital_human import DigitalHumanBackendBase


class HeygenBackend(DigitalHumanBackendBase):
    name = "heygen"
    require_env = ['HEYGEN_API_KEY']

    # 元数据(agent 分区路由与 status 工具消费)
    region = "overseas"      # cn / overseas / local
    kind = "cloud"          # cloud / selfhosted
    modes = ['offline', 'realtime']

    # —— 脚手架状态:以下方法为骨架,按 PLUGINS_REPO_TODO 对应任务实现 ——

    def synthesize(self, *args, **kwargs):
        return {
            "success": False,
            "error": (
                "HeyGen LiveAvatar provider 尚未实现(插件为脚手架版)。"
                "实现进度见 totalclaw-plugins 仓 PLUGINS_REPO_TODO。"
            ),
        }

    def query_task(self, *args, **kwargs):
        return {"success": False, "error": "HeyGen LiveAvatar provider 尚未实现"}
