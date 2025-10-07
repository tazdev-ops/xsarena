from typing import Any, Dict

import yaml


def load_playbook(path: str) -> Dict[str, Any]:
    """Load a playbook from a YAML file"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def merge_defaults(pb: Dict[str, Any], proj: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Merge playbook, project defaults, and params with proper precedence"""
    result = {}

    # Start with project defaults
    result.update(proj)

    # Override with playbook values
    for key, value in pb.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            # Recursively merge nested dictionaries
            result[key] = merge_nested_dict(result[key], value)
        else:
            result[key] = value

    # Override with params
    for key, value in params.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            # Recursively merge nested dictionaries
            result[key] = merge_nested_dict(result[key], value)
        else:
            result[key] = value

    return result


def merge_nested_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Helper function to recursively merge nested dictionaries"""
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = merge_nested_dict(result[key], value)
        else:
            result[key] = value
    return result
