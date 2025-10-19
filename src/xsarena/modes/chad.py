"""Chad mode (evidence-based Q&A) for XSArena."""

from pathlib import Path
from typing import List, Optional

from ..core.engine import Engine
from ..core.prompt import pcl


class ChadMode:
    """Handles evidence-based Q&A functionality."""

    def __init__(self, engine: Engine):
        self.engine = engine

    async def answer_question(
        self, question: str, context: str = "", extra_notes: Optional[str] = None
    ) -> str:
        """Answer a question based on evidence and context."""
        prompt = f"""Provide a direct, evidence-based answer to this question:

{question}

Context for answering:
{context}

Be concise but thorough. Support your answer with evidence when available. If uncertain, state so clearly."""

        # Build system prompt using PCL with chad role directive
        role_content = self._load_role_directive("chad")
        system_prompt = self._build_system_prompt(
            "evidence-based Q&A", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def batch_questions(
        self, questions_file: str, answers_file: str, extra_notes: Optional[str] = None
    ) -> str:
        """Process a batch of questions from a file and save answers."""
        # Read the questions file
        from ..core.tools import read_file

        questions_content = read_file(questions_file)

        # Process each question
        questions = questions_content.strip().split(
            "\n\n"
        )  # Assuming questions are separated by blank lines
        answers = []

        for question in questions:
            if question.strip():
                answer = await self.answer_question(
                    question.strip(), extra_notes=extra_notes
                )
                answers.append(f"Q: {question.strip()}\nA: {answer}\n")

        # Write answers to the answers file
        answers_content = "\n\n".join(answers)
        from ..core.tools import write_file

        write_file(answers_file, answers_content)

        return f"Processed {len(questions)} questions, answers saved to {answers_file}"

    async def evidence_check(
        self, claim: str, evidence: str, extra_notes: Optional[str] = None
    ) -> str:
        """Check a claim against provided evidence."""
        prompt = f"""Evaluate this claim against the provided evidence:

Claim: {claim}

Evidence: {evidence}

Assess the validity of the claim based on the evidence. Be objective and specific."""

        # Build system prompt using PCL with chad role directive
        role_content = self._load_role_directive("chad")
        system_prompt = self._build_system_prompt(
            "evidence evaluation", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def source_analysis(
        self, sources: List[str], question: str, extra_notes: Optional[str] = None
    ) -> str:
        """Analyze multiple sources to answer a question."""
        sources_text = "\n\n".join(
            [f"Source {i+1}: {source}" for i, source in enumerate(sources)]
        )

        prompt = f"""Analyze the following sources to answer this question:

Question: {question}

Sources:
{sources_text}

Synthesize information from all sources to provide a comprehensive answer. Note where sources agree or disagree."""

        # Build system prompt using PCL with chad role directive
        role_content = self._load_role_directive("chad")
        system_prompt = self._build_system_prompt(
            "source analysis", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def fact_check(
        self, statement: str, extra_notes: Optional[str] = None
    ) -> str:
        """Fact-check a given statement."""
        prompt = f"""Fact-check this statement:

{statement}

Provide evidence for or against the statement. State the veracity clearly and cite sources where possible."""

        # Build system prompt using PCL with chad role directive
        role_content = self._load_role_directive("chad")
        system_prompt = self._build_system_prompt(
            "fact checking", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def summarize_evidence(
        self, evidence_list: List[str], extra_notes: Optional[str] = None
    ) -> str:
        """Summarize a list of evidence points."""
        evidence_text = "\n\n".join(
            [f"Item {i+1}: {item}" for i, item in enumerate(evidence_list)]
        )

        prompt = f"""Summarize the following evidence items:

{evidence_text}

Provide a concise summary of the key points and their implications."""

        # Build system prompt using PCL with chad role directive
        role_content = self._load_role_directive("chad")
        system_prompt = self._build_system_prompt(
            "evidence summarization", extra_notes, role_content
        )
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

    def _build_system_prompt(
        self, subject: str, extra_notes: Optional[str], role_content: str
    ) -> str:
        """Build system prompt using PCL with role directive content."""
        # Compose the prompt using PCL
        composition = pcl.compose(
            subject=subject,
            base="reference",  # Use reference base for factual accuracy
            overlays=[
                "no_bs"
            ],  # Use no_bs overlay for direct, evidence-based responses
            extra_notes=extra_notes,
        )

        # If role directive exists, append its content to the system text
        if role_content:
            composition.system_text += f"\n\n{role_content}"

        return composition.system_text
