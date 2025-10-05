"""Configuration management for LMASudio."""
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Config(BaseModel):
    """Application configuration."""
    backend: str = "bridge"  # bridge or openrouter
    model: str = "default"
    window_size: int = 100
    anchor_length: int = 300
    continuation_mode: str = "anchor"  # anchor, strict, or off
    repetition_threshold: float = 0.8
    max_retries: int = 3
    api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    base_url: str = "http://localhost:8080/v1"  # Default for bridge
    timeout: int = 300
    redaction_enabled: bool = False
    
    class Config:
        env_file = ".env"