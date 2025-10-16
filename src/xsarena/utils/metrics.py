"""Metrics utilities with safe fallbacks when extras aren't installed."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import prometheus, but provide fallbacks
try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Define dummy classes that do nothing
    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

    def start_http_server(*args, **kwargs):
        pass


class MetricsCollector:
    """Metrics collector that safely falls back when prometheus isn't available."""

    def __init__(self):
        self._enabled = PROMETHEUS_AVAILABLE
        self._job_costs = {}  # Track costs in memory when prometheus unavailable

        if self._enabled:
            # Define metrics when prometheus is available
            self.tokens_used_total = Counter(
                "xsarena_tokens_used_total",
                "Total tokens used by XSArena",
                ["model", "type"],  # type: input/output
            )
            self.costs_total = Counter(
                "xsarena_costs_total", "Total estimated costs in USD", ["model"]
            )
            self.chunks_processed_total = Counter(
                "xsarena_chunks_processed_total", "Total chunks processed", ["task"]
            )
            self.job_duration_seconds = Histogram(
                "xsarena_job_duration_seconds", "Job duration in seconds", ["task"]
            )
            self.active_jobs = Gauge(
                "xsarena_active_jobs", "Number of currently active jobs"
            )
        else:
            # Initialize dummy attributes when prometheus unavailable
            self.tokens_used_total = Counter()
            self.costs_total = Counter()
            self.chunks_processed_total = Counter()
            self.job_duration_seconds = Histogram()
            self.active_jobs = Gauge()

    def record_tokens(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """Record token usage."""
        if self._enabled:
            self.tokens_used_total.labels(model=model, type="input").inc(input_tokens)
            self.tokens_used_total.labels(model=model, type="output").inc(output_tokens)
        # When prometheus unavailable, we could log or store in memory if needed

    def record_cost(self, model: str, cost: float) -> None:
        """Record estimated cost."""
        if self._enabled:
            self.costs_total.labels(model=model).inc(cost)
        # Store in memory when prometheus unavailable
        if model not in self._job_costs:
            self._job_costs[model] = 0.0
        self._job_costs[model] += cost

    def record_chunk_processed(self, task: str) -> None:
        """Record a chunk processed."""
        if self._enabled:
            self.chunks_processed_total.labels(task=task).inc()

    def record_job_duration(self, task: str, duration: float) -> None:
        """Record job duration."""
        if self._enabled:
            self.job_duration_seconds.labels(task=task).observe(duration)

    def set_active_jobs(self, count: int) -> None:
        """Set active jobs count."""
        if self._enabled:
            self.active_jobs.set(count)

    def get_total_cost(self, model: Optional[str] = None) -> float:
        """Get total cost, either for specific model or all models."""
        if self._enabled:
            # In a real prometheus setup, we'd query the counter
            # For fallback, return memory-stored value
            if model:
                return self._job_costs.get(model, 0.0)
            return sum(self._job_costs.values())
        else:
            return (
                self._job_costs.get(model, 0.0)
                if model
                else sum(self._job_costs.values())
            )

    def start_server(self, port: int = 8000) -> None:
        """Start metrics server if prometheus is available."""
        if self._enabled:
            start_http_server(port)
            print(f"Metrics server started on port {port}")
        else:
            print(
                "Metrics server not started (prometheus-client not installed). "
                "Install with: pip install xsarena[metrics]"
            )


# Global metrics instance
metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return metrics
