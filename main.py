import httpx
from urllib.parse import quote

from core.plugin import BasePlugin, logger, on
from core.provider import LLMRequest

from core.utils.tool_utils import BaseTool


class NtfyTool(BaseTool):
    name = "ntfy"
    description = "Push notifications to ntfy"
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "title (optional)"},
            "msg": {"type": "string", "description": "notification content"}
        },
        "required": ["msg"]
    }

    def __init__(self, cfg: dict):
        super().__init__()
        self._url = cfg.get("topic_url", "")

    async def execute(self, event, *_, msg: str, title: str = None) -> str:
        headers = {}
        if title:
            headers["Title"] = quote(title)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._url,
                content=msg.encode(encoding="utf-8"),
                headers=headers
            )
            return resp.text


class NtfyPlugin(BasePlugin):
    def __init__(self, ctx, cfg: dict):
        super().__init__(ctx, cfg)
        self.url = cfg.get("topic_url", "")
        self.as_tool = cfg.get("as_tool", False)

    async def initialize(self):
        logger.info(f"[Ntfy] URL: {self.url}")
        logger.info(f"[Ntfy] LLM Tool: {self.as_tool}")

    async def terminate(self):
        pass

    @on.llm_request()
    async def inject_ntfy_tool(self, _event, req: LLMRequest, *_):
        if self.as_tool:
            req.tool_set.add(
                NtfyTool(cfg=self.plugin_cfg)
            )

    async def push_notification(self, msg: str, title: str = None) -> str:
        """Expose to other plugins"""
        headers = {}
        if title:
            headers["Title"] = quote(title)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.url,
                data=msg.encode(encoding="utf-8"),
                headers=headers
            )
            return resp.json()
