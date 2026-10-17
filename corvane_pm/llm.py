"""LLM and embedding adapters for an OpenAI-compatible endpoint (local Ollama).

machina's ``LLMProvider`` calls LiteLLM but has no base-URL or API-key
argument, so this subclass injects them on every call. With
``LLM_MODEL=qwen2.5:7b`` LiteLLM is called as ``openai/qwen2.5:7b`` against
``LLM_BASE_URL``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
from langchain_core.embeddings import Embeddings
from machina.llm.provider import LLMProvider

if TYPE_CHECKING:
    from machina.observability.tracing import ActionTracer

    from corvane_pm.config import LLMSettings


class OpenAICompatProvider(LLMProvider):
    """machina LLMProvider pointed at an OpenAI-compatible base URL."""

    def __init__(self, settings: LLMSettings, *, tracer: ActionTracer | None = None) -> None:
        super().__init__(
            model=f"openai/{settings.model}",
            temperature=0.1,
            max_tokens=settings.max_tokens,
            request_timeout=settings.timeout_s,
            tracer=tracer,
        )
        self._api_base = settings.base_url
        self._api_key = settings.api_key

    def _inject(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        kwargs.setdefault("api_base", self._api_base)
        kwargs.setdefault("api_key", self._api_key)
        return kwargs

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return await super().complete(messages, **self._inject(kwargs))

    async def complete_with_tools(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        return await super().complete_with_tools(messages, tools, **self._inject(kwargs))


class OpenAICompatEmbeddings(Embeddings):
    """LangChain embeddings over ``POST {base_url}/embeddings`` (e.g. nomic-embed-text)."""

    def __init__(self, settings: LLMSettings, *, batch_size: int = 16) -> None:
        self._url = f"{settings.base_url}/embeddings"
        self._headers = {"Authorization": f"Bearer {settings.api_key}"}
        self._model = settings.embed_model
        self._timeout = settings.timeout_s
        self._batch = batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        with httpx.Client(timeout=self._timeout) as client:
            for start in range(0, len(texts), self._batch):
                batch = texts[start : start + self._batch]
                resp = client.post(self._url, headers=self._headers,
                                   json={"model": self._model, "input": batch})
                resp.raise_for_status()
                data = sorted(resp.json()["data"], key=lambda d: d["index"])
                vectors.extend(d["embedding"] for d in data)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
