"""Anthropic LLM provider — official Python SDK."""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.llm.base import HealthCheckResult, LLMProvider, LLMResponse
from app.llm.circuit_breaker import CircuitBreaker, call_with_retry


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        vision_model: str | None = None,
        timeout_seconds: int = 60,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.vision_model = vision_model or model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.anthropic.com",
                timeout=self.timeout_seconds,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
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
        # Convert roles: anthropic uses "user" / "assistant" / "system"
        system = ""
        anthropic_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system = content
                continue
            anthropic_messages.append({"role": role, "content": content})

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = tools
        if response_schema is not None:
            payload["tool_choice"] = {"type": "tool", "name": "extract_fields"}
            payload["tools"] = payload.get("tools", []) + [
                {
                    "name": "extract_fields",
                    "description": "Extract fields matching the schema",
                    "input_schema": response_schema.model_json_schema() if hasattr(response_schema, "model_json_schema") else {"type": "object"},
                }
            ]

        try:
            data = await self._post("/v1/messages", payload)
        except httpx.HTTPError:
            return LLMResponse(
                text="",
                tool_calls=[],
                usage={},
                latency_ms=(_t.monotonic() - start) * 1000,
                provider=self.name,
                model=self.model,
            )

        text = ""
        tool_calls = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(block)

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
        mime = "image/png"
        if image_bytes[:2] == b"\xff\xd8":
            mime = "image/jpeg"
        payload: dict[str, Any] = {
            "model": self.vision_model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract fields per this JSON schema: " + json.dumps(schema)},
                        {"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}},
                    ],
                }
            ],
        }
        try:
            data = await self._post("/v1/messages", payload)
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
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
            # Minimal message to verify connectivity
            payload = {
                "model": self.model,
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "ping"}],
            }
            await self._post("/v1/messages", payload)
            latency = (_t.monotonic() - start) * 1000
            return HealthCheckResult(
                healthy=True,
                latency_ms=latency,
                error=None,
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


_anthropic_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)


async def anthropic_chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    response_schema: type[Any] | None = None,
    stream: bool = False,
    api_key: str = "",
    model: str = "claude-3-5-sonnet-20241022",
) -> LLMResponse:
    provider = AnthropicProvider(api_key=api_key, model=model)
    return await call_with_retry(
        provider.chat, messages, tools=tools, response_schema=response_schema,
        stream=stream, max_retries=provider.max_retries,
        base_delay=1.0, max_delay=4.0, breaker=_anthropic_breaker,
    )
