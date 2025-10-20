"""Metrics tracking logic for XSArena chunk processing."""

import logging

from ....utils.density import avg_sentence_len, filler_rate, lexical_density
from ..model import JobV3

logger = logging.getLogger(__name__)


async def apply_lossless_metrics_and_compression(
    content: str, job: JobV3, chunk_idx: int, job_store, transport, session_state=None
) -> str:
    """
    Apply lossless metrics computation and optional compression pass.

    Args:
        content: Content to analyze and potentially compress
        job: The current job object
        chunk_idx: Current chunk index
        job_store: Job store for logging
        transport: Backend transport for compression API calls
        session_state: Session state for configuration

    Returns:
        Potentially compressed content
    """
    # Compute metrics
    ld = lexical_density(content)
    fr = filler_rate(content)
    asl = avg_sentence_len(content)
    job_store._log_event(
        job.id,
        {
            "type": "density_metrics",
            "chunk_idx": chunk_idx,
            "lexical_density": round(ld, 4),
            "filler_per_k": round(fr, 2),
            "avg_sentence_len": round(asl, 2),
        },
    )

    # Check if compression should be enforced
    enforce = (
        bool(getattr(session_state, "lossless_enforce", False))
        if session_state
        else False
    )
    target_density = (
        float(getattr(session_state, "target_density", 0.55)) if session_state else 0.55
    )
    max_adverbs_k = (
        int(getattr(session_state, "max_adverbs_per_k", 15)) if session_state else 15
    )
    max_sent_len = (
        int(getattr(session_state, "max_sentence_len", 22)) if session_state else 22
    )

    needs_compress = enforce and (
        ld < target_density or fr > max_adverbs_k or asl > max_sent_len
    )

    if needs_compress:
        compress_prompt = (
            "Lossless compression pass: Rewrite the EXACT content below to higher density.\n"
            "- Preserve every fact and entailment.\n"
            "- Remove fillers/hedges; avoid generic transitions.\n"
            "- Do not add or remove claims.\n"
            "CONTENT:\n<<<CHUNK\n" + content + "\nCHUNK>>>"
        )
        extend_payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precision editor enforcing a lossless compression contract.",
                },
                {"role": "user", "content": compress_prompt},
            ],
            "model": (
                job.run_spec.model
                if hasattr(job.run_spec, "model") and job.run_spec.model
                else "gpt-4o"
            ),
        }
        try:
            compress_resp = await transport.send(extend_payload)
            new_content = (
                compress_resp.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if new_content and len(new_content.strip()) > 0:
                content = new_content.strip()
                # Recompute metrics after compress
                ld2 = lexical_density(content)
                fr2 = filler_rate(content)
                asl2 = avg_sentence_len(content)
                job_store._log_event(
                    job.id,
                    {
                        "type": "compress_pass",
                        "chunk_idx": chunk_idx,
                        "before": {
                            "ld": round(ld, 4),
                            "fr": round(fr, 2),
                            "asl": round(asl, 2),
                        },
                        "after": {
                            "ld": round(ld2, 4),
                            "fr": round(fr2, 2),
                            "asl": round(asl2, 2),
                        },
                    },
                )
        except Exception:
            # If compress fails, proceed with content as-is
            job_store._log_event(
                job.id,
                {
                    "type": "compress_pass_failed",
                    "chunk_idx": chunk_idx,
                },
            )

    return content
