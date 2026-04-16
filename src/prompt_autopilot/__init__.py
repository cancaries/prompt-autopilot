"""
prompt-autopilot - Auto-optimize prompts, evaluate quality, learn preferences.
"""

__version__ = "1.0.0"

from .core import (
    analyze_instruction,
    generate_optimized_versions,
    generate_optimized_prompt,
    evaluate_version,
    optimize,
    optimize_with_llm,
    generate_with_llm,
    record_feedback,
    load_preferences,
    load_config,
    save_config,
    save_template,
    list_templates,
    search_templates,
    get_llm_tier,
    get_llm_config,
    LLM_TIERS,
)
from .library import (
    save_prompt,
    load_prompt,
    list_prompts,
    search_prompts,
    delete_prompt,
    use_prompt,
    find_similar,
    update_prompt,
)
from .display import display_result, DisplayStyle

__all__ = [
    "analyze_instruction",
    "generate_optimized_versions",
    "generate_optimized_prompt",
    "evaluate_version",
    "optimize",
    "optimize_with_llm",
    "generate_with_llm",
    "record_feedback",
    "load_preferences",
    "load_config",
    "save_config",
    "save_template",
    "list_templates",
    "search_templates",
    "save_prompt",
    "load_prompt",
    "list_prompts",
    "search_prompts",
    "delete_prompt",
    "use_prompt",
    "find_similar",
    "update_prompt",
    "display_result",
    "DisplayStyle",
    "get_llm_tier",
    "get_llm_config",
    "LLM_TIERS",
]
