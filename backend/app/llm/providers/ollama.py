"""Ollama LLM provider — local model execution via the Ollama HTTP API."""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.llm.base import HealthCheckResult, LLMProvider, LLMResponse
from app.llm.circuit_breaker import CircuitBreaker, call_with_retry


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b-instruct",
        vision_model: str | None = None,
        timeout_seconds: int = 60,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.vision_model = vision_model or model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds)
        return self._client

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        resp = await self.client.post(path, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_schema: type[Any] | None = None,
        stream: bool = False,
    ) -> LLMResponse:
        import time as _t

        start = _t.monotonic()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
        if response_schema is not None:
            # Ollama supports JSON schema via "format" field
            payload["format"] = response_schema.model_json_schema() if hasattr(response_schema, "model_json_schema") else str(response_schema)

        try:
            data = await self._post("/api/chat", payload)
        except httpx.HTTPError:
            return LLMResponse(
                text="",
                tool_calls=[],
                usage={},
                latency_ms=(_t.monotonic() - start) * 1000,
                provider=self.name,
                model=self.model,
            )

        message = data.get("message", {})
        text = message.get("content", "") or ""
        tool_calls = message.get("tool_calls", []) or []
        usage = data.get("usage", {})

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            latency_ms=(_t.monotonic() - start) * 1000,
            provider=self.name,
            model=self.model,
        )

    async def vision_extract(
        self,
        image_bytes: bytes,
        schema: dict[str, Any],
    ) -> LLMResponse:
        import base64
        import time as _t

        start = _t.monotonic()
        # Ollama vision: embed base64 image in the message
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        payload: dict[str, Any] = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": "Extract the fields from this document according to the JSON schema: " + json.dumps(schema),
                    "images": [b64],
                }
            ],
            "stream": False,
            "format": schema,
        }
        try:
            data = await self._post("/api/chat", payload)
            message = data.get("message", {})
            text = message.get("content", "") or ""
        except httpx.HTTPError:
            text = ""

        return LLMResponse(
            text=text,
            tool_calls=[],
            usage={},
            latency_ms=(_t.monotonic() - start) * 1000,
            provider=self.name,
            model=self.vision_model,
        )

    async def health_check(self) -> HealthCheckResult:
        import time as _t
        start = _t.monotonic()
        try:
            data = await self._post("/api/tags", {})
            models = [m.get("name", "") for m in data.get("models", [])]
            model_available = any(self.model in m for m in models)
            latency = (_t.monotonic() - start) * 1000
            return HealthCheckResult(
                healthy=model_available,
                latency_ms=latency,
                error=None if model_available else f"model {self.model} not found",
                provider=self.name,
                model=self.model,
            )
        except Exception as err:
            return HealthCheckResult(
                healthy=False,
                latency_ms=(_t.monotonic() - start) * 1000,
                error=str(err),
                provider=self.name,
                model=self.model,
            )


_ollama_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)


async def ollama_chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    response_schema: type[Any] | None = None,
    stream: bool = False,
    base_url: str = "http://localhost:11434",
    model: str = "qwen2.5:7b-instruct",
) -> LLMResponse:
    provider = OllamaProvider(base_url=base_url, model=model)
    return await call_with_retry(
        provider.chat, messages, tools=tools, response_schema=response_schema,
        stream=stream, max_retries=provider.max_retries,
        base_delay=1.0, max_delay=4.0, breaker=_ollama_breaker,
    )
