"""OpenAI-compatible LLM provider — covers OpenAI, Groq, OpenRouter, Together,
LM Studio, vLLM, and Gemini's OpenAI-compatible endpoint."""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.llm.base import HealthCheckResult, LLMProvider, LLMResponse
from app.llm.circuit_breaker import CircuitBreaker, call_with_retry


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        timeout_seconds: int = 60,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or ""
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds, headers=headers)
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
            payload["tool_choice"] = "required"
        if response_schema is not None:
            payload["response_format"] = {"type": "json_object"}
            # Append schema instruction to system message
            if payload["messages"] and payload["messages"][0].get("role") == "system":
                payload["messages"][0]["content"] += "\n\nRespond with JSON matching this schema: " + (
                    response_schema.model_json_schema() if hasattr(response_schema, "model_json_schema") else str(response_schema)
                )

        try:
            data = await self._post("/chat/completions", payload)
        except httpx.HTTPError:
            return LLMResponse(
                text="",
                tool_calls=[],
                usage={},
                latency_ms=(_t.monotonic() - start) * 1000,
                provider=self.name,
                model=self.model,
            )

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
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
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        # Detect image type from first bytes (simple heuristic)
        mime = "image/png"
        if image_bytes[:2] == b"\xff\xd8":
            mime = "image/jpeg"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract fields per this JSON schema: " + json.dumps(schema)},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            data = await self._post("/chat/completions", payload)
            message = data.get("choices", [{}])[0].get("message", {})
            text = message.get("content", "") or ""
        except httpx.HTTPError:
            text = ""

        return LLMResponse(
            text=text,
            tool_calls=[],
            usage={},
            latency_ms=(_t.monotonic() - start) * 1000,
            provider=self.name,
            model=self.model,
        )

    async def health_check(self) -> HealthCheckResult:
        import time as _t
        start = _t.monotonic()
        try:
            # Try models endpoint to verify connectivity
            resp = await self.client.get("/models")
            resp.raise_for_status()
            models = [m.get("id", "") for m in resp.json().get("data", [])]
            model_available = any(self.model in m for m in models) or not models
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


_openai_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)


async def openai_compatible_chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    response_schema: type[Any] | None = None,
    stream: bool = False,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> LLMResponse:
    provider = OpenAICompatibleProvider(base_url=base_url, model=model, api_key=api_key)
    return await call_with_retry(
        provider.chat, messages, tools=tools, response_schema=response_schema,
        stream=stream, max_retries=provider.max_retries,
        base_delay=1.0, max_delay=4.0, breaker=_openai_breaker,
    )
