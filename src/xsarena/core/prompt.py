"""Prompt Composition Layer (PCL) - Centralized prompt composition with schema and lints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


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
        """Load richer templates from various sources."""
        # Try to load from core templates first
        try:
            from .templates import COMPRESSED_OVERLAY, NARRATIVE_OVERLAY, NO_BS_ADDENDUM

            if NARRATIVE_OVERLAY:
                self.OVERLAYS["narrative"] = NARRATIVE_OVERLAY.strip()
            if COMPRESSED_OVERLAY:
                self.OVERLAYS["compressed"] = COMPRESSED_OVERLAY.strip()
            if NO_BS_ADDENDUM:
                self.OVERLAYS["no_bs"] = NO_BS_ADDENDUM.strip()
        except ImportError:
            pass

        # Try legacy templates as fallback
        try:
            import lma_templates as legacy

            if hasattr(legacy, "NARRATIVE_OVERLAY") and legacy.NARRATIVE_OVERLAY:
                self.OVERLAYS["narrative"] = legacy.NARRATIVE_OVERLAY.strip()
            if hasattr(legacy, "COMPRESSED_OVERLAY") and legacy.COMPRESSED_OVERLAY:
                self.OVERLAYS["compressed"] = legacy.COMPRESSED_OVERLAY.strip()
            if hasattr(legacy, "NO_BS_ADDENDUM") and legacy.NO_BS_ADDENDUM:
                self.OVERLAYS["no_bs"] = legacy.NO_BS_ADDENDUM.strip()
        except ImportError:
            pass

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

        # Base intent
        if base == "zero2hero":
            parts.append(
                "Goal: pedagogical manual from foundations to practice with steady depth; no early wrap-ups."
            )
        elif base == "reference":
            parts.append(
                "Goal: tight reference handbook; definitions first; terse, unambiguous rules and examples."
            )
        elif base == "pop":
            parts.append(
                "Goal: accessible, accurate narrative explainer with vignettes; keep rigor without academic padding."
            )
        elif base == "nobs":
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
) -> PromptComposition:
    """Convenience function to compose a prompt using the global PCL instance."""
    return pcl.compose(
        subject=subject,
        base=base,
        overlays=overlays,
        extra_notes=extra_notes,
        min_chars=min_chars,
        passes=passes,
        max_chunks=max_chunks,
    )
