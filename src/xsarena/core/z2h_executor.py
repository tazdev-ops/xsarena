"""Z2HExecutor - Zero-to-Hero execution engine with section writing, outline parsing, and failover capabilities"""

import json
import os
from typing import Any, Dict, List

from . import costs
from .artifacts import combine_sections, write_aid, write_outline, write_plan, write_section
from .backends import get_backend
from .planner import parse_outline, pick_anchor, target_chars
from .state import SessionState


class Z2HExecutor:
    """
    Z2HExecutor - Zero-to-Hero execution engine with:
    - run_outline → parse → plan.json
    - run_next_section loop
    - combine
    - aids fan-out (sequential)
    - failover
    - watchdog
    - cancellation
    """

    def __init__(self, job_runner, job_id: str, playbook: Dict[str, Any], params: Dict[str, Any], backend: str):
        self.job_runner = job_runner
        self.job_id = job_id
        self.playbook = playbook
        self.params = params
        self.backend = backend
        self.jobs_dir = job_runner.jobs_dir

        # State
        self.state = SessionState()
        self.state.session_mode = "zero2hero"
        self.state.coverage_hammer_on = playbook.get("hammer", True)
        self.state.output_min_chars = params.get("continuation", {}).get("minChars", 3000)
        self.state.watchdog_secs = playbook.get("failover", {}).get("watchdog_secs", 45)

        # Initialize backend
        from .backends import get_backend

        self.backend_instance = get_backend(backend, playbook.get("model"))
        self.state.job_id = job_id

    async def run_outline(self) -> str:
        """Generate outline and parse it into plan.json"""
        from .engine import Engine

        engine = Engine(self.backend_instance, self.state)

        subject = self.playbook["subject"]
        outline_prompt = f"Create a detailed outline for a comprehensive book about '{subject}'. Include chapters with their subtopics."
        outline_response = await engine.send_and_collect(outline_prompt)

        # Write outline artifact
        outline_path = write_outline(self.job_id, outline_response)

        # Parse the outline and create plan
        plan_dict = parse_outline(outline_response, subject)
        plan_path = write_plan(self.job_id, plan_dict)

        # Record event
        self.job_runner.write_event(self.job_id, {"type": "outline_completed", "chars": len(outline_response)})

        return plan_path

    async def run_next_section(self, section_num: int, plan_path: str) -> str:
        """Run next section based on plan, with cancellation and failover support"""
        from .engine import Engine

        engine = Engine(self.backend_instance, self.state)

        # Load current plan
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_dict = json.load(f)

        subject = self.playbook["subject"]
        max_retries = self.playbook.get("failover", {}).get("max_retries", 3)
        fallback_backend_name = self.playbook.get("failover", {}).get("fallback_backend", "openrouter")

        # Use last section content or outline as anchor
        anchor = ""
        if section_num > 1:
            prev_section_path = os.path.join(self.jobs_dir, self.job_id, f"section_{section_num-1}.md")
            if os.path.exists(prev_section_path):
                with open(prev_section_path, "r", encoding="utf-8") as f:
                    prev_content = f.read()
                    anchor = pick_anchor(prev_content)
        else:
            # For first section, use outline as context
            outline_path = os.path.join(self.jobs_dir, self.job_id, "outline.md")
            if os.path.exists(outline_path):
                with open(outline_path, "r", encoding="utf-8") as f:
                    anchor = pick_anchor(f.read(), 400)

        # Calculate target character length with adaptive adjustment based on previous chunks
        system_text = self.playbook.get("system_text", "")
        target_length = target_chars(
            system_text, anchor, job_id=self.job_id, current_target=self.state.output_min_chars
        )

        # Build the prompt with system instructions and continuation
        if section_num == 1:
            prompt = f"BEGIN writing a comprehensive book about '{subject}'. Use the following guidelines: {system_text}\n\n{anchor}"
        else:
            prompt = f"Continue writing the book about '{subject}', building on what you've already established. Use the following guidelines: {system_text}\n\nPrevious context: {anchor}"

        # Send to engine with watchdog and cancellation handling
        import asyncio

        try:
            engine.state.output_min_chars = target_length
            response = await asyncio.wait_for(
                engine.send_and_collect(prompt, system_prompt=system_text), timeout=self.state.watchdog_secs
            )
        except asyncio.TimeoutError:
            self.job_runner.write_event(
                self.job_id,
                {"type": "watchdog_timeout", "section": section_num, "timeout_secs": self.state.watchdog_secs},
            )
            raise Exception("Watchdog timeout")  # This will trigger failover or cancellation handling

        # Write section artifact
        section_path = write_section(self.job_id, section_num, response)

        # Update plan.json to mark section as done
        plan_dict["last_next"] = f"Continue to section {section_num + 1}"
        if "completed_sections" not in plan_dict:
            plan_dict["completed_sections"] = []
        if section_num not in plan_dict["completed_sections"]:
            plan_dict["completed_sections"].append(section_num)

        # Update chapter status if available
        if "chapters" in plan_dict:
            for chapter in plan_dict["chapters"]:
                if chapter["n"] == section_num:
                    chapter["status"] = "done"
                    break

        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, indent=2)

        # Calculate costs for this chunk
        cost_estimate = costs.estimate_cost(
            [{"role": "assistant", "content": response}],
            self.backend_instance.name if hasattr(self.backend_instance, "name") else "unknown",
        )

        # Record the cost event
        cost_event = {
            "type": "cost",
            "input_tokens": cost_estimate["input_tokens"],
            "output_tokens": cost_estimate["output_tokens"],
            "est_usd": cost_estimate["estimated_cost"],
            "model": getattr(self.backend_instance, "model", "unknown"),
        }
        self.job_runner.write_event(self.job_id, cost_event)

        # Update job's total cost
        job = self.job_runner.load(self.job_id)
        job.meta["total_cost_usd"] = job.meta.get("total_cost_usd", 0.0) + cost_estimate["estimated_cost"]
        self.job_runner._update_job(job)

        # Check budget
        budget_usd = self.playbook.get("budget_usd") or self.job_runner.project_defaults.get("budget", {}).get(
            "default_usd"
        )
        if budget_usd and job.meta["total_cost_usd"] > budget_usd:
            budget_event = {
                "type": "budget_exceeded",
                "total_usd": job.meta["total_cost_usd"],
                "budget_limit": budget_usd,
            }
            self.job_runner.write_event(self.job_id, budget_event)
            raise Exception("Budget exceeded")

        # Lint the content for quality
        from .lintdoc import lint_chunk

        lint_results = lint_chunk(response, self.playbook.get("subject", ""))

        # Write lint results to event log
        if lint_results["has_issues"]:
            self.job_runner.write_event(
                self.job_id,
                {
                    "type": "lint_warning",
                    "section": section_num,
                    "issues": lint_results["issues"],
                    "score": lint_results["overall_score"],
                },
            )
        else:
            # Warn if NEXT marker is missing but still advance by plan order
            next_check = lint_results["next_marker"]
            if not next_check["has_next"]:
                self.job_runner.write_event(
                    self.job_id,
                    {
                        "type": "lint_warning",
                        "section": section_num,
                        "issues": ["NEXT: marker missing (continuing by plan order)"],
                        "next_present": False,
                    },
                )

        # Record the chunk completion
        self.job_runner.write_event(
            self.job_id,
            {
                "type": "chunk_done",
                "section": section_num,
                "chars": len(response),
                "next": plan_dict.get("last_next", f"Continue to section {section_num + 1}"),
            },
        )

        return section_path

    async def combine(self) -> str:
        """Combine sections into final document"""
        final_path = combine_sections(self.job_id)
        return final_path

    async def run_aids_fanout(self, final_path: str) -> List[str]:
        """Generate aids as fan-out jobs"""
        aids_paths = []
        subject = self.playbook["subject"]

        if self.playbook.get("aids") and self.playbook.get("aids") != [None]:  # Check if aids were specified
            for aid_type in self.playbook["aids"]:
                if aid_type == "cram":
                    cram_content = f"# Cram Sheet for {subject}\n\nThis is a cram sheet based on the comprehensive book about {subject}.\n\n## Key Points\n- Point 1\n- Point 2\n- Point 3"
                    cram_path = write_aid(self.job_id, "cram", cram_content)
                    aids_paths.append(cram_path)
                elif aid_type == "flashcards":
                    flashcards_content = f"# Flashcards for {subject}\n\n## Card 1\nQ: What is the main concept?\nA: {subject} is a comprehensive field.\n\n## Card 2\nQ: What are the core principles?\nA: There are several key principles.\n\n## Card 3\nQ: What are the applications?\nA: Applications are diverse."
                    flashcards_path = write_aid(self.job_id, "flashcards", flashcards_content)
                    aids_paths.append(flashcards_path)
                elif aid_type == "glossary":
                    glossary_content = f"# Glossary for {subject}\n\n## Key Terms\n\n**Term 1**: Definition of term 1.\n\n**Term 2**: Definition of term 2.\n\n**Term 3**: Definition of term 3."
                    glossary_path = write_aid(self.job_id, "glossary", glossary_content)
                    aids_paths.append(glossary_path)
                elif aid_type == "index":
                    index_content = f"# Index for {subject}\n\n## Topics Covered\n\n- Topic 1: Page X\n- Topic 2: Page Y\n- Topic 3: Page Z"
                    index_path = write_aid(self.job_id, "index", index_content)
                    aids_paths.append(index_path)

        return aids_paths

    async def execute_full_workflow(self, max_chunks: int = 8) -> Dict[str, Any]:
        """Execute the full Z2H workflow with all features"""
        # First, run the outline generation
        plan_path = await self.run_outline()

        # Load plan to get initial section number
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_dict = json.load(f)
        completed_sections = plan_dict.get("completed_sections", [])
        current_section = len(completed_sections) + 1  # Continue from next section

        # Run sections in a loop
        while current_section <= max_chunks:
            # Check if job was cancelled
            current_job = self.job_runner.load(self.job_id)
            if current_job.state == "CANCELLED":
                current_job.state = "CANCELLED"
                self.job_runner._update_job(current_job)
                break

            try:
                await self.run_next_section(current_section, plan_path)
                current_section += 1
            except Exception as e:
                # Handle watchdog timeout and cancellation
                if "watchdog" in str(e).lower() or "timeout" in str(e).lower():
                    current_job.state = "STALLED"
                    self.job_runner._update_job(current_job)
                    self.job_runner.write_event(
                        self.job_id, {"type": "watchdog_timeout", "error": str(e), "section": current_section}
                    )
                    break
                elif "cancel" in str(e).lower() or current_job.state == "CANCELLED":
                    current_job.state = "CANCELLED"
                    self.job_runner._update_job(current_job)
                    self.job_runner.write_event(self.job_id, {"type": "job_cancelled", "reason": str(e)})
                    break
                else:
                    # Handle retries and failover
                    max_retries = self.playbook.get("failover", {}).get("max_retries", 3)
                    fallback_backend_name = self.playbook.get("failover", {}).get("fallback_backend", "openrouter")
                    retry_count = 0

                    while retry_count < max_retries:
                        retry_count += 1
                        self.job_runner.write_event(
                            self.job_id,
                            {"type": "retry", "attempt": retry_count, "error": str(e), "section": current_section},
                        )

                        # Simple backoff before retry (5s/15s/45s)
                        import time

                        backoff_time = min(45, 5 * (3 ** (retry_count - 1)))  # 5s, 15s, 45s
                        self.job_runner.write_event(
                            self.job_id, {"type": "retry_backoff", "backoff_secs": backoff_time, "attempt": retry_count}
                        )
                        time.sleep(backoff_time)

                        try:
                            # Try to run the section again
                            await self.run_next_section(current_section, plan_path)
                            break  # Success, exit retry loop
                        except Exception as retry_e:
                            if retry_count >= max_retries:
                                # Try failover to fallback backend
                                if self.backend != fallback_backend_name:
                                    self.job_runner.write_event(
                                        self.job_id,
                                        {
                                            "type": "failover",
                                            "to_backend": fallback_backend_name,
                                            "section": current_section,
                                        },
                                    )

                                    # Create transplant summary
                                    from .summary import make_transplant_summary

                                    transplant_summary = make_transplant_summary(self.job_id, self.jobs_dir)

                                    # Switch to fallback backend and continue
                                    self.backend_instance = get_backend(
                                        fallback_backend_name, self.playbook.get("model")
                                    )
                                    self.backend = fallback_backend_name

                                    # Apply transplant summary to engine state
                                    if transplant_summary:
                                        self.state.transplant_summary = transplant_summary

                                    # Reset retry count and try again
                                    retry_count = 0
                                    continue  # Continue with the new backend
                                else:
                                    # Failover not possible or failed, mark as failed
                                    current_job.state = "FAILED"
                                    self.job_runner._update_job(current_job)
                                    self.job_runner.write_event(
                                        self.job_id, {"type": "job_failed", "error": str(retry_e)}
                                    )
                                    return {"status": "FAILED", "error": str(retry_e)}
                            # Otherwise, continue to next retry
                    else:
                        # If we exhausted retries without success or failover
                        current_job.state = "FAILED"
                        self.job_runner._update_job(current_job)
                        self.job_runner.write_event(self.job_id, {"type": "job_failed", "error": str(e)})
                        return {"status": "FAILED", "error": str(e)}

        # After all sections are done, combine them and generate aids
        final_path = await self.combine()
        aids_paths = await self.run_aids_fanout(final_path)

        # Update job as completed
        current_job = self.job_runner.load(self.job_id)
        current_job.state = "DONE"
        self.job_runner._update_job(current_job)
        self.job_runner.write_event(self.job_id, {"type": "job_completed"})

        return {
            "status": "DONE",
            "final_path": final_path,
            "aids_paths": aids_paths,
            "sections_completed": current_section - 1,
        }
