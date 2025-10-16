"""Job runner implementation for XSArena v0.3."""
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime

from pydantic import BaseModel
from ..backends.transport import BackendTransport, BaseEvent
from ..v2_orchestrator.specs import RunSpecV2
from ..jsonio import load_json_auto


class JobV3(BaseModel):
    """Version 3 job model with typed fields."""
    id: str
    name: str
    run_spec: RunSpecV2
    backend: str
    state: str = "PENDING"  # PENDING/RUNNING/STALLED/RETRYING/DONE/FAILED/CANCELLED
    retries: int = 0
    created_at: str = datetime.now().isoformat()
    updated_at: str = datetime.now().isoformat()
    artifacts: Dict[str, str] = {}
    meta: Dict[str, Any] = {}
    progress: Dict[str, Any] = {}  # Track progress like chunks completed, tokens used


class JobRunnerV3:
    """Version 3 job runner with typed events and async event bus."""
    
    def __init__(self, project_defaults: Optional[Dict[str, Any]] = None):
        self.defaults = project_defaults or {}
        Path(".xsarena/jobs").mkdir(parents=True, exist_ok=True)
        self.event_handlers: List[Callable[[BaseEvent], Awaitable[None]]] = []

    def register_event_handler(self, handler: Callable[[BaseEvent], Awaitable[None]]):
        """Register an event handler for job events."""
        self.event_handlers.append(handler)

    async def _emit_event(self, event: BaseEvent):
        """Emit an event to all registered handlers."""
        for handler in self.event_handlers:
            try:
                await handler(event)
            except Exception:
                # Log error but don't fail the job due to event handler issues
                pass

    def _job_dir(self, job_id: str) -> Path:
        """Get the directory for a job."""
        return Path(".xsarena") / "jobs" / job_id

    def submit(self, run_spec: RunSpecV2, backend: str = "bridge") -> str:
        """Submit a new job with the given run specification."""
        job_id = str(uuid.uuid4())
        job = JobV3(
            id=job_id,
            name=run_spec.subject,
            run_spec=run_spec,
            backend=backend,
            state="PENDING",
        )
        jd = self._job_dir(job_id)
        jd.mkdir(parents=True, exist_ok=True)
        
        # Save job metadata
        job_path = jd / "job.json"
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job.model_dump(), f, indent=2)
        
        # Initialize events log
        events_path = jd / "events.jsonl"
        event_data = {
            "ts": self._ts(),
            "type": "job_submitted",
            "job_id": job_id,
            "spec": run_spec.model_dump()
        }
        with open(events_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(event_data) + "\n")
        
        return job_id

    def load(self, job_id: str) -> JobV3:
        """Load a job by ID."""
        job_path = self._job_dir(job_id) / "job.json"
        data = load_json(job_path)
        return JobV3(**data)

    def _save_job(self, job: JobV3):
        """Save job metadata."""
        jd = self._job_dir(job.id)
        job_path = jd / "job.json"
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(job.model_dump(), f, indent=2)

    def list_jobs(self) -> List[JobV3]:
        """List all jobs."""
        base = Path(".xsarena") / "jobs"
        out: List[JobV3] = []
        if not base.exists():
            return out
        for d in base.iterdir():
            p = d / "job.json"
            if p.exists():
                out.append(self.load(d.name))
        return out

    def _log_event(self, job_id: str, ev: Dict[str, Any]):
        """Log an event for a job."""
        ev_path = self._job_dir(job_id) / "events.jsonl"
        ev["ts"] = self._ts()
        with open(ev_path, "a", encoding="utf-8") as e:
            e.write(json.dumps(ev) + "\n")

    @staticmethod
    def _ts() -> str:
        """Get current timestamp."""
        return time.strftime("%Y-%m-%dT%H:%M:%S")

    async def run_job(self, job_id: str, transport: BackendTransport):
        """Run a job with the given transport."""
        job = self.load(job_id)
        job.state = "RUNNING"
        job.updated_at = self._ts()
        self._save_job(job)
        
        # Emit job started event
        job_started_event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "job_id": job_id,
            "spec": job.run_spec.model_dump()
        }
        await self._emit_event(BaseEvent(**job_started_event))
        self._log_event(job_id, {"type": "job_started", "job_id": job_id})

        # Prepare output path
        out_path = job.run_spec.out_path or f"./books/{job.run_spec.subject.replace(' ', '_')}.final.md"
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        # Extract run parameters from spec
        max_chunks = job.run_spec.resolved()["chunks"]
        fail = {}  # TODO: Add failure handling from spec
        watchdog_secs = getattr(job.run_spec, 'timeout', 300)
        max_retries = 3  # TODO: Make configurable

        async def on_chunk(idx: int, body: str, hint: Optional[str] = None):
            """Callback for when a chunk is completed."""
            with open(out_path, "a", encoding="utf-8") as f:
                if f.tell() == 0 or idx == 1:
                    f.write(body)
                else:
                    f.write(("\\n\\n" if not body.startswith("\\n") else "") + body)
            
            # Log chunk completion
            self._log_event(job_id, {
                "type": "chunk_done", 
                "job_id": job_id, 
                "idx": idx, 
                "bytes": len(body),
                "hint": hint
            })
            
            # Emit chunk done event
            chunk_done_event = {
                "event_id": str(uuid.uuid4()),
                "timestamp": time.time(),
                "job_id": job_id,
                "chunk_id": f"chunk_{idx}",
                "result": body
            }
            await self._emit_event(BaseEvent(**chunk_done_event))

        async def on_event(ev_type: str, payload: Dict[str, Any]):
            """Callback for other events."""
            self._log_event(job_id, {"type": ev_type, "job_id": job_id, **payload})

        async def _do_run():
            """Internal function to perform the actual run."""
            # This would integrate with the new autopilot FSM
            # For now, we'll simulate the process
            for chunk_idx in range(1, max_chunks + 1):
                # Simulate sending a request to the transport
                payload = {
                    "messages": [
                        {"role": "system", "content": f"Generate content for {job.run_spec.subject}"},
                        {"role": "user", "content": f"Generate chunk {chunk_idx} of a book about {job.run_spec.subject}"}
                    ],
                    "model": "gpt-4o"  # Use model from spec
                }
                
                try:
                    response = await transport.send(payload)
                    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                    await on_chunk(chunk_idx, content)
                except Exception as e:
                    # Emit chunk failed event
                    chunk_failed_event = {
                        "event_id": str(uuid.uuid4()),
                        "timestamp": time.time(),
                        "job_id": job_id,
                        "chunk_id": f"chunk_{chunk_idx}",
                        "error_message": str(e)
                    }
                    await self._emit_event(BaseEvent(**chunk_failed_event))
                    raise

        # Run with retry logic
        attempt = 0
        while True:
            try:
                await asyncio.wait_for(_do_run(), timeout=watchdog_secs)
                
                # Mark job as completed
                job.artifacts["final"] = out_path
                job.state = "DONE"
                
                # Emit job completed event
                job_completed_event = {
                    "event_id": str(uuid.uuid4()),
                    "timestamp": time.time(),
                    "job_id": job_id,
                    "result_path": out_path,
                    "total_chunks": max_chunks
                }
                await self._emit_event(BaseEvent(**job_completed_event))
                
                self._log_event(job_id, {
                    "type": "job_completed", 
                    "job_id": job_id, 
                    "final": out_path,
                    "total_chunks": max_chunks
                })
                break
            except asyncio.TimeoutError:
                self._log_event(job_id, {
                    "type": "watchdog_timeout", 
                    "job_id": job_id, 
                    "secs": watchdog_secs
                })
                
                if attempt < max_retries:
                    attempt += 1
                    self._log_event(job_id, {
                        "type": "retry", 
                        "job_id": job_id, 
                        "attempt": attempt
                    })
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    job.state = "FAILED"
                    job_failed_event = {
                        "event_id": str(uuid.uuid4()),
                        "timestamp": time.time(),
                        "job_id": job_id,
                        "error_message": "watchdog timeout"
                    }
                    await self._emit_event(BaseEvent(**job_failed_event))
                    self._log_event(job_id, {
                        "type": "job_failed", 
                        "job_id": job_id, 
                        "error": "watchdog timeout"
                    })
                    break
            except Exception as ex:
                if attempt < max_retries:
                    attempt += 1
                    self._log_event(job_id, {
                        "type": "retry", 
                        "job_id": job_id, 
                        "attempt": attempt, 
                        "error": str(ex)
                    })
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    job.state = "FAILED"
                    job_failed_event = {
                        "event_id": str(uuid.uuid4()),
                        "timestamp": time.time(),
                        "job_id": job_id,
                        "error_message": str(ex)
                    }
                    await self._emit_event(BaseEvent(**job_failed_event))
                    self._log_event(job_id, {
                        "type": "job_failed", 
                        "job_id": job_id, 
                        "error": str(ex)
                    })
                    break
            finally:
                job.updated_at = self._ts()
                self._save_job(job)

        self._log_event(job_id, {
            "type": "job_ended", 
            "job_id": job_id, 
            "state": job.state
        })