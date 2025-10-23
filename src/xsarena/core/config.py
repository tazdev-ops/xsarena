# src/xsarena/core/config.py
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from rich.console import Console

load_dotenv()

console = Console()


class Config(BaseModel):
    backend: str = "bridge"  # Default to browser-based bridge; API backends are optional for advanced use
    model: str = "default"
    window_size: int = 100
    anchor_length: int = 300
    continuation_mode: str = "anchor"
    repetition_threshold: float = 0.35
    max_retries: int = 3
    api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    base_url: str = "http://127.0.0.1:5102/v1"  # Default to v2 bridge port
    timeout: int = 300
    redaction_enabled: bool = False

    @model_validator(mode="after")
    def validate_config(self) -> "Config":
        """Validate configuration values."""
        errors = []

        # Validate backend
        if self.backend not in ("bridge", "openrouter", "null"):
            errors.append(
                f"Invalid backend: {self.backend}. Valid options are: bridge, openrouter, null"
            )

        # Validate model
        if self.backend == "openrouter" and not self.api_key:
            errors.append(
                "OpenRouter backend requires api_key. Set OPENROUTER_API_KEY environment "
                "variable or configure in .xsarena/config.yml"
            )

        # Validate base_url format
        if self.base_url and not self.base_url.startswith(("http://", "https://")):
            errors.append(
                f"Invalid base_url format: {self.base_url}. Must start with http:// or https://"
            )

        # Validate numeric ranges
        if self.window_size < 1 or self.window_size > 1000:
            errors.append(f"window_size must be between 1-1000, got {self.window_size}")

        if self.anchor_length < 50 or self.anchor_length > 1000:
            errors.append(
                f"anchor_length must be between 50-1000, got {self.anchor_length}"
            )

        if self.repetition_threshold < 0 or self.repetition_threshold > 1:
            errors.append(
                f"repetition_threshold must be between 0-1, got {self.repetition_threshold}"
            )

        if self.max_retries < 0 or self.max_retries > 10:
            errors.append(f"max_retries must be between 0-10, got {self.max_retries}")

        if self.timeout < 1 or self.timeout > 3600:
            errors.append(f"timeout must be between 1-3600 seconds, got {self.timeout}")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))

        return self

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, v: str) -> str:
        """Normalize base_url to always end with /v1"""
        v = (v or "").strip()
        if not v:
            return "/v1"
        v = v.rstrip("/")
        if not v.endswith("/v1"):
            v = v + "/v1"
        return v

    def save_to_file(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump()
        p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: str) -> "Config":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return cls(**data)
        except ValidationError as e:
            console.print(f"[red]Validation error in config file {path}:[/red]")
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                console.print(f"  [yellow]{field}:[/yellow] {error['msg']}")
            raise
        except Exception:
            return cls()

    @classmethod
    def load_with_layered_config(
        cls, config_file_path: Optional[str] = ".xsarena/config.yml"
    ) -> "Config":
        """Load config with layered precedence:
        defaults → .xsarena/config.yml → environment variables → CLI flags (applied by main).
        """
        """Load config with layered precedence:
        defaults → .xsarena/config.yml → environment variables → CLI flags (applied by main).
        """
        # Start with defaults
        config_dict: Dict[str, Any] = {
            "backend": "bridge",  # Default to browser-based bridge; API backends are optional for advanced use
            "model": "default",
            "window_size": 100,
            "anchor_length": 300,
            "continuation_mode": "anchor",
            "repetition_threshold": 0.35,
            "max_retries": 3,
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "base_url": "http://127.0.0.1:5102/v1",
            "timeout": 300,
            "redaction_enabled": False,
        }

        # Load from config file if it exists
        if config_file_path:
            config_path = Path(config_file_path)
            if config_path.exists():
                try:
                    file_config = (
                        yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                    )
                    # Validate the file config keys against the model fields
                    unknown_keys = set(file_config.keys()) - set(
                        cls.model_fields.keys()
                    )
                    if unknown_keys:
                        console.print(
                            f"[yellow]Warning: Unknown config keys in {config_file_path}:[/yellow] "
                            f"{', '.join(sorted(unknown_keys))}"
                        )

                    config_dict.update(file_config)
                except Exception as e:
                    console.print(
                        f"[red]Error loading config file {config_file_path}: {e}[/red]"
                    )

        # Override with environment variables
        env_overrides: Dict[str, Any] = {}
        backend_env = os.getenv("XSARENA_BACKEND")
        if backend_env is not None:
            env_overrides["backend"] = backend_env
        model_env = os.getenv("XSARENA_MODEL")
        if model_env is not None:
            env_overrides["model"] = model_env
        window_size_env = os.getenv("XSARENA_WINDOW_SIZE")
        if window_size_env is not None:
            env_overrides["window_size"] = int(window_size_env)
        anchor_length_env = os.getenv("XSARENA_ANCHOR_LENGTH")
        if anchor_length_env is not None:
            env_overrides["anchor_length"] = int(anchor_length_env)
        continuation_mode_env = os.getenv("XSARENA_CONTINUATION_MODE")
        if continuation_mode_env is not None:
            env_overrides["continuation_mode"] = continuation_mode_env
        repetition_threshold_env = os.getenv("XSARENA_REPETITION_THRESHOLD")
        if repetition_threshold_env is not None:
            env_overrides["repetition_threshold"] = float(repetition_threshold_env)
        max_retries_env = os.getenv("XSARENA_MAX_RETRIES")
        if max_retries_env is not None:
            env_overrides["max_retries"] = int(max_retries_env)
        api_key_env = os.getenv("OPENROUTER_API_KEY")
        if api_key_env is not None:
            env_overrides["api_key"] = api_key_env
        base_url_env = os.getenv("XSARENA_BASE_URL")
        if base_url_env is not None:
            env_overrides["base_url"] = base_url_env
        timeout_env = os.getenv("XSARENA_TIMEOUT")
        if timeout_env is not None:
            env_overrides["timeout"] = int(timeout_env)
        redaction_enabled_env = os.getenv("XSARENA_REDACTION_ENABLED")
        if redaction_enabled_env is not None:
            env_overrides["redaction_enabled"] = redaction_enabled_env.lower() in (
                "true",
                "1",
                "yes",
            )

        config_dict.update(env_overrides)

        # Create and return the validated config
        return cls(**config_dict)

    @classmethod
    def validate_config_keys(cls, config_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate config keys and return unknown keys with suggestions"""
        unknown_keys = {}
        for key in config_data:
            if key not in cls.model_fields:
                # Simple suggestion: find closest matching field
                suggestions = [
                    field for field in cls.model_fields if key in field or field in key
                ]
                unknown_keys[key] = suggestions[:3]  # Return up to 3 suggestions
        return unknown_keys
