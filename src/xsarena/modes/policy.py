"""Policy analysis modes for XSArena."""

from pathlib import Path
from typing import List

from ..core.engine import Engine


# Load templates directly from directive files
def _load_directive_content(file_path: str) -> str:
    """Load content from a directive file."""
    # First try relative to current working directory
    if Path(file_path).exists():
        return Path(file_path).read_text(encoding="utf-8").strip()

    # Try relative to project root (relative to this file)
    project_root = Path(__file__).parent.parent.parent.parent
    full_path = project_root / file_path
    if full_path.exists():
        return full_path.read_text(encoding="utf-8").strip()

    # Return empty string if not found
    return ""


# Load system prompts from directive files
SYSTEM_PROMPTS = {
    "policy": _load_directive_content("directives/roles/policy.md"),
}

# Fallback hardcoded value if directive file is not available
if not SYSTEM_PROMPTS["policy"]:
    SYSTEM_PROMPTS[
        "policy"
    ] = "You are a policy analysis assistant. Generate comprehensive policy documents with implementation strategies."


class PolicyMode:
    """Handles policy analysis and generation functionality."""

    def __init__(self, engine: Engine):
        self.engine = engine

    async def generate_from_topic(self, topic: str, requirements: str = "") -> str:
        """Generate policy document from a topic and requirements."""
        prompt = f"""Generate a comprehensive policy document about {topic}.

Requirements:
{requirements}

Create a policy that addresses key issues, implementation strategies, and potential challenges."""

        system_prompt = SYSTEM_PROMPTS["policy"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def analyze_compliance(self, policy: str, evidence_files: List[str]) -> str:
        """Analyze policy compliance against evidence files."""
        evidence_text = "\n\n".join(evidence_files)
        prompt = f"""Analyze the following policy for compliance and effectiveness:

Policy:
{policy}

Evidence:
{evidence_text}

Evaluate how well the policy addresses the issues presented in the evidence, identify gaps, and suggest improvements."""

        system_prompt = SYSTEM_PROMPTS["policy"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def score_compliance(self, policy: str, evidence_files: List[str]) -> str:
        """Score policy compliance against evidence files."""
        evidence_text = "\n\n".join(evidence_files)
        prompt = f"""Score the following policy based on how well it addresses the issues in the provided evidence:

Policy:
{policy}

Evidence:
{evidence_text}

Provide a compliance score from 1-10 with detailed reasoning for the score, highlighting strengths and weaknesses."""

        system_prompt = SYSTEM_PROMPTS["policy"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def gap_analysis(self, policy: str, requirements: str) -> str:
        """Analyze gaps between policy and requirements."""
        prompt = f"""Perform a gap analysis comparing this policy to the stated requirements:

Policy:
{policy}

Requirements:
{requirements}

Identify gaps, inconsistencies, and areas where the policy does not adequately address the requirements."""

        system_prompt = SYSTEM_PROMPTS["policy"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def implementation_checklist(self, policy: str) -> str:
        """Generate an implementation checklist for the policy."""
        prompt = f"""Create a detailed implementation checklist for this policy:

{policy}

Include specific steps, responsibilities, timelines, and success metrics for implementation."""

        system_prompt = SYSTEM_PROMPTS["policy"]
        return await self.engine.send_and_collect(prompt, system_prompt)
