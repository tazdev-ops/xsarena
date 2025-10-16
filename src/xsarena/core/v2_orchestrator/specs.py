"""Run specification model for XSArena v0.2."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class LengthPreset(str, Enum):
    """Length presets for runs."""
    STANDARD = "standard"
    LONG = "long"
    VERY_LONG = "very-long"
    MAX = "max"


class SpanPreset(str, Enum):
    """Span presets for runs."""
    MEDIUM = "medium"
    LONG = "long"
    BOOK = "book"


class RunSpecV2(BaseModel):
    """Version 2 run specification with typed fields."""
    subject: str = Field(..., description="The subject to generate content about")
    length: LengthPreset = Field(LengthPreset.LONG, description="Length preset for the run")
    span: SpanPreset = Field(SpanPreset.BOOK, description="Span preset for the run")
    overlays: List[str] = Field(default_factory=lambda: ["narrative", "no_bs"], description="Overlay specifications")
    extra_note: str = Field("", description="Additional notes or instructions")
    extra_files: List[str] = Field(default_factory=list, description="Additional files to include")
    out_path: Optional[str] = Field(None, description="Output path for the result")
    outline_scaffold: Optional[str] = Field(None, description="Outline scaffold to follow")
    
    # Additional fields that might be needed
    profile: Optional[str] = Field(None, description="Profile to use for the run")
    backend: Optional[str] = Field("bridge", description="Backend to use for the run")
    concurrency: int = Field(1, description="Number of concurrent operations")
    timeout: int = Field(300, description="Timeout for operations in seconds")
    
    class Config:
        """Configuration for the model."""
        extra = "forbid"  # Forbid extra fields to catch typos
    
    def resolved(self) -> Dict[str, Any]:
        """Resolve presets to actual values."""
        length_presets = {
            "standard": {"min": 4200, "passes": 1},
            "long": {"min": 5800, "passes": 3},
            "very-long": {"min": 6200, "passes": 4},
            "max": {"min": 6800, "passes": 5},
        }
        
        span_presets = {
            "medium": 12,
            "long": 24,
            "book": 40
        }
        
        length_config = length_presets[self.length.value]
        chunks = span_presets[self.span.value]
        
        return {
            "min_length": length_config["min"],
            "passes": length_config["passes"],
            "chunks": chunks
        }