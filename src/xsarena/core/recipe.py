"""Recipe model for XSArena."""

from typing import List, Optional

from pydantic import BaseModel, Field


class RecipeV2(BaseModel):
    """Recipe model with validation for accepted keys."""

    subject: str = Field(..., description="Subject for the recipe")
    length: str = Field(default="standard", description="Length of the output")
    span: str = Field(default="medium", description="Time span for the recipe")
    overlays: Optional[List[str]] = Field(default=[], description="Overlays to apply")
    extra_files: Optional[List[str]] = Field(
        default=[], description="Extra files to include"
    )
    generate_plan: Optional[bool] = Field(
        default=False, description="Whether to generate a plan"
    )
    out_path: Optional[str] = Field(default=None, description="Output path for results")

    class Config:
        extra = (
            "forbid"  # This will cause validation to fail if unknown keys are provided
        )
