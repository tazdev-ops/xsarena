"""Plugin and profile discovery system for XSArena."""

from importlib.metadata import entry_points
from typing import Any, Dict, List

import yaml

from .project_paths import get_project_root


def discover_profiles() -> Dict[str, Any]:
    """Discover profiles from various sources."""
    profiles = {}

    # Load from default profiles
    from ..core.specs import DEFAULT_PROFILES

    profiles.update(DEFAULT_PROFILES)

    # Load from directives/profiles/presets.yml using project root resolution
    project_root = get_project_root()
    presets_path = project_root / "directives" / "profiles" / "presets.yml"
    if presets_path.exists():
        try:
            data = yaml.safe_load(presets_path.read_text(encoding="utf-8")) or {}
            presets_profiles = data.get("profiles", {})
            if isinstance(presets_profiles, dict):
                profiles.update(presets_profiles)
        except Exception:
            pass  # If we can't read the file, continue with existing profiles

    return profiles


def discover_overlays() -> Dict[str, str]:
    """Discover overlays from directives/style.*.md files."""
    overlays = {}

    # Look for style overlay files using project root resolution
    project_root = get_project_root()
    directives_path = project_root / "directives"
    if directives_path.exists():
        for style_file in directives_path.glob("style.*.md"):
            try:
                content = style_file.read_text(encoding="utf-8")
                # Parse OVERLAY: header if present
                lines = content.splitlines()
                overlay_name = style_file.stem.replace(
                    "style.", ""
                )  # Extract name from filename

                # Look for OVERLAY: header
                overlay_content = []
                for line in lines:
                    if line.startswith("OVERLAY:"):
                        # Extract content after OVERLAY: header
                        overlay_content.append(
                            line[8:].strip()
                        )  # Remove "OVERLAY:" part
                    elif (
                        overlay_content
                    ):  # If we've found the header, continue adding content
                        overlay_content.append(line)

                if overlay_content:
                    overlays[overlay_name] = "\n".join(overlay_content).strip()
                else:
                    # Use entire content if no OVERLAY: header
                    overlays[overlay_name] = content.strip()
            except Exception:
                continue  # Skip files that can't be read

    return overlays


def discover_roles() -> Dict[str, str]:
    """Discover roles from directives/roles/*.md files."""
    roles = {}

    project_root = get_project_root()
    roles_dir = project_root / "directives" / "roles"
    if roles_dir.exists():
        for role_file in roles_dir.glob("*.md"):
            try:
                role_name = role_file.stem
                content = role_file.read_text(encoding="utf-8")
                roles[role_name] = content.strip()
            except Exception:
                continue  # Skip files that can't be read

    return roles


def discover_plugins() -> List[Dict[str, Any]]:
    """Discover plugins via Python entry points."""
    plugins = []

    try:
        # Look for entry points under "xsarena.plugins"
        eps = entry_points()
        if hasattr(eps, "select"):  # New API in Python 3.10+
            plugin_eps = eps.select(group="xsarena.plugins")
        else:  # Old API
            plugin_eps = eps.get("xsarena.plugins", [])

        for ep in plugin_eps:
            try:
                plugin_func = ep.load()
                plugin_data = plugin_func()
                if isinstance(plugin_data, dict):
                    plugins.append(plugin_data)
            except Exception:
                continue  # Skip plugins that fail to load
    except Exception:
        pass  # Entry points not available on older Python versions

    return plugins


def merge_discovered_config() -> Dict[str, Any]:
    """Merge all discovered configurations into a unified structure."""
    config = {
        "profiles": discover_profiles(),
        "overlays": discover_overlays(),
        "roles": discover_roles(),
        "plugins": discover_plugins(),
    }
    return config


def list_profiles() -> List[Dict[str, Any]]:
    """List all available profiles with their sources."""
    profiles = discover_profiles()
    result = []
    for name, profile in profiles.items():
        result.append(
            {
                "name": name,
                "description": profile.get("description", ""),
                "overlays": profile.get("overlays", []),
                "extra": profile.get("extra", ""),
                "source": "built-in",  # or file path if loaded from file
            }
        )
    return result


def list_overlays() -> List[Dict[str, Any]]:
    """List all available overlays with their sources."""
    overlays = discover_overlays()
    result = []
    for name, content in overlays.items():
        result.append(
            {
                "name": name,
                "content_preview": (
                    content[:100] + "..." if len(content) > 100 else content
                ),
                "source": f"directives/style.{name}.md",
            }
        )
    return result


def list_roles() -> List[Dict[str, Any]]:
    """List all available roles with their sources."""
    roles = discover_roles()
    result = []
    for name, content in roles.items():
        result.append(
            {
                "name": name,
                "content_preview": (
                    content[:100] + "..." if len(content) > 100 else content
                ),
                "source": f"directives/roles/{name}.md",
            }
        )
    return result
