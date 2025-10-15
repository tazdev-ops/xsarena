"""Configuration management for XSArena."""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

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

    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from a YAML file."""
        if config_path is None:
            # Try common config file locations
            for path in [".xsarena/config.yml", ".xsarena/config.yaml", "config.yml", "config.yaml"]:
                if Path(path).exists():
                    config_path = path
                    break
        
        if config_path and Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
            
            # Only set values that are present in the config file
            # This allows defaults to be preserved for missing values
            config_kwargs = {}
            for field_name, field_info in cls.__fields__.items():
                if field_name in config_data:
                    config_kwargs[field_name] = config_data[field_name]
            
            # Also check environment variables (they take precedence over config file)
            env_api_key = os.getenv("OPENROUTER_API_KEY")
            if env_api_key:
                config_kwargs["api_key"] = env_api_key
            
            return cls(**config_kwargs)
        
        # Return default config if no file exists
        return cls()

    def save_to_file(self, config_path: str):
        """Save configuration to a YAML file."""
        config_dict = self.dict()
        # Don't save sensitive information like API keys to the config file
        config_dict.pop("api_key", None)
        
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
