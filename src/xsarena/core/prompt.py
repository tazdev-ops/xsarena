"""Prompt Composition Layer (PCL) - Centralized prompt composition with schema and lints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..utils.discovery import discover_overlays
from ..utils.project_paths import get_project_root
from .manifest import load_manifest


@dataclass
class PromptComposition:
    """Result of prompt composition with applied settings and warnings."""

    system_text: str
    applied: Dict[str, Any]
    warnings: List[str]


class PromptCompositionLayer:
    """Centralized prompt composition with schema and lints."""

    # Base modes and their descriptions
    BASE_MODES = {
        "zero2hero": "pedagogical manual from foundations to practice",
        "reference": "tight reference handbook with definitions first",
        "pop": "accessible narrative explainer with vignettes",
        "nobs": "no‑bullshit manual with tight prose",
    }

    # Overlay options
    OVERLAYS = {
        "no_bs": "Plain language. No fluff. Concrete nouns; tight sentences.",
        "narrative": "Teach-before-use narrative. Define terms at first mention.",
        "compressed": "Compressed narrative. Minimal headings; dense flow.",
        "bilingual": "Mirror structure and translate line-for-line as pairs.",
    }

    def __init__(self):
        self._load_extended_templates()

    def _load_extended_templates(self):
        """Load richer templates from directive files using discovery."""
        # Load overlays using discovery utility
        discovered_overlays = discover_overlays()

        # Update overlays with discovered content, keeping fallbacks for missing ones
        for overlay_name, overlay_content in discovered_overlays.items():
            if overlay_content.strip():
                self.OVERLAYS[overlay_name] = overlay_content

        # Load manifest for additional overlays if available
        manifest = load_manifest()
        manifest_overlays = manifest.get("overlays", [])
        for overlay_info in manifest_overlays:
            if (
                isinstance(overlay_info, dict)
                and "name" in overlay_info
                and "content" in overlay_info
            ):
                self.OVERLAYS[overlay_info["name"]] = overlay_info["content"]

    def compose(
        self,
        subject: str,
        base: str = "zero2hero",
        overlays: Optional[List[str]] = None,
        extra_notes: Optional[str] = None,
        min_chars: int = 4200,
        passes: int = 1,
        max_chunks: int = 12,
    ) -> PromptComposition:
        """
        Compose a final system prompt from base mode, overlays, and subject.

        Args:
            subject: The subject to write about
            base: Base mode (zero2hero, reference, pop, nobs)
            overlays: List of style overlays to apply
            extra_notes: Additional domain-specific notes
            min_chars: Minimum chars per chunk
            passes: Auto-extend passes per chunk
            max_chunks: Maximum number of chunks

        Returns:
            PromptComposition with system_text, applied settings, and warnings
        """
        if overlays is None:
            overlays = []

        # Validate inputs
        warnings = []
        if base not in self.BASE_MODES:
            base = "zero2hero"  # fallback
            warnings.append(f"Unknown base mode '{base}', using 'zero2hero'")

        invalid_overlays = [ov for ov in overlays if ov not in self.OVERLAYS]
        if invalid_overlays:
            warnings.extend([f"Unknown overlay '{ov}'" for ov in invalid_overlays])
            overlays = [ov for ov in overlays if ov in self.OVERLAYS]

        # Build the system text
        parts = []

        # Base intent - try to get from manifest first, then fallback to current logic
        manifest = load_manifest()
        base_templates = manifest.get("prompts", [])

        # Look for the base template in the manifest
        base_template = None
        for template in base_templates:
            if isinstance(template, dict) and template.get("name") == base:
                base_template = template.get("content", "")
                break

        if base_template:
            # Use the template from manifest, replacing {subject} placeholder
            base_content = base_template.replace("{subject}", subject)
            parts.append(base_content)
        else:
            # Fallback to original logic if not found in manifest
            if base == "zero2hero":
                # Load the zero2hero template from directive file
                zero2hero_path = (
                    get_project_root() / "directives" / "base" / "zero2hero.md"
                )

                if zero2hero_path.exists():
                    try:
                        with open(zero2hero_path, "r", encoding="utf-8") as f:
                            zero2hero_content = f.read().strip()
                            # Replace {subject} placeholder with actual subject
                            zero2hero_content = zero2hero_content.replace(
                                "{subject}", subject
                            )
                            parts.append(zero2hero_content)
                    except Exception:
                        # Fallback to hardcoded content if file reading fails
                        parts.append(
                            "Goal: pedagogical manual from foundations to practice with steady depth; no early wrap-ups."
                        )
                else:
                    # Fallback to hardcoded content if file doesn't exist
                    parts.append(
                        "Goal: pedagogical manual from foundations to practice with steady depth; no early wrap-ups."
                    )
            elif base == "reference":
                ref_path = get_project_root() / "directives" / "base" / "reference.md"
                if ref_path.exists():
                    try:
                        parts.append(ref_path.read_text(encoding="utf-8").strip())
                    except Exception:
                        parts.append(
                            "Goal: tight reference handbook; definitions first; terse, unambiguous rules and examples."
                        )
                else:
                    parts.append(
                        "Goal: tight reference handbook; definitions first; terse, unambiguous rules and examples."
                    )
            elif base == "pop":
                pop_path = get_project_root() / "directives" / "base" / "pop.md"
                if pop_path.exists():
                    try:
                        parts.append(pop_path.read_text(encoding="utf-8").strip())
                    except Exception:
                        parts.append(
                            "Goal: accessible, accurate narrative explainer with vignettes; keep rigor without academic padding."
                        )
                else:
                    parts.append(
                        "Goal: accessible, accurate narrative explainer with vignettes; keep rigor without academic padding."
                    )
            elif base == "nobs":
                nobs_path = get_project_root() / "directives" / "base" / "nobs.md"
                if nobs_path.exists():
                    try:
                        parts.append(nobs_path.read_text(encoding="utf-8").strip())
                    except Exception:
                        parts.append(
                            "Goal: no‑bullshit manual; only what changes decisions or understanding; tight prose."
                        )
                else:
                    parts.append(
                        "Goal: no‑bullshit manual; only what changes decisions or understanding; tight prose."
                    )

        # Apply overlays
        for overlay_key in overlays:
            overlay_text = self.OVERLAYS.get(overlay_key, "")
            if overlay_text:
                parts.append(overlay_text)

        # Add continuation rules
        parts.append(
            "Continuation: continue exactly from anchor; do not restart sections; do not summarize prematurely. "
            "If nearing length limit, stop cleanly with: NEXT: [Continue]."
        )

        # Add extra notes if provided
        if extra_notes and extra_notes.strip():
            parts.append(extra_notes.strip())

        # Add domain-specific notes
        if "law" in subject.lower() or "policy" in subject.lower():
            parts.append("This is educational, not legal advice.")

        system_text = "\n".join(parts)

        # Track what was applied
        applied = {
            "subject": subject,
            "base": base,
            "overlays": overlays,
            "extra_notes": extra_notes,
            "continuation": {
                "mode": "anchor",
                "min_chars": min_chars,
                "passes": passes,
                "max_chunks": max_chunks,
                "repeat_warn": True,
            },
        }

        return PromptComposition(
            system_text=system_text, applied=applied, warnings=warnings
        )

    def lint(self, subject: str, base: str, overlays: List[str]) -> List[str]:
        """Perform basic linting on prompt composition parameters."""
        warnings = []

        # Check for subject length
        if len(subject.strip()) < 3:
            warnings.append(
                "Subject is very short (< 3 chars), consider being more specific"
            )

        # Check for common overlay conflicts
        if "narrative" in overlays and "compressed" in overlays:
            warnings.append(
                "Using both 'narrative' and 'compressed' overlays may create conflicting styles"
            )

        # Check base mode appropriateness for subject
        if "law" in subject.lower() and base == "pop":
            warnings.append(
                "For legal subjects, 'reference' or 'nobs' base modes might be more appropriate than 'pop'"
            )

        return warnings


# Global instance for convenience
pcl = PromptCompositionLayer()


def compose_prompt(
    subject: str,
    base: str = "zero2hero",
    overlays: Optional[List[str]] = None,
    extra_notes: Optional[str] = None,
    min_chars: int = 4200,
    passes: int = 1,
    max_chunks: int = 12,
    outline_first: bool = False,  # New parameter for outline-first functionality
    apply_reading_overlay: bool = False,  # New parameter to control reading overlay
) -> PromptComposition:
    """Convenience function to compose a prompt using the global PCL instance."""
    # Always call pcl.compose directly
    result = pcl.compose(
        subject=subject,
        base=base,
        overlays=overlays,
        extra_notes=extra_notes,
        min_chars=min_chars,
        passes=passes,
        max_chunks=max_chunks,
    )

    # If outline_first is enabled, modify the system text to include outline-first instructions
    if outline_first:
        outline_instruction = (
            "\n\nOUTLINE-FIRST SCAFFOLD\n"
            "- First chunk: produce a chapter-by-chapter outline consistent with the subject; end with NEXT: [Begin Chapter 1].\n"
            "- Subsequent chunks: follow the outline; narrative prose; define terms once; no bullet walls."
        )
        result.system_text += outline_instruction
        # Update applied metadata to reflect the outline-first mode
        if "outline_first" not in result.applied:
            result.applied["outline_first"] = True

    # If reading overlay is enabled, add the reading overlay instruction
    if apply_reading_overlay:
        reading_instruction = (
            "\n\nDOMAIN-AWARE FURTHER READING\n"
            "- At the end of major sections, include a 'Further Reading' box with 2-3 curated references.\n"
            "- Use domain-specific resources from data/resource_map.en.json if available.\n"
            "- Format: 'Further Reading: [Resource 1]; [Resource 2]; [Resource 3]'\n"
        )
        result.system_text += reading_instruction
        # Update applied metadata to reflect the reading overlay
        result.applied["reading_overlay"] = True

    return result
