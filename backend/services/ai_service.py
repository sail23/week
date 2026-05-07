"""
OpenAI 范式 AI 服务封装。
使用 aiohttp 进行 HTTP 调用，避免 httpx 在某些 Windows 环境下的 TLS 兼容性问题。
支持流式输出和多轮对话上下文。
"""
import json
from typing import AsyncIterator, List, Dict, Any, Optional
import aiohttp
from config import settings


class AIService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=300, connect=30)
            self._session = aiohttp.ClientSession(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _build_messages(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    async def generate_stream(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        messages = self._build_messages(user_message, system_prompt, history)
        session = await self._get_session()

        async with session.post(
            "/v1/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "stream": True,
            },
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(
                    f"AI API 返回错误 {response.status}: {text}"
                )

            async for line in response.content:
                line = line.decode("utf-8", errors="replace").strip()
                if not line or line.startswith(":"):
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue

    async def generate(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        messages = self._build_messages(user_message, system_prompt, history)
        session = await self._get_session()

        async with session.post(
            "/v1/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
            },
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"AI API 返回错误 {resp.status}: {text}")

            data = await resp.json()
            return (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )


ai_service = AIService()
