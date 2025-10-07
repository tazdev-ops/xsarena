import json
import os
from datetime import datetime
from typing import Any, Dict

# Try to import prometheus_client, but don't fail if not available
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

    PROMETHEUS_AVAILABLE = True

    # Define metrics
    XSA_LLM_TOKENS_TOTAL = Counter(
        "xsarena_llm_tokens_total",
        "Total LLM tokens processed",
        ["job_id", "model", "direction"],  # direction: input or output
    )

    XSA_LLM_COST_USD_TOTAL = Counter("xsarena_llm_cost_usd_total", "Total estimated cost in USD", ["job_id", "model"])

    XSA_JOB_DURATION_SECONDS = Histogram(
        "xsarena_job_duration_seconds", "Duration of job execution in seconds", ["job_id", "status"]
    )

    XSA_JOB_ACTIVE_GAUGE = Gauge("xsarena_job_active", "Number of currently active jobs", ["job_id"])

except ImportError:
    PROMETHEUS_AVAILABLE = False


def write_event(job_id: str, event: Dict[str, Any]) -> None:
    """Write an event to the job's events log"""
    job_dir = os.path.join(".xsarena", "jobs", job_id)
    events_path = os.path.join(job_dir, "events.jsonl")

    event["ts"] = datetime.now().isoformat()
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    # Track metrics if prometheus is available
    if PROMETHEUS_AVAILABLE:
        if event.get("type") == "cost":
            # Track token counts and costs
            input_tokens = event.get("input_tokens", 0)
            output_tokens = event.get("output_tokens", 0)
            est_usd = event.get("est_usd", 0.0)
            model = event.get("model", "unknown")

            if input_tokens:
                XSA_LLM_TOKENS_TOTAL.labels(job_id=job_id, model=model, direction="input").inc(input_tokens)
            if output_tokens:
                XSA_LLM_TOKENS_TOTAL.labels(job_id=job_id, model=model, direction="output").inc(output_tokens)
            if est_usd:
                XSA_LLM_COST_USD_TOTAL.labels(job_id=job_id, model=model).inc(est_usd)


def aggregate_counters(job_id: str) -> Dict[str, int]:
    """Aggregate simple counters from the events log"""
    job_dir = os.path.join(".xsarena", "jobs", job_id)
    events_path = os.path.join(job_dir, "events.jsonl")

    if not os.path.exists(events_path):
        return {"chunks": 0, "retries": 0, "stalls": 0}

    counters = {"chunks": 0, "retries": 0, "stalls": 0}
    with open(events_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    event = json.loads(line.strip())
                    if event.get("type") == "chunk_done":
                        counters["chunks"] += 1
                    elif event.get("type") == "retry":
                        counters["retries"] += 1
                    elif event.get("type") == "stall":
                        counters["stalls"] += 1
                except json.JSONDecodeError:
                    continue

    return counters


def get_metrics():
    """Get Prometheus metrics in text format"""
    if PROMETHEUS_AVAILABLE:
        return generate_latest().decode("utf-8")
    else:
        return "# Prometheus metrics not available - install prometheus-client\n"


def track_job_start(job_id: str):
    """Track when a job starts"""
    if PROMETHEUS_AVAILABLE:
        XSA_JOB_ACTIVE_GAUGE.labels(job_id=job_id).set(1)


def track_job_end(job_id: str, status: str, duration: float):
    """Track when a job ends"""
    if PROMETHEUS_AVAILABLE:
        XSA_JOB_ACTIVE_GAUGE.labels(job_id=job_id).set(0)
        XSA_JOB_DURATION_SECONDS.labels(job_id=job_id, status=status).observe(duration)
