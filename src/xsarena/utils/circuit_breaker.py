"""Circuit breaker implementation for XSArena."""

import time
from enum import Enum
from typing import Any, Callable, Type


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Tripped, requests blocked
    HALF_OPEN = "half_open"  # Testing if we can close


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 15.0,
        expected_exception: Type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._opened_time = 0.0

    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state."""
        # Check if we should transition from OPEN to HALF_OPEN
        if (
            self._state == CircuitState.OPEN
            and time.time() - self._opened_time >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
        return self._state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            raise RuntimeError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    async def async_call(self, func, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            raise RuntimeError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful operation."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0

    def _on_failure(self):
        """Handle failed operation."""
        self._failure_count += 1

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_time = time.time()

    def reset(self):
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._opened_time = 0.0


class CircuitBreakerTransport:
    """Wrapper that adds circuit breaker functionality to a transport."""

    def __init__(
        self, transport, failure_threshold: int = 3, recovery_timeout: float = 15.0
    ):
        self.transport = transport
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=(RuntimeError, ConnectionError),
        )

    async def send(self, payload):
        """Send payload with circuit breaker protection."""
        return await self.circuit_breaker.async_call(self.transport.send, payload)

    async def health_check(self):
        """Perform health check."""
        try:
            result = await self.circuit_breaker.async_call(self.transport.health_check)
            return result
        except Exception:
            return False

    async def stream_events(self):
        """Stream events."""
        return await self.circuit_breaker.async_call(self.transport.stream_events)

    @property
    def circuit_breaker_state(self):
        """Get the current circuit breaker state."""
        return self.circuit_breaker.state

    @property
    def base_url(self):
        """Delegate base_url to wrapped transport if it exists."""
        if hasattr(self.transport, "base_url"):
            return self.transport.base_url
        return getattr(self.transport, "base_url", "unknown")
