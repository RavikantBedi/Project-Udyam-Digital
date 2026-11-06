"""Circuit breaker with retry + exponential backoff for LLM provider calls."""
from __future__ import annotations

import asyncio
import time
from enum import Enum
from typing import Any


class CircuitState(str, Enum):  # noqa: UP042 — str+Enum intentional for JSON serialization
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # failing fast, skip to next provider
    HALF_OPEN = "half_open"  # probing recovery


class CircuitBreaker:
    """Circuit breaker that trips after ``failure_threshold`` consecutive
    failures and stays open for ``recovery_timeout`` seconds."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        now = time.monotonic()
        if self._state == CircuitState.OPEN:
            if self._opened_at and now - self._opened_at >= self.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        if self._state != CircuitState.OPEN and self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def allow_request(self) -> bool:
        return self.state != CircuitState.OPEN


async def call_with_retry(
    func,
    *args,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    breaker: CircuitBreaker | None = None,
    **kwargs: Any,
) -> Any:
    """Call ``func`` with exponential backoff and optional circuit breaker.

    On failure, retries with ``base_delay * 2^attempt`` seconds sleep,
    capped at ``max_delay``.  If a circuit breaker is provided and its
    circuit is open, the call is skipped and a ``CircuitOpenError`` is raised.
    """
    if breaker is not None and not breaker.allow_request():
        raise CircuitOpenError("circuit breaker is open")

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            if breaker is not None:
                breaker.record_success()
            return result
        except Exception as err:
            last_error = err
            if breaker is not None:
                breaker.record_failure()
            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open and the call is skipped."""
