"""
Simple profiles functionality for XSArena.
"""


def load_profiles():
    """
    Returns a dictionary of predefined profiles.
    """
    return {
        "narrative": {"overlays": ["narrative", "no_bs"], "extra": ""},
        "compressed": {
            "overlays": ["compressed", "no_bs"],
            "extra": "Dense narrative; avoid bullets.",
        },
        "pop": {"overlays": ["pop"], "extra": "Accessible; rigor without padding."},
        "reference": {
            "overlays": ["nobs"],
            "extra": "Terse, factual; definitions first.",
        },
    }
