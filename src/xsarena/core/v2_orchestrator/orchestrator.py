"""Orchestrator for XSArena v0.2 - manages the overall workflow."""

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..autopilot.fsm import AutopilotFSM
from ..backends import create_backend
from ..backends.transport import BackendTransport
from ..jobs.scheduler import Scheduler
from ..prompt import compose_prompt
from ..state import SessionState
from .specs import RunSpecV2


class Orchestrator:
    """Main orchestrator that manages the entire run process."""

    def __init__(self, transport: Optional[BackendTransport] = None):
        self.transport = transport
        self.fsm = AutopilotFSM()
        self._job_runner = None  # Lazy initialization to avoid circular import
        self.scheduler = Scheduler()

    def _calculate_directive_digests(
        self, overlays: List[str], extra_files: List[str]
    ) -> Dict[str, str]:
        """Calculate SHA256 digests for directive files and extra files."""
        digests = {}

        # Calculate digests for overlays
        for overlay in overlays:
            # Try to find overlay directive file
            overlay_paths = [
                Path(f"directives/style/{overlay}.md"),
                Path(f"directives/overlays/{overlay}.md"),
                Path(f"directives/{overlay}.md"),
            ]

            for overlay_path in overlay_paths:
                if overlay_path.exists():
                    try:
                        content = overlay_path.read_text(encoding="utf-8")
                        digest = hashlib.sha256(content.encode()).hexdigest()
                        digests[f"overlay:{overlay}"] = digest
                        break
                    except Exception:
                        continue

        # Calculate digests for extra files
        for extra_file in extra_files:
            extra_path = Path(extra_file)
            if extra_path.exists():
                try:
                    content = extra_path.read_text(encoding="utf-8")
                    digest = hashlib.sha256(content.encode()).hexdigest()
                    digests[f"extra:{extra_file}"] = digest
                except Exception:
                    continue

        # Calculate digest for base directive
        base_path = Path("directives/base/zero2hero.md")
        if base_path.exists():
            try:
                content = base_path.read_text(encoding="utf-8")
                digest = hashlib.sha256(content.encode()).hexdigest()
                digests["base:zero2hero"] = digest
            except Exception:
                pass

        return digests

    def _get_git_commit_hash(self) -> Optional[str]:
        """Get the current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                check=True,
            )
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def _get_config_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of current configuration."""
        import yaml

        config_snapshot = {}

        # Get settings from config.yml
        config_path = Path(".xsarena/config.yml")
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_content = yaml.safe_load(f) or {}
                config_snapshot["settings"] = config_content.get("settings", {})
            except Exception:
                config_snapshot["settings"] = {}

        # Get bridge IDs from session state
        session_path = Path(".xsarena/session_state.json")
        if session_path.exists():
            try:
                with open(session_path, "r", encoding="utf-8") as f:
                    session_content = json.load(f) or {}
                # Only include bridge-related IDs
                bridge_ids = {}
                for key, value in session_content.items():
                    if "bridge" in key.lower():
                        bridge_ids[key] = value
                if bridge_ids:
                    config_snapshot["bridge_ids"] = bridge_ids
            except Exception:
                pass

        return config_snapshot

    def _check_directive_drift(self) -> List[str]:
        """Check for directive drift by comparing current directive files to the lockfile."""
        import json
        from pathlib import Path

        lockfile_path = Path(".xsarena/directives.lock")
        if not lockfile_path.exists():
            return []  # No lockfile exists, so no drift to check

        try:
            with open(lockfile_path, "r", encoding="utf-8") as f:
                lock_data = json.load(f)

            locked_directives = lock_data.get("directives", {})
            drifts = []

            for relative_path, expected_hash in locked_directives.items():
                file_path = Path(relative_path)
                if file_path.exists():
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        current_hash = hashlib.sha256(content.encode()).hexdigest()
                        if current_hash != expected_hash:
                            drifts.append(f"Changed: {relative_path}")
                    except Exception:
                        drifts.append(f"Unreadable: {relative_path}")
                else:
                    drifts.append(f"Missing: {relative_path}")

            return drifts
        except Exception as e:
            print(f"Warning: Could not check directive drift: {e}")
            return []

    def _save_run_manifest(
        self,
        job_id: str,
        system_text: str,
        run_spec: RunSpecV2,
        overlays: List[str],
        extra_files: List[str],
    ) -> str:
        """Save run manifest with all required information."""
        import json
        from datetime import datetime
        from pathlib import Path

        # Calculate directive digests
        directive_digests = self._calculate_directive_digests(overlays, extra_files)

        # Get git commit hash
        git_commit_hash = self._get_git_commit_hash()

        # Get config snapshot
        config_snapshot = self._get_config_snapshot()

        # Check for directive drift and log if any
        directive_drifts = self._check_directive_drift()

        # Create manifest data
        manifest_data = {
            "final_system_text": system_text,
            "resolved_run_spec": run_spec.model_dump(),
            "directive_digests": directive_digests,
            "config_snapshot": config_snapshot,
            "git_commit_hash": git_commit_hash,
            "timestamp": datetime.now().isoformat(),
            "directive_drifts": directive_drifts,  # Include any detected drifts
        }

        # Create job directory if it doesn't exist
        job_dir = Path(".xsarena/jobs") / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        # Save manifest
        manifest_path = job_dir / "run_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        return str(manifest_path)

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()

    @property
    def job_runner(self):
        """Lazy load JobManager to avoid circular import."""
        if self._job_runner is None:
            from ..jobs.model import JobManager

            self._job_runner = JobManager()
        return self._job_runner

    async def run_spec(
        self, run_spec: RunSpecV2, backend_type: str = "bridge", priority: int = 5
    ) -> str:
        """Run a specification through the orchestrator."""
        if not self.transport:
            # Pass bridge-specific IDs if they are provided in the run spec
            transport_kwargs = {}
            if run_spec.bridge_session_id:
                transport_kwargs["session_id"] = run_spec.bridge_session_id
            if run_spec.bridge_message_id:
                transport_kwargs["message_id"] = run_spec.bridge_message_id

            self.transport = create_backend(backend_type, **transport_kwargs)

        # session + prompt composition (unchanged)
        session_state = SessionState.load_from_file(".xsarena/session_state.json")
        resolved = run_spec.resolved()
        resolved["min_length"] = getattr(
            session_state, "output_min_chars", resolved["min_length"]
        )

        # compose system_text here as you already do:
        comp = compose_prompt(
            subject=run_spec.subject,
            base="zero2hero",
            overlays=run_spec.overlays,
            extra_notes=run_spec.extra_note,
            min_chars=resolved["min_length"],
            passes=resolved["passes"],
            max_chunks=resolved["chunks"],
            apply_reading_overlay=getattr(session_state, "reading_overlay_on", False),
        )
        system_text = comp.system_text
        for file_path in run_spec.extra_files:
            p = Path(file_path)
            if p.exists():
                system_text += "\n\n" + p.read_text(encoding="utf-8", errors="ignore")

        # NEW: resume-safe scheduling
        out_path = (
            run_spec.out_path
            or f"./books/{run_spec.subject.replace(' ', '_')}.final.md"
        )
        existing = self.job_runner.find_resumable_job_by_output(out_path)
        if existing:
            job = self.job_runner.load(existing)
            if job.state == "RUNNING":
                job_id = job.id
                print(f"[run] existing RUNNING job → {job_id}")
            else:
                job_id = self.job_runner.prepare_job_for_resume(existing)
                print(f"[run] resuming job → {job_id}")
        else:
            job_id = self.job_runner.submit(
                run_spec, backend_type, system_text, session_state
            )
            print(f"[run] submitted → {job_id}")

        # Save run manifest with all required information
        self._save_run_manifest(
            job_id=job_id,
            system_text=system_text,
            run_spec=run_spec,
            overlays=run_spec.overlays,
            extra_files=run_spec.extra_files,
        )
        print(f"[run] manifest saved → .xsarena/jobs/{job_id}/run_manifest.json")

        self.scheduler.set_transport(self.transport)
        await self.scheduler.submit_job(job_id, priority=priority)
        await self.scheduler.wait_for_job(job_id)
        return job_id

    async def run_with_fsm(self, run_spec: RunSpecV2) -> Dict[str, Any]:
        """Run a specification using the FSM approach."""
        # Convert run_spec to FSM-compatible format
        fsm_input = run_spec.model_dump()

        # Run the FSM
        result = await self.fsm.run(fsm_input)

        return result.model_dump()

    async def run_continue(
        self,
        run_spec: RunSpecV2,
        file_path: str,
        until_end: bool = False,
        priority: int = 5,
    ) -> str:
        """Run a continue operation from an existing file."""
        # Create a transport if not provided
        if not self.transport:
            # Pass bridge-specific IDs if they are provided in the run spec
            transport_kwargs = {}
            if run_spec.bridge_session_id:
                transport_kwargs["session_id"] = run_spec.bridge_session_id
            if run_spec.bridge_message_id:
                transport_kwargs["message_id"] = run_spec.bridge_message_id

            self.transport = create_backend("bridge", **transport_kwargs)

        # Load session state to override run_spec values with dynamic config
        session_state = SessionState.load_from_file(".xsarena/session_state.json")

        # Create a modified run_spec with values from session state
        resolved = run_spec.resolved()

        # Override resolved values with session state values if they exist
        resolved["min_length"] = getattr(
            session_state, "output_min_chars", resolved["min_length"]
        )

        composition = compose_prompt(
            subject=run_spec.subject,
            base="zero2hero",  # Default base, can be made configurable
            overlays=run_spec.overlays,
            extra_notes=run_spec.extra_note,
            min_chars=resolved["min_length"],
            passes=resolved["passes"],
            max_chunks=resolved["chunks"],
            apply_reading_overlay=getattr(session_state, "reading_overlay_on", False),
        )

        # Read contents of extra_files and append to system_text
        system_text = composition.system_text
        for extra_file_path in run_spec.extra_files:
            try:
                p = Path(extra_file_path)
                if p.exists():
                    content = p.read_text(encoding="utf-8")
                    system_text += "\n\n" + content
            except Exception as e:
                print(f"Warning: Could not read extra file {extra_file_path}: {e}")

        # Submit job to the new system with the composed system_text and session state
        job_id = self.job_runner.submit_continue(
            run_spec, file_path, until_end, system_text, session_state
        )

        # Save run manifest with all required information
        self._save_run_manifest(
            job_id=job_id,
            system_text=system_text,
            run_spec=run_spec,
            overlays=run_spec.overlays,
            extra_files=run_spec.extra_files,
        )
        print(f"[run] manifest saved → .xsarena/jobs/{job_id}/run_manifest.json")

        # Set the transport for the scheduler
        self.scheduler.set_transport(self.transport)

        # Submit job to scheduler
        await self.scheduler.submit_job(job_id, priority=priority)

        # Wait for job to complete
        await self.scheduler.wait_for_job(job_id)

        return job_id
