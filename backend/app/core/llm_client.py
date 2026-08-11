"""Provider-agnostic LLM generation clients."""

from abc import ABC, abstractmethod
from typing import Any

from app.config import get_settings


class LLMClient(ABC):
    """Define the text-generation boundary used by services."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text from explicit system and user prompts or raise on provider failure."""


class GroqLLMClient(LLMClient):
    """Generate completions through Groq's OpenAI-compatible API."""

    def __init__(self, model: str = "llama-3.3-70b-versatile") -> None:
        from groq import AsyncGroq

        settings = get_settings()
        self._client: Any = AsyncGroq(api_key=settings.groq_api_key.get_secret_value())
        self._model = model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the first text completion, failing when the provider returns no content."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Groq returned an empty completion")
        return content
