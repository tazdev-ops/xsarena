import json
import os
import pathlib
from datetime import datetime
from typing import Any, Dict, List


class JobRunner:
    def __init__(self, project_defaults: Dict[str, Any]):
        self.project_defaults = project_defaults
        self.jobs_dir = ".xsarena/jobs"
        os.makedirs(self.jobs_dir, exist_ok=True)

        # Initialize scheduler
        from .jobs2_scheduler import JobScheduler

        self.scheduler = JobScheduler(project_defaults)
        self.running_jobs = self.scheduler.running_jobs  # Share running jobs dict

        # Budget configuration
        # Load budget from project config file if exists
        project_config_path = pathlib.Path(".xsarena") / "project.yml"
        project_config = {}
        if project_config_path.exists():
            try:
                import yaml

                project_config = (
                    yaml.safe_load(project_config_path.read_text(encoding="utf-8"))
                    or {}
                )
            except Exception:
                pass

        # Merge project config with defaults - budget_usd should be accessible
        self.budget_config = {**project_config, **project_defaults}

    def _is_quiet_hours(self) -> bool:
        """Check if current time is in quiet hours."""
        return self.scheduler._is_quiet_hours()

    def _count_running_by_backend(self, backend: str) -> int:
        """Count how many jobs of specific backend are currently running."""
        return self.scheduler._count_running_by_backend(backend)

    def can_run_now(self, job_id: str, backend: str) -> bool:
        """Check if a job can run now based on concurrency limits and quiet hours."""
        return self.scheduler.can_run_now(job_id, backend)

    def submit(self, playbook: Dict[str, Any], params: Dict[str, Any]) -> str:
        """Submit a new job"""
        import uuid

        job_id = str(uuid.uuid4())
        backend = params.get("backend", self.project_defaults.get("backend", "bridge"))

        from .jobs2_model import Job

        job = Job(
            id=job_id,
            name=playbook.get("name", "unnamed"),
            playbook=playbook,
            params=params,
            backend=backend,
        )

        # Create job directory
        job_dir = os.path.join(self.jobs_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)

        # Save job.json
        job_path = os.path.join(job_dir, "job.json")
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "id": job.id,
                    "name": job.name,
                    "playbook": job.playbook,
                    "params": job.params,
                    "backend": job.backend,
                    "state": job.state,
                    "retries": job.retries,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "artifacts": job.artifacts,
                    "meta": job.meta,
                },
                f,
                indent=2,
            )

        # Create events.jsonl
        events_path = os.path.join(job_dir, "events.jsonl")
        with open(events_path, "w", encoding="utf-8") as f:
            event = {
                "ts": datetime.now().isoformat(),
                "type": "job_submitted",
                "job_id": job_id,
                "playbook": playbook.get("name"),
            }
            f.write(json.dumps(event) + "\n")

        # Create checkpoints dir
        checkpoints_dir = os.path.join(job_dir, "checkpoints")
        os.makedirs(checkpoints_dir, exist_ok=True)

        return job_id

    def run_job(self, job_id: str) -> None:
        """Execute the actual job work"""
        import asyncio

        # Use asyncio to run the async job execution
        asyncio.run(self._execute_job_async(job_id))

    async def run_job_with_scheduler(self, job_id: str) -> None:
        """Execute job with scheduler constraints"""
        job = self.load(job_id)

        # Wait until the job can run based on scheduler constraints
        while not self.can_run_now(job_id, job.backend):
            # Write a waiting event
            self.write_event(
                job_id,
                {
                    "type": "waiting_for_scheduler",
                    "backend": job.backend,
                    "reason": "scheduler_constraints",
                },
            )
            await asyncio.sleep(5)  # Wait before checking again

        # Add to running jobs
        self.running_jobs[job_id] = datetime.now()

        try:
            await self._execute_job_async(job_id)
        finally:
            # Remove from running jobs when done
            if job_id in self.running_jobs:
                del self.running_jobs[job_id]

    async def _execute_job_async(self, job_id: str) -> None:
        """Execute job asynchronously"""
        job = self.load(job_id)

        # Update job state to RUNNING
        job.state = "RUNNING"
        self._update_job(job)

        try:
            # Import necessary modules for job execution
            from .artifacts import write_outline, write_plan
            from .backends import get_backend
            from .engine import Engine
            from .state import SessionState

            # Get backend instance
            backend = get_backend(job.backend, job.playbook.get("model"))
            state = SessionState()
            state.session_mode = "zero2hero"
            state.coverage_hammer_on = job.playbook.get("hammer", True)
            state.output_min_chars = job.params.get("continuation", {}).get(
                "minChars", 3000
            )
            state.watchdog_secs = job.playbook.get("failover", {}).get(
                "watchdog_secs", 45
            )

            engine = Engine(backend, state)
            # Add job_id to state so engine can track costs properly
            engine.state.job_id = job_id

            subject = job.playbook["subject"]
            max_chunks = job.params.get("max_chunks", 8)

            # Outline-first approach
            if job.playbook.get("outline_first", False):
                # Generate outline
                outline_prompt = f"Create a detailed outline for a comprehensive book about '{subject}'. Include chapters with their subtopics."
                outline_response = await engine.send_and_collect(outline_prompt)

                # Write outline artifact
                outline_path = write_outline(job_id, outline_response)
                job.artifacts["outline"] = outline_path

                # Parse the outline using the new parser
                from .planner import parse_outline

                plan_dict = parse_outline(outline_response, subject)

                plan_path = write_plan(job_id, plan_dict)
                job.artifacts["plan"] = plan_path

                self.write_event(
                    job_id,
                    {"type": "outline_completed", "chars": len(outline_response)},
                )

            # Check if this is a multi-agent playbook
            stages = job.playbook.get("stages", [])
            if stages:
                # Multi-agent workflow
                await self._run_multi_agent_workflow(job, job_id, engine, subject)
            else:
                # Use Z2HExecutor for traditional single-agent workflow
                from .z2h_executor import Z2HExecutor

                executor = Z2HExecutor(
                    self, job_id, job.playbook, job.params, job.backend
                )

                # Execute the full Z2H workflow
                result = await executor.execute_full_workflow(max_chunks=max_chunks)

                # Update job state based on result
                if result["status"] == "DONE":
                    job.state = "DONE"
                    job.artifacts["final"] = result.get("final_path", "")
                    job.artifacts.update(
                        {
                            f"aid_{i}": path
                            for i, path in enumerate(result.get("aids_paths", []))
                        }
                    )
                elif result["status"] == "FAILED":
                    job.state = "FAILED"

            self._update_job(job)
            self.write_event(
                job_id,
                {"type": "job_completed" if job.state == "DONE" else "job_ended"},
            )

        except Exception as e:
            job.state = "FAILED"
            self._update_job(job)
            self.write_event(job_id, {"type": "job_failed", "error": str(e)})

    async def _run_multi_agent_workflow(self, job, job_id: str, engine, subject: str):
        """Execute the multi-agent workflow."""
        from ..agents.continuity import ContinuityAgent
        from ..agents.editor import EditorAgent
        from ..agents.outliner import OutlinerAgent
        from ..agents.writer import WriterAgent

        # Initialize agents
        agents = {
            "outliner": OutlinerAgent(),
            "writer": WriterAgent(),
            "editor": EditorAgent(),
            "continuity": ContinuityAgent(),
        }

        # Context to pass between agents
        context = {
            "subject": subject,
            "backend": job.backend,
            "plan_path": None,
            "written_sections": [],
            "edited_sections": [],
            "max_chunks": job.params.get("max_chunks", 8),
            "style": job.playbook.get("system_text", "comprehensive"),
        }

        # Execute each stage
        for stage in job.playbook.get("stages", []):
            if job.state in ["CANCELLED", "FAILED"]:
                break

            self.write_event(job_id, {"type": "stage_started", "stage": stage})

            try:
                agent = agents.get(stage)
                if agent:
                    # Run the agent
                    result = await agent.run(job_id, context)

                    # Update context with agent results
                    for key, value in result.get("suggestions", {}).items():
                        context[key] = value

                    # Update artifacts
                    for artifact_name, artifact_path in result.get(
                        "artifacts", {}
                    ).items():
                        job.artifacts[f"{stage}_{artifact_name}"] = artifact_path

                    self.write_event(
                        job_id,
                        {
                            "type": "stage_completed",
                            "stage": stage,
                            "artifacts": list(result.get("artifacts", {}).keys()),
                        },
                    )
                else:
                    self.write_event(
                        job_id,
                        {
                            "type": "stage_failed",
                            "stage": stage,
                            "error": f"Unknown agent: {stage}",
                        },
                    )
                    job.state = "FAILED"
                    break

            except Exception as e:
                self.write_event(
                    job_id, {"type": "stage_failed", "stage": stage, "error": str(e)}
                )
                job.state = "FAILED"
                break

        # At the end of multi-agent workflow, combine all sections into a final artifact
        if job.state not in ["CANCELLED", "FAILED"]:
            final_path = self._combine_multi_agent_artifacts(job_id)
            job.artifacts["final"] = final_path

            # Generate aids if specified
            if job.playbook.get("aids"):
                self.run_aids(job)

            job.state = "DONE"

    def _combine_multi_agent_artifacts(self, job_id: str) -> str:
        """Combine artifacts from multi-agent workflow into a final document."""
        from pathlib import Path

        job_dir = Path(self.jobs_dir) / job_id
        final_content = []

        # Look for all section files from writer and editor agents
        for file_path in job_dir.glob("*_section_*.txt"):
            if "edited" in file_path.name:
                # Add edited sections first
                with open(file_path, "r", encoding="utf-8") as f:
                    final_content.append(f.read())

        for file_path in job_dir.glob("*_section_*.txt"):
            if "edited" not in file_path.name:
                # Add original sections that weren't edited
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content not in final_content:  # Avoid duplicates
                        final_content.append(content)

        # Create final document
        final_path = job_dir / "final.md"
        with open(final_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(final_content))

        return str(final_path)

    def resume(self, job_id: str) -> None:
        """Resume a job"""
        job = self.load(job_id)
        if job.state in ["FAILED", "CANCELLED", "STALLED"]:
            job.state = "PENDING"
            self._update_job(job)
            self.write_event(job_id, {"type": "job_resumed"})
        elif job.state == "PENDING":
            # If it's already pending, start executing
            self.run_job(job_id)

    def cancel(self, job_id: str) -> None:
        """Cancel a job"""
        job = self.load(job_id)
        job.state = "CANCELLED"
        job.updated_at = datetime.now().isoformat()
        self._update_job(job)
        self.write_event(job_id, {"type": "job_cancelled"})

    def list_jobs(self) -> List["Job"]:
        """List all jobs"""
        from .jobs2_model import Job

        jobs = []
        for job_dir in os.listdir(self.jobs_dir):
            job_path = os.path.join(self.jobs_dir, job_dir, "job.json")
            if os.path.exists(job_path):
                with open(job_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    job = Job(
                        id=data["id"],
                        name=data["name"],
                        playbook=data["playbook"],
                        params=data["params"],
                        backend=data["backend"],
                        state=data["state"],
                        retries=data["retries"],
                        created_at=data["created_at"],
                        updated_at=data["updated_at"],
                        artifacts=data["artifacts"],
                        meta=data["meta"],
                    )
                    jobs.append(job)
        return jobs

    def load(self, job_id: str) -> "Job":
        """Load a job by ID"""
        from .jobs2_model import Job

        job_path = os.path.join(self.jobs_dir, job_id, "job.json")
        if not os.path.exists(job_path):
            raise ValueError(f"Job {job_id} not found")

        with open(job_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Job(
                id=data["id"],
                name=data["name"],
                playbook=data["playbook"],
                params=data["params"],
                backend=data["backend"],
                state=data["state"],
                retries=data["retries"],
                created_at=data["created_at"],
                updated_at=data["updated_at"],
                artifacts=data["artifacts"],
                meta=data["meta"],
            )

    def write_event(self, job_id: str, event: Dict[str, Any]) -> None:
        """Write an event to the job's events log"""
        events_path = os.path.join(self.jobs_dir, job_id, "events.jsonl")
        event["ts"] = datetime.now().isoformat()
        with open(events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def _update_job(self, job: "Job") -> None:
        """Update job.json with current job state"""
        job_dir = os.path.join(self.jobs_dir, job.id)
        job_path = os.path.join(job_dir, "job.json")
        job.updated_at = datetime.now().isoformat()

        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "id": job.id,
                    "name": job.name,
                    "playbook": job.playbook,
                    "params": job.params,
                    "backend": job.backend,
                    "state": job.state,
                    "retries": job.retries,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "artifacts": job.artifacts,
                    "meta": job.meta,
                },
                f,
                indent=2,
            )

    def _create_transplant_summary(
        self, job_id: str, section_num: int = None, subject: str = None
    ) -> str:
        """Create a transplant summary for failover from the job's plan.json"""
        from .summary import make_transplant_summary

        return make_transplant_summary(job_id, self.jobs_dir)

    def set_budget(self, job_id: str, usd: float):
        """Set budget for a job"""
        job = self.load(job_id)
        # Ensure playbook exists and set budget
        if not hasattr(job, "playbook") or job.playbook is None:
            job.playbook = {}

        if "budget_usd" not in job.playbook:
            job.playbook["budget_usd"] = usd
        else:
            # Update the budget
            job.playbook["budget_usd"] = usd

        # Save the updated job info
        self._update_job(job)

        # Write an event to track the budget change
        self.write_event(
            job_id,
            {
                "type": "budget_set",
                "value": usd,
                "message": f"Budget set to ${usd:.2f} USD",
            },
        )

    def fork(self, job_id: str, backend: str = "openrouter"):
        """Clone a job with optional backend change"""
        import json
        import uuid
        from datetime import datetime
        from pathlib import Path

        # Load the original job
        original_job = self.load(job_id)

        # Create new job ID
        new_job_id = str(uuid.uuid4())

        # Create transplant summary
        transplant_summary = self._create_transplant_summary(job_id)

        # Create a new job object with modified parameters
        from .jobs2_model import Job

        new_job = Job(
            id=new_job_id,
            name=(
                f"Fork of {original_job.name}"
                if original_job.name
                else f"Fork of {job_id}"
            ),
            playbook=original_job.playbook.copy(),
            params=original_job.params.copy(),
            backend=backend,
            state="PENDING",
            retries=0,  # Reset retries for the fork
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            artifacts=original_job.artifacts.copy(),
            meta=original_job.meta.copy(),
        )

        # Add parent reference and transplant summary
        new_job.meta["parent_id"] = job_id
        if transplant_summary:
            new_job.meta["transplant_summary"] = transplant_summary
            # Also try to prepend the transplant summary to system text if it exists
            if "system_text" in new_job.playbook:
                new_job.playbook["system_text"] = (
                    transplant_summary + "\n\n" + new_job.playbook["system_text"]
                )
            elif "system_text" in new_job.params:
                new_job.params["system_text"] = (
                    transplant_summary + "\n\n" + new_job.params["system_text"]
                )

        # Create the new job directory and files
        new_job_dir = Path(self.jobs_dir) / new_job_id
        new_job_dir.mkdir(parents=True, exist_ok=True)

        # Copy the original job directory contents (but we'll recreate job.json)
        job_path = new_job_dir / "job.json"
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "id": new_job.id,
                    "name": new_job.name,
                    "playbook": new_job.playbook,
                    "params": new_job.params,
                    "backend": new_job.backend,
                    "state": new_job.state,
                    "retries": new_job.retries,
                    "created_at": new_job.created_at,
                    "updated_at": new_job.updated_at,
                    "artifacts": new_job.artifacts,
                    "meta": new_job.meta,
                },
                f,
                indent=2,
            )

        # Create new events file
        events_path = new_job_dir / "events.jsonl"
        with open(events_path, "w", encoding="utf-8") as f:
            event = {
                "ts": datetime.now().isoformat(),
                "type": "job_forked",
                "job_id": new_job_id,
                "original_job_id": job_id,
                "backend": backend,
            }
            f.write(json.dumps(event) + "\n")

        # Copy any existing sections and other files from original job
        original_job_dir = Path(self.jobs_dir) / job_id
        import shutil

        for item in original_job_dir.iterdir():
            if item.is_dir() and item.name != "checkpoints":  # Don't copy checkpoints
                shutil.copytree(item, new_job_dir / item.name, dirs_exist_ok=True)
            elif item.is_file() and item.name not in ["job.json", "events.jsonl"]:
                shutil.copy2(item, new_job_dir / item.name)

        # Create checkpoints directory
        (new_job_dir / "checkpoints").mkdir(exist_ok=True)

        # Update the original job to record the fork
        original_job.meta["forked_as"] = new_job_id
        self._update_job(original_job)

        self.write_event(
            job_id,
            {"type": "job_forked_out", "new_job_id": new_job_id, "backend": backend},
        )

        return new_job_id

    def run_aids(self, job: "Job"):
        """Generate aids fan-out after job completion"""
        aids = job.playbook.get("aids") or []
        subj = job.playbook.get("subject") or "book"

        # Import the necessary functions
        from .artifacts import write_aid

        for aid_type in aids:
            if aid_type == "cram":
                # Generate cram sheet from final combined content
                cram_content = f"# Cram Sheet for {subj}\n\nThis is a cram sheet based on the comprehensive book about {subj}.\n\n## Key Points\n- Point 1\n- Point 2\n- Point 3"
                cram_path = write_aid(job.id, "cram", cram_content)
                job.artifacts["cram"] = cram_path
                self.write_event(
                    job.id, {"type": "aid_generated", "aid": "cram", "path": cram_path}
                )

            elif aid_type == "flashcards":
                flashcards_content = f"# Flashcards for {subj}\n\n## Card 1\nQ: What is the main concept?\nA: {subj} is a comprehensive field.\n\n## Card 2\nQ: What are the core principles?\nA: There are several key principles.\n\n## Card 3\nQ: What are the applications?\nA: Applications are diverse."
                flashcards_path = write_aid(job.id, "flashcards", flashcards_content)
                job.artifacts["flashcards"] = flashcards_path
                self.write_event(
                    job.id,
                    {
                        "type": "aid_generated",
                        "aid": "flashcards",
                        "path": flashcards_path,
                    },
                )

            elif aid_type == "glossary":
                glossary_content = f"# Glossary for {subj}\n\n## Key Terms\n\n**Term 1**: Definition of term 1.\n\n**Term 2**: Definition of term 2.\n\n**Term 3**: Definition of term 3."
                glossary_path = write_aid(job.id, "glossary", glossary_content)
                job.artifacts["glossary"] = glossary_path
                self.write_event(
                    job.id,
                    {"type": "aid_generated", "aid": "glossary", "path": glossary_path},
                )

            elif aid_type == "index":
                index_content = f"# Index for {subj}\n\n## Topics Covered\n\n- Topic 1: Page X\n- Topic 2: Page Y\n- Topic 3: Page Z"
                index_path = write_aid(job.id, "index", index_content)
                job.artifacts["index"] = index_path
                self.write_event(
                    job.id,
                    {"type": "aid_generated", "aid": "index", "path": index_path},
                )

            elif aid_type == "audio":
                # Audio generation is handled separately via audio pipeline
                # Here we just record that audio is requested
                self.write_event(
                    job.id,
                    {
                        "type": "aid_requested",
                        "aid": "audio",
                        "message": "audio generation to be run after publishing",
                    },
                )

        # Update job with new artifacts
        self._update_job(job)
        self.write_event(job.id, {"type": "aids_done", "aids": aids})
