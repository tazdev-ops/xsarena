import os

import aiohttp

from .backends import Backend, Message


class OllamaBackend(Backend):
    def __init__(self, base: str | None = None, model: str | None = None):
        self.base = base or os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434")
        self.model = model or "llama3"

    async def send(self, messages: list[Message], stream: bool = False) -> str:
        url = self.base.rstrip("/") + "/api/chat"
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=600) as resp:
                j = await resp.json()
                # Expect {"message":{"content":"..."}} or similar; adapt as needed
                try:
                    return j["message"]["content"]
                except Exception:
                    # Some ollama versions return "response": "..."
                    return j.get("response", "")
