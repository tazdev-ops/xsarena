"""Orchestrator for XSArena v0.2 - manages the overall workflow."""

from typing import Any, Dict, Optional

from ..autopilot.fsm import AutopilotFSM
from ..backends import create_backend
from ..backends.transport import BackendTransport
from ..jobs.model import JobRunnerV3
from ..jobs.scheduler import Scheduler
from .specs import RunSpecV2


class Orchestrator:
    """Main orchestrator that manages the entire run process."""

    def __init__(self, transport: Optional[BackendTransport] = None):
        self.transport = transport
        self.fsm = AutopilotFSM()
        self.job_runner = JobRunnerV3()
        self.scheduler = Scheduler()

    async def run_spec(self, run_spec: RunSpecV2, backend_type: str = "bridge") -> str:
        """Run a specification through the orchestrator."""
        # Create a transport if not provided
        if not self.transport:
            self.transport = create_backend(backend_type)

        # Submit job to the new system
        job_id = self.job_runner.submit(run_spec, backend_type)

        # Set the transport for the scheduler
        self.scheduler.set_transport(self.transport)

        # Submit job to scheduler
        await self.scheduler.submit_job(job_id)

        # Wait for job to complete
        await self.scheduler.wait_for_job(job_id)

        return job_id

    async def run_with_fsm(self, run_spec: RunSpecV2) -> Dict[str, Any]:
        """Run a specification using the FSM approach."""
        # Convert run_spec to FSM-compatible format
        fsm_input = run_spec.model_dump()

        # Run the FSM
        result = await self.fsm.run(fsm_input)

        return result.model_dump()

    async def run_continue(self, run_spec: RunSpecV2, file_path: str, until_end: bool = False) -> str:
        """Run a continue operation from an existing file."""
        # Create a transport if not provided
        if not self.transport:
            self.transport = create_backend("bridge")

        # Submit job to the new system
        job_id = self.job_runner.submit_continue(run_spec, file_path, until_end)
        
        # Set the transport for the scheduler
        self.scheduler.set_transport(self.transport)

        # Submit job to scheduler
        await self.scheduler.submit_job(job_id)

        # Wait for job to complete
        await self.scheduler.wait_for_job(job_id)

        return job_id
