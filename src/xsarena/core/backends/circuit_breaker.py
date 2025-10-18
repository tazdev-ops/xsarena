"""Circuit breaker implementation for XSArena transport."""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, List

from .transport import BackendTransport, BaseEvent

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Tripped, requests blocked
    HALF_OPEN = "half_open"  # Testing if failure condition is resolved


class CircuitBreakerTransport(BackendTransport):
    """Transport wrapper that adds circuit breaker functionality."""

    def __init__(
        self,
        wrapped_transport: BackendTransport,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        failure_ratio: float = 0.5,
    ):
        """
        Initialize circuit breaker wrapper.

        Args:
            wrapped_transport: The transport to wrap
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before allowing test requests
            failure_ratio: Ratio of failed requests that triggers the breaker
        """
        self.wrapped_transport = wrapped_transport
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_ratio = failure_ratio

        # Circuit breaker state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.total_requests = 0
        self.failed_requests = 0
        self._lock = asyncio.Lock()

    async def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a payload with circuit breaker protection."""
        async with self._lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    # Move to half-open state to test recovery
                    self.state = CircuitState.HALF_OPEN
                    logger.info(
                        "send_breaker_half_open",
                        extra={"transport": type(self.wrapped_transport).__name__},
                    )
                else:
                    # Still in open state, short-circuit with error
                    logger.warning(
                        "send_breaker_open",
                        extra={
                            "transport": type(self.wrapped_transport).__name__,
                            "reason": "circuit is open",
                        },
                    )
                    raise RuntimeError(
                        "Circuit breaker is open - temporarily unavailable; retrying soon"
                    )

            # If in half-open state, allow one request to test recovery
            if self.state == CircuitState.HALF_OPEN:
                # Allow this one request, then we'll update state based on result
                pass

        # Actually send the request (outside lock to avoid blocking other requests)
        try:
            result = await self.wrapped_transport.send(payload)

            # Update circuit breaker state on success
            async with self._lock:
                self.total_requests += 1
                if self.state == CircuitState.HALF_OPEN:
                    # Success in half-open state means we can close the circuit
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(
                        "send_retry",
                        extra={
                            "transport": type(self.wrapped_transport).__name__,
                            "status": "recovered",
                        },
                    )
                logger.info(
                    "send_success",
                    extra={"transport": type(self.wrapped_transport).__name__},
                )
            return result

        except Exception as e:
            # Update circuit breaker state on failure
            async with self._lock:
                self.total_requests += 1
                self.failed_requests += 1
                self.failure_count += 1
                self.last_failure_time = time.time()

                # Calculate failure rate
                failure_rate = self.failed_requests / max(self.total_requests, 1)

                # Check if we should open the circuit
                if (
                    self.failure_count >= self.failure_threshold
                    or failure_rate >= self.failure_ratio
                ):
                    self.state = CircuitState.OPEN
                    logger.warning(
                        "send_breaker_open",
                        extra={
                            "transport": type(self.wrapped_transport).__name__,
                            "failure_count": self.failure_count,
                            "failure_rate": failure_rate,
                            "total_requests": self.total_requests,
                            "failed_requests": self.failed_requests,
                        },
                    )
                else:
                    logger.warning(
                        "send_retry",
                        extra={
                            "transport": type(self.wrapped_transport).__name__,
                            "failure_count": self.failure_count,
                            "error": str(e),
                        },
                    )

            raise e

    async def health_check(self) -> bool:
        """Check health of wrapped transport."""
        return await self.wrapped_transport.health_check()

    async def stream_events(self) -> List[BaseEvent]:
        """Stream events from wrapped transport."""
        return await self.wrapped_transport.stream_events()
