import asyncio
import httpx
import json
from urllib.parse import quote
from pathlib import Path

from core.plugin import BasePlugin, logger, on
from core.provider import LLMRequest

from core.chat.message_utils import MessageChain
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
        self.emoji_json = {}
        self.recv_topics = {}
        self._listening_topic_tasks: list[asyncio.Task] = list()

    async def initialize(self):
        logger.info(f"[Ntfy] URL: {self.url}")
        logger.info(f"[Ntfy] LLM Tool: {self.as_tool}")

        base_dir = Path(__file__).parent
        emoji_path = base_dir / "emoji.json"

        try:
            with open(emoji_path, 'r', encoding="utf-8") as f:
                self.emoji_json = json.loads(f.read())
        except Exception as e:
            logger.warning(f"[Ntfy] Failed to load emoji.json: {e}")

        self.recv_topics = self.plugin_cfg.get("recv_topics", {})

        if self.recv_topics:
            await self.listen_topics()

    async def terminate(self):
        for task in self._listening_topic_tasks:
            task.cancel()
        if self._listening_topic_tasks:
            await asyncio.gather(*self._listening_topic_tasks, return_exceptions=True)

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

    async def listen_topics(self):
        for _, topic_config in self.recv_topics.items():
            if not isinstance(topic_config, dict):
                logger.warning(f"[Ntfy] Invalid topic config: {topic_config}")
                continue

            topic_url = topic_config.get("url", "")
            sessions = topic_config.get("sessions", [])

            if not topic_url or not sessions:
                continue

            logger.info(f"[Ntfy] Listening to {topic_url}, sessions subscribed: {sessions}")
            if not isinstance(sessions, list):
                sessions = []

            self._listening_topic_tasks.append(
                asyncio.create_task(
                    self.listen_to_topic(topic_url, sessions)
                )
            )

    async def listen_to_topic(self, topic_url: str, sessions: list):
        client = httpx.AsyncClient(timeout=None)
        try:
            async with client.stream("GET", f"{topic_url.rstrip('/')}/json") as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue

                    msg_json = json.loads(line)
                    event = msg_json.get("event", "")

                    if event == "message":
                        raw_title = msg_json.get("title", "")
                        title = msg_json.get("title", f"{topic_url.split('://')[-1]}")
                        msg = msg_json.get("message", "")
                        tags = msg_json.get("tags", [])
                        click_url = msg_json.get("click", "")

                        if tags:
                            title_emoji = ""

                            for tag in tags:
                                emoji = self.emoji_json.get(tag, "")
                                if emoji:
                                    title_emoji += f"{emoji} "

                            if raw_title:
                                title = title_emoji + title
                            else:
                                msg = title_emoji + msg

                        ntfy_notice = f"[Ntfy] Notice received:\nTitle: {title}\nMessage: {msg}"
                        if click_url:
                            ntfy_notice += f"\nClick URL: {click_url}"

                        for session in sessions:
                            chain = MessageChain().text(ntfy_notice)
                            await self.ctx.publish_notice(session=session, chain=chain)
        except Exception as e:
            logger.error(f"[Ntfy] {topic_url} error: {e}")
