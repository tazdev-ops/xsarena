"""Prompt templates for LMASudio."""
from typing import Dict, List

# System prompts for different modes
SYSTEM_PROMPTS = {
    "book": """You are a skilled author helping write a comprehensive book. 
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing.""",
    
    "lossless": """You are a precise text processor. Your goal is to improve text while preserving all original meaning.
Improve grammar, clarity, and flow. Break up dense paragraphs. Add structure where appropriate.
Preserve all facts, details, and specific information. Do not add new content or opinions.
Format responses in markdown.""",
    
    "bilingual": """You are a translation and alignment expert. Translate text accurately between languages.
Maintain the original meaning and context. Provide translation that is natural in the target language.""",
    
    "policy": """You are a policy analysis expert. Review the provided text for policy compliance, evidence, and recommendations.
Provide clear, actionable feedback focused on policy implications and implementation feasibility.""",
    
    "chad": """You are an evidence-based Q&A assistant. Provide direct, factual answers based on available information.
Be concise but thorough. When uncertain, state so clearly. Support your responses with evidence when possible.""",
    
    "coder": """You are an expert programmer. Provide accurate, efficient code solutions.
Follow best practices for the language being used. Include clear comments and error handling where appropriate."""
}

# User instruction templates
USER_PROMPTS = {
    "outline": "Create a detailed outline for a book about {topic}. Include main chapters, subsections, and key points for each section.",
    
    "chapter": "Write Chapter {chapter_num} titled '{chapter_title}' of the book about {topic}. Use the following outline: {outline_section}",
    
    "polish": "Review and improve this text: {text}\n\nFocus on tightening prose, removing repetition, and improving flow while preserving all facts and details.",
    
    "shrink": "Condense this text to approximately 70% of its current length while preserving all facts and key information: {text}",
    
    "diagram": "Generate a mermaid diagram for: {description}\n\nChoose the most appropriate diagram type (flowchart, sequence, mindmap, etc.)",
    
    "quiz": "Generate flashcards or quiz questions from this content: {content}\n\nCreate {num_questions} questions with answers.",
    
    "critique": "Critique this text for repetition, flow issues, and clarity: {text}"
}

# Continuation prompts
CONTINUATION_PROMPTS = {
    "strict": """[STRICT CONTINUATION] Continue writing from where the previous text left off. 
Maintain the same style, tone, and content direction. Don't repeat what was already said.
Keep the same voice and perspective that was established. The next content should flow naturally from the previous text.
{anchor_context}""",
    
    "anchor": """[CONTINUATION FROM CONTEXT] Using the context provided, continue the content in the same style and direction.
{anchor_context}

Continue writing from this point, maintaining consistency with the established content."""
}

# Repetition handling prompts
REPETITION_PROMPTS = {
    "retry": """[STRICT CONTINUATION] Continue writing from where the previous text left off. 
This is a retry after detecting repetition. Focus on advancing the content in a new direction.
Avoid repeating concepts, phrases, or sentence structures from the previous response.
{anchor_context}"""
}