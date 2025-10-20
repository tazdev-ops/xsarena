"""Centralized job resume logic."""
from pathlib import Path
from typing import Optional
import sys
import typer

class ResumeHandler:
    def __init__(self, job_runner):
        self.job_runner = job_runner
    
    def check_and_handle_resume(
        self,
        out_path: str,
        resume: Optional[bool],
        overwrite: bool,
        is_tty: bool = None
    ) -> tuple[bool, Optional[str]]:
        """
        Check for existing job and handle resume/overwrite logic.
        Returns: (should_create_new, existing_job_id)
        """
        if is_tty is None:
            is_tty = sys.stdin.isatty()
        
        existing_job_id = self.job_runner.find_resumable_job_by_output(out_path)
        
        if not existing_job_id:
            return True, None
        
        if overwrite:
            return True, None
        
        if resume is True:
            return False, existing_job_id
        
        if resume is False:
            return True, None
        
        # resume is None (default) - prompt user if TTY
        if is_tty:
            typer.echo(f"Resumable job exists for {out_path}: {existing_job_id}")
            typer.echo("Use --resume to continue or --overwrite to start fresh.")
            raise typer.Exit(2)
        else:
            # Non-interactive: default to resume
            return False, existing_job_id