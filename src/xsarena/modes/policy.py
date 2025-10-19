"""Policy analysis modes for XSArena."""

from pathlib import Path
from typing import List, Optional

from ..core.engine import Engine
from ..core.prompt import pcl


class PolicyMode:
    """Handles policy analysis and generation functionality."""

    def __init__(self, engine: Engine):
        self.engine = engine

    async def generate_from_topic(self, topic: str, requirements: str = "", extra_notes: Optional[str] = None) -> str:
        """Generate policy document from a topic and requirements."""
        prompt = f"""Generate a comprehensive policy document about {topic}.

Requirements:
{requirements}

Create a policy that addresses key issues, implementation strategies, and potential challenges."""

        # Build system prompt using PCL with policy role directive
        role_content = self._load_role_directive("policy")
        system_prompt = self._build_system_prompt("policy generation", extra_notes, role_content)
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def analyze_compliance(self, policy: str, evidence_files: List[str], extra_notes: Optional[str] = None) -> str:
        """Analyze policy compliance against evidence files."""
        evidence_text = "\n\n".join(evidence_files)
        prompt = f"""Analyze the following policy for compliance and effectiveness:

Policy:
{policy}

Evidence:
{evidence_text}

Evaluate how well the policy addresses the issues presented in the evidence, identify gaps, and suggest improvements."""

        # Build system prompt using PCL with policy role directive
        role_content = self._load_role_directive("policy")
        system_prompt = self._build_system_prompt("policy compliance analysis", extra_notes, role_content)
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def score_compliance(self, policy: str, evidence_files: List[str], extra_notes: Optional[str] = None) -> str:
        """Score policy compliance against evidence files."""
        evidence_text = "\n\n".join(evidence_files)
        prompt = f"""Score the following policy based on how well it addresses the issues in the provided evidence:

Policy:
{policy}

Evidence:
{evidence_text}

Provide a compliance score from 1-10 with detailed reasoning for the score, highlighting strengths and weaknesses."""

        # Build system prompt using PCL with policy role directive
        role_content = self._load_role_directive("policy")
        system_prompt = self._build_system_prompt("policy scoring", extra_notes, role_content)
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def gap_analysis(self, policy: str, requirements: str, extra_notes: Optional[str] = None) -> str:
        """Analyze gaps between policy and requirements."""
        prompt = f"""Perform a gap analysis comparing this policy to the stated requirements:

Policy:
{policy}

Requirements:
{requirements}

Identify gaps, inconsistencies, and areas where the policy does not adequately address the requirements."""

        # Build system prompt using PCL with policy role directive
        role_content = self._load_role_directive("policy")
        system_prompt = self._build_system_prompt("policy gap analysis", extra_notes, role_content)
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def implementation_checklist(self, policy: str, extra_notes: Optional[str] = None) -> str:
        """Generate an implementation checklist for the policy."""
        prompt = f"""Create a detailed implementation checklist for this policy:

{policy}

Include specific steps, responsibilities, timelines, and success metrics for implementation."""

        # Build system prompt using PCL with policy role directive
        role_content = self._load_role_directive("policy")
        system_prompt = self._build_system_prompt("policy implementation checklist", extra_notes, role_content)
        return await self.engine.send_and_collect(prompt, system_prompt)

    def _load_role_directive(self, role_name: str) -> str:
        """Load content from a role directive file."""
        # Try relative to project root (relative to this file)
        project_root = Path(__file__).parent.parent.parent.parent
        role_path = project_root / "directives" / "roles" / f"{role_name}.md"
        
        if role_path.exists():
            try:
                return role_path.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        
        # Return empty string if not found
        return ""

    def _build_system_prompt(self, subject: str, extra_notes: Optional[str], role_content: str) -> str:
        """Build system prompt using PCL with role directive content."""
        # Compose the prompt using PCL
        composition = pcl.compose(
            subject=subject,
            base="reference",  # Use reference base for structured policy documents
            overlays=["no_bs"],  # Use no_bs overlay for plain English policy writing
            extra_notes=extra_notes
        )
        
        # If role directive exists, append its content to the system text
        if role_content:
            composition.system_text += f"\n\n{role_content}"
        
        return composition.system_text
