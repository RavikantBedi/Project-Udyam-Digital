"""LLM provider interface — provider-agnostic abstraction for chat and vision."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Normalised response from any LLM provider."""
    text: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float
    provider: str
    model: str
    raw: dict[str, Any] | None = None


class HealthCheckResult(BaseModel):
    """Result of a provider health check."""
    healthy: bool
    latency_ms: float | None = None
    error: str | None = None
    provider: str
    model: str


class LLMProvider(ABC):
    """Abstract base class for all LLM providers.

    Implementations must normalise their provider-specific response into
    :class:`LLMResponse`.  All network calls must honour ``timeout_seconds``
    and implement retry-with-backoff via the circuit breaker.
    """

    name: str
    timeout_seconds: int = 30
    max_retries: int = 3

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_schema: type[BaseModel] | None = None,
        stream: bool = False,
    ) -> LLMResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def vision_extract(
        self,
        image_bytes: bytes,
        schema: dict[str, Any],
    ) -> LLMResponse:
        """Extract structured fields from a document image."""
        ...

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """Return provider health (latency, error, model availability)."""
        ...
