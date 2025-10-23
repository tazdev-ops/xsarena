"""Job controllers for interactive mode."""

import logging

from rich.console import Console

from ...core.v2_orchestrator.orchestrator import Orchestrator
from ..context import CLIContext

logger = logging.getLogger(__name__)


class JobsController:
    """Controller for managing jobs in interactive mode."""

    def __init__(self, console: Console, ctx: CLIContext, orchestrator: Orchestrator):
        self.console = console
        self.ctx = ctx
        self.orchestrator = orchestrator

    async def pause_job(self, args):
        """Pause a running job."""
        if not args:
            self.console.print("[red]Error: Please provide a job ID[/red]")
            return

        job_id = args[0]
        try:
            await self.orchestrator.job_manager.pause_job(job_id)
            self.console.print(f"[green]✓ Job {job_id} paused[/green]")
        except Exception as e:
            self.console.print(f"[red]Error pausing job {job_id}: {e}[/red]")

    async def resume_job(self, args):
        """Resume a paused job."""
        if not args:
            self.console.print("[red]Error: Please provide a job ID[/red]")
            return

        job_id = args[0]
        try:
            await self.orchestrator.job_manager.resume_job(job_id)
            self.console.print(f"[green]✓ Job {job_id} resumed[/green]")
        except Exception as e:
            self.console.print(f"[red]Error resuming job {job_id}: {e}[/red]")

    async def next_job(self, args):
        """Send next instruction to a job."""
        if len(args) < 2:
            self.console.print(
                "[red]Error: Please provide job ID and continuation hint[/red]"
            )
            return

        job_id = args[0]
        continuation = " ".join(args[1:])
        try:
            await self.orchestrator.job_manager.send_next_hint(job_id, continuation)
            self.console.print(f"[green]✓ Next hint sent to job {job_id}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error sending hint to job {job_id}: {e}[/red]")

    async def cancel_job(self, args):
        """Cancel a running job."""
        if not args:
            self.console.print("[red]Error: Please provide a job ID[/red]")
            return

        job_id = args[0]
        try:
            await self.orchestrator.job_manager.cancel_job(job_id)
            self.console.print(f"[green]✓ Job {job_id} canceled[/green]")
        except Exception as e:
            self.console.print(f"[red]Error canceling job {job_id}: {e}[/red]")
