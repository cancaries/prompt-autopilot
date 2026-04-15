"""
prompt-autopilot - Auto-optimize prompts, evaluate quality, learn preferences.
"""

__version__ = "1.0.0"

from .core import (
    analyze_instruction,
    generate_optimized_versions,
    evaluate_version,
    optimize,
    record_feedback,
    load_preferences,
    save_template,
    list_templates,
    search_templates,
)
from .display import display_result, DisplayStyle

__all__ = [
    "analyze_instruction",
    "generate_optimized_versions",
    "evaluate_version",
    "optimize",
    "record_feedback",
    "load_preferences",
    "save_template",
    "list_templates",
    "search_templates",
    "display_result",
    "DisplayStyle",
]
