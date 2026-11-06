"""Provider manager — chains LLM providers with circuit-breaker fallback."""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.llm.base import HealthCheckResult, LLMProvider, LLMResponse
from app.llm.circuit_breaker import CircuitBreaker, call_with_retry
from app.llm.encryption import SecretStore
from app.llm.pii import PIIRedactor, assert_no_raw_pii
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.offline import OfflineProvider
from app.llm.providers.ollama import OllamaProvider
from app.llm.providers.openai_compatible import (
    OpenAICompatibleProvider,
)

logger = logging.getLogger("accel.llm")


class ProviderManager:
    """Manages a prioritised list of LLM providers with circuit-breaker fallback.

    The last provider in the chain is always the offline provider, so the
    demo never fails completely.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.secret_store = SecretStore(self.settings.app_encryption_key)
        self._providers: list[LLMProvider] = []
        self._breakers: list[CircuitBreaker] = []
        self._last_health: dict[str, HealthCheckResult] = {}
        self._build_chain()

    # ------------------------------------------------------------------
    # Chain building
    # ------------------------------------------------------------------
    def _build_chain(self) -> None:
        providers: list[tuple[LLMProvider, CircuitBreaker]] = []

        provider_name = self.settings.llm_provider

        # Ollama
        if provider_name in ("ollama", "auto") or self._ollama_configured():
            providers.append((
                OllamaProvider(
                    base_url=self.settings.ollama_base_url,
                    model=self.settings.llm_model or "qwen2.5:7b-instruct",
                    vision_model=self.settings.llm_vision_model or "qwen2.5vl",
                    timeout_seconds=self.settings.llm_timeout_seconds,
                    max_retries=self.settings.llm_max_retries,
                ),
                CircuitBreaker(
                    failure_threshold=self.settings.llm_circuit_breaker_threshold,
                    recovery_timeout=self.settings.llm_circuit_breaker_timeout_seconds,
                ),
            ))

        # Anthropic (only if API key configured)
        if self.settings.anthropic_api_key:
            providers.append((
                AnthropicProvider(
                    api_key=self.settings.anthropic_api_key,
                    model=self.settings.llm_model or "claude-3-5-sonnet-20241022",
                    vision_model=self.settings.llm_vision_model or "claude-3-5-sonnet-20241022",
                    timeout_seconds=self.settings.llm_timeout_seconds,
                    max_retries=self.settings.llm_max_retries,
                ),
                CircuitBreaker(
                    failure_threshold=self.settings.llm_circuit_breaker_threshold,
                    recovery_timeout=self.settings.llm_circuit_breaker_timeout_seconds,
                ),
            ))

        # OpenAI-compatible
        if self.settings.openai_api_key or self.settings.openai_base_url:
            providers.append((
                OpenAICompatibleProvider(
                    base_url=self.settings.openai_base_url or "https://api.openai.com/v1",
                    model=self.settings.llm_model or "gpt-4o-mini",
                    api_key=self.settings.openai_api_key,
                    timeout_seconds=self.settings.llm_timeout_seconds,
                    max_retries=self.settings.llm_max_retries,
                ),
                CircuitBreaker(
                    failure_threshold=self.settings.llm_circuit_breaker_threshold,
                    recovery_timeout=self.settings.llm_circuit_breaker_timeout_seconds,
                ),
            ))

        # Offline is always last
        providers.append((
            OfflineProvider(),
            CircuitBreaker(failure_threshold=999, recovery_timeout=60.0),
        ))

        self._providers = [p for p, _ in providers]
        self._breakers = [b for _, b in providers]

    def _ollama_configured(self) -> bool:
        import httpx
        try:
            resp = httpx.get(f"{self.settings.ollama_base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        response_schema: type[Any] | None = None,
        stream: bool = False,
        redact_pii: bool = True,
    ) -> LLMResponse:
        if redact_pii:
            messages = self._redact_messages(messages)

        for provider, breaker in zip(self._providers, self._breakers, strict=True):
            try:
                response = await call_with_retry(
                    provider.chat,
                    messages,
                    tools=tools,
                    response_schema=response_schema,
                    stream=stream,
                    max_retries=provider.max_retries,
                    base_delay=1.0,
                    max_delay=4.0,
                    breaker=breaker,
                )
                if redact_pii:
                    response.text = self._redactor.restore(response.text)
                # Safety: assert no raw PII leaked
                assert_no_raw_pii(response.text, "LLM response")
                return response
            except Exception:
                logger.warning("LLM provider %s failed", provider.name)
                continue

        # All providers failed — return error response
        return LLMResponse(
            text="I'm sorry, the advisor is temporarily unavailable. Please try again in a moment.",
            tool_calls=[],
            usage={},
            latency_ms=0.0,
            provider="offline",
            model="error",
        )

    async def vision_extract(
        self,
        image_bytes: bytes,
        schema: dict[str, Any],
        vision_enabled: bool = False,
    ) -> LLMResponse:
        if not vision_enabled:
            return LLMResponse(
                text="",
                tool_calls=[],
                usage={},
                latency_ms=0.0,
                provider="offline",
                model="vision_disabled",
            )

        for provider, breaker in zip(self._providers, self._breakers, strict=True):
            try:
                response = await call_with_retry(
                    provider.vision_extract,
                    image_bytes,
                    schema,
                    max_retries=provider.max_retries,
                    base_delay=1.0,
                    max_delay=4.0,
                    breaker=breaker,
                )
                return response
            except Exception:
                logger.warning("Vision provider %s failed", provider.name)
                continue

        return LLMResponse(
            text="",
            tool_calls=[],
            usage={},
            latency_ms=0.0,
            provider="offline",
            model="vision_error",
        )

    async def health_check_all(self) -> dict[str, HealthCheckResult]:
        results: dict[str, HealthCheckResult] = {}
        for provider in self._providers:
            try:
                result = await provider.health_check()
                results[provider.name] = result
            except Exception as err:
                results[provider.name] = HealthCheckResult(
                    healthy=False,
                    latency_ms=None,
                    error=str(err),
                    provider=provider.name,
                    model=getattr(provider, "model", "unknown"),
                )
        self._last_health = results
        return results

    @property
    def active_provider(self) -> str:
        return self._providers[0].name if self._providers else "offline"

    # ------------------------------------------------------------------
    # PII helpers
    # ------------------------------------------------------------------
    @property
    def _redactor(self) -> PIIRedactor:
        return PIIRedactor()

    def _redact_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        redacted = []
        for m in messages:
            new_m = dict(m)
            if isinstance(new_m.get("content"), str):
                new_m["content"] = self._redactor.redact(new_m["content"])
            redacted.append(new_m)
        return redacted

    def get_masked_api_key(self, provider_name: str) -> str:
        """Return masked API key for display (last 4 chars only)."""
        key = ""
        if provider_name == "anthropic":
            key = self.settings.anthropic_api_key or ""
        elif provider_name == "openai_compatible":
            key = self.settings.openai_api_key or ""
        return self.secret_store.mask(key)
