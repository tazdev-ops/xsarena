from __future__ import annotations
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .jobs2_model import Job
from .state import SessionState
from .engine import Engine
from .backends import create_backend
from .config import Config

class JobRunner:
    def __init__(self, project_defaults: Dict[str, Any] | None = None):
        self.defaults = project_defaults or {}
        Path(".xsarena/jobs").mkdir(parents=True, exist_ok=True)

    def _job_dir(self, job_id: str) -> Path:
        return Path(".xsarena") / "jobs" / job_id

    def submit(self, playbook: Dict[str, Any], params: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            name=playbook.get("name", "job"),
            playbook=playbook,
            params=params,
            backend=os.getenv("XSA_BACKEND", "bridge"),
            state="PENDING",
        )
        jd = self._job_dir(job_id)
        jd.mkdir(parents=True, exist_ok=True)
        with open(jd / "job.json", "w", encoding="utf-8") as f:
            json.dump(job.__dict__, f, indent=2)
        with open(jd / "events.jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps({"ts": self._ts(), "type": "job_submitted", "job_id": job_id}) + "\n")
        return job_id

    def load(self, job_id: str) -> Job:
        with open(self._job_dir(job_id) / "job.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return Job(**data)

    def _save_job(self, job: Job):
        jd = self._job_dir(job.id)
        with open(jd / "job.json", "w", encoding="utf-8") as f:
            json.dump(job.__dict__, f, indent=2)

    def list_jobs(self) -> List[Job]:
        base = Path(".xsarena") / "jobs"
        out: List[Job] = []
        if not base.exists():
            return out
        for d in base.iterdir():
            p = d / "job.json"
            if p.exists():
                out.append(self.load(d.name))
        return out

    def _log_event(self, job_id: str, ev: Dict[str, Any]):
        ev_path = self._job_dir(job_id) / "events.jsonl"
        ev["ts"] = self._ts()
        with open(ev_path, "a", encoding="utf-8") as e:
            e.write(json.dumps(ev) + "\n")

    @staticmethod
    def _ts() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S")

    def _build_engine(self, job: Job) -> Engine:
        cfg = Config()
        st = SessionState()
        # apply continuation knobs from params
        cont = job.params.get("continuation", {}) or {}
        if cont.get("mode"):
            st.continuation_mode = cont["mode"]
        st.output_min_chars = int(cont.get("minChars", st.output_min_chars))
        st.output_push_max_passes = int(cont.get("pushPasses", st.output_push_max_passes))
        st.repetition_warn = bool(cont.get("repeatWarn", st.repetition_warn))
        # enable coverage hammer for book tasks
        if (job.playbook.get("task") or "").startswith("book."):
            st.session_mode = "zero2hero"

        backend = create_backend(job.backend, base_url=cfg.base_url, api_key=cfg.api_key, model=job.playbook.get("model") or cfg.model)
        return Engine(backend, st)

    def run_job(self, job_id: str):
        job = self.load(job_id)
        job.state = "RUNNING"
        job.updated_at = self._ts()
        self._save_job(job)
        self._log_event(job_id, {"type": "job_started", "job_id": job_id})

        out_path = (job.params.get("io", {}) or {}).get("outPath") or f"./books/{job.playbook.get('subject','book')}.final.md"
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        sys = job.playbook.get("system_text") or ""
        max_chunks = int(job.params.get("max_chunks") or 1)
        fail = job.playbook.get("failover", {}) or {}
        watchdog_secs = int(fail.get("watchdog_secs", 0) or 0)
        max_retries = int(fail.get("max_retries", 0) or 0)
        fallback_backend = fail.get("fallback_backend")

        def on_chunk(idx: int, body: str, hint: Optional[str]):
            with open(out_path, "a", encoding="utf-8") as f:
                if f.tell() == 0 or idx == 1:
                    f.write(body)
                else:
                    f.write(("\n\n" if not body.startswith("\n") else "") + body)
            self._log_event(job_id, {"type": "chunk_done", "job_id": job_id, "idx": idx, "bytes": len(body)})

        def on_event(ev_type: str, payload: Dict[str, Any]):
            self._log_event(job_id, {"type": ev_type, "job_id": job_id, **payload})

        async def _do_run(engine: Engine):
            if max_chunks > 1:
                await engine.autopilot_run("BEGIN", max_chunks=max_chunks, on_chunk=on_chunk, on_event=on_event, system_prompt=sys)
            else:
                chunk = await engine.send_and_collect("BEGIN", system_prompt=sys)
                on_chunk(1, chunk, None)

        # retry/failover loop
        attempt = 0
        tried_fallback = False
        engine = self._build_engine(job)

        while True:
            try:
                if watchdog_secs > 0:
                    asyncio.run(asyncio.wait_for(_do_run(engine), timeout=watchdog_secs))
                else:
                    asyncio.run(_do_run(engine))
                job.artifacts["final"] = out_path
                job.state = "DONE"
                self._log_event(job_id, {"type": "job_completed", "job_id": job_id, "final": out_path})
                break
            except asyncio.TimeoutError:
                self._log_event(job_id, {"type": "watchdog_timeout", "job_id": job_id, "secs": watchdog_secs})
                if attempt < max_retries:
                    attempt += 1
                    self._log_event(job_id, {"type": "retry", "job_id": job_id, "attempt": attempt})
                    continue
                if fallback_backend and not tried_fallback:
                    tried_fallback = True
                    job.backend = fallback_backend
                    engine = self._build_engine(job)
                    self._log_event(job_id, {"type": "failover", "job_id": job_id, "backend": fallback_backend})
                    continue
                job.state = "FAILED"
                self._log_event(job_id, {"type": "job_failed", "job_id": job_id, "error": "watchdog timeout"})
                break
            except Exception as ex:
                if attempt < max_retries:
                    attempt += 1
                    self._log_event(job_id, {"type": "retry", "job_id": job_id, "attempt": attempt, "error": str(ex)})
                    continue
                if fallback_backend and not tried_fallback:
                    tried_fallback = True
                    job.backend = fallback_backend
                    engine = self._build_engine(job)
                    self._log_event(job_id, {"type": "failover", "job_id": job_id, "backend": fallback_backend})
                    continue
                job.state = "FAILED"
                self._log_event(job_id, {"type": "job_failed", "job_id": job_id, "error": str(ex)})
                break
            finally:
                job.updated_at = self._ts()
                self._save_job(job)

        self._log_event(job_id, {"type": "job_ended", "job_id": job_id, "state": job.state})

    # Stubs (future work: real cooperative cancel/resume)
    def resume(self, job_id: str): pass
    def cancel(self, job_id: str): pass
    def fork(self, job_id: str, backend: str = "openrouter") -> str:
        import shutil
        new_id = str(uuid.uuid4())
        shutil.copytree(self._job_dir(job_id), self._job_dir(new_id))
        jd = self.load(new_id)
        jd.id = new_id
        jd.backend = backend or jd.backend
        jd.state = "PENDING"
        self._save_job(jd)
        return new_id
    def set_budget(self, job_id: str, usd: float): pass