"""Chad mode (evidence-based Q&A) for LMASudio."""
from typing import List, Dict, Any
from ..core.engine import Engine
from ..core.templates import SYSTEM_PROMPTS

class ChadMode:
    """Handles evidence-based Q&A functionality."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    async def answer_question(self, question: str, context: str = "") -> str:
        """Answer a question based on evidence and context."""
        prompt = f"""Provide a direct, evidence-based answer to this question:

{question}

Context for answering:
{context}

Be concise but thorough. Support your answer with evidence when available. If uncertain, state so clearly."""
        
        system_prompt = SYSTEM_PROMPTS["chad"]
        return await self.engine.send_and_collect(prompt, system_prompt)
    
    async def batch_questions(self, questions_file: str, answers_file: str) -> str:
        """Process a batch of questions from a file and save answers."""
        # Read the questions file
        from ..core.tools import read_file
        questions_content = read_file(questions_file)
        
        # Process each question
        questions = questions_content.strip().split('\n\n')  # Assuming questions are separated by blank lines
        answers = []
        
        for question in questions:
            if question.strip():
                answer = await self.answer_question(question.strip())
                answers.append(f"Q: {question.strip()}\nA: {answer}\n")
        
        # Write answers to the answers file
        answers_content = '\n\n'.join(answers)
        from ..core.tools import write_file
        write_file(answers_file, answers_content)
        
        return f"Processed {len(questions)} questions, answers saved to {answers_file}"
    
    async def evidence_check(self, claim: str, evidence: str) -> str:
        """Check a claim against provided evidence."""
        prompt = f"""Evaluate this claim against the provided evidence:

Claim: {claim}

Evidence: {evidence}

Assess the validity of the claim based on the evidence. Be objective and specific."""
        
        system_prompt = SYSTEM_PROMPTS["chad"]
        return await self.engine.send_and_collect(prompt, system_prompt)
    
    async def source_analysis(self, sources: List[str], question: str) -> str:
        """Analyze multiple sources to answer a question."""
        sources_text = "\n\n".join([f"Source {i+1}: {source}" for i, source in enumerate(sources)])
        
        prompt = f"""Analyze the following sources to answer this question:

Question: {question}

Sources:
{sources_text}

Synthesize information from all sources to provide a comprehensive answer. Note where sources agree or disagree."""
        
        system_prompt = SYSTEM_PROMPTS["chad"]
        return await self.engine.send_and_collect(prompt, system_prompt)
    
    async def fact_check(self, statement: str) -> str:
        """Fact-check a given statement."""
        prompt = f"""Fact-check this statement:

{statement}

Provide evidence for or against the statement. State the veracity clearly and cite sources where possible."""
        
        system_prompt = SYSTEM_PROMPTS["chad"]
        return await self.engine.send_and_collect(prompt, system_prompt)
    
    async def summarize_evidence(self, evidence_list: List[str]) -> str:
        """Summarize a list of evidence points."""
        evidence_text = "\n\n".join([f"Item {i+1}: {item}" for i, item in enumerate(evidence_list)])
        
        prompt = f"""Summarize the following evidence items:

{evidence_text}

Provide a concise summary of the key points and their implications."""
        
        system_prompt = SYSTEM_PROMPTS["chad"]
        return await self.engine.send_and_collect(prompt, system_prompt)