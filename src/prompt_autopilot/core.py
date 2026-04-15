"""
Core optimization logic for prompt-autopilot.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, TypedDict

# Storage paths
AUTOPILOT_DIR = Path.home() / ".prompt-autopilot"
PREFERENCES_FILE = AUTOPILOT_DIR / "preferences.json"
TEMPLATES_DIR = AUTOPILOT_DIR / "templates"
HISTORY_DIR = AUTOPILOT_DIR / "history"

# Initialize directories
AUTOPILOT_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
HISTORY_DIR.mkdir(exist_ok=True)

DEFAULT_PREFERENCES = {
    "format_preference": "detailed",
    "tone_preference": "concise",
    "common_missing": [],
    "feedback_history": [],
    "version_count": 3,
    "auto_analyze": True,
    "show_scores": True,
    "auto_apply": False,
}

# =============================================================================
# Types
# =============================================================================

class AnalysisResult(TypedDict):
    missing: list[str]
    assumptions: list[str]
    risks: list[str]
    word_count: int

class VersionResult(TypedDict):
    type: str
    description: str
    template: str

class EvaluationResult(TypedDict):
    scores: dict[str, int]
    overall: float
    grade: str

class OptimizationResult(TypedDict):
    original: str
    analysis: AnalysisResult
    versions: list[VersionResult]
    evaluations: list[EvaluationResult]
    recommended_idx: int
    recommended_version: VersionResult
    recommended_evaluation: EvaluationResult

# =============================================================================
# Preferences
# =============================================================================

def load_preferences() -> dict:
    """Load user preferences from file."""
    if PREFERENCES_FILE.exists():
        with open(PREFERENCES_FILE, "r") as f:
            return {**DEFAULT_PREFERENCES, **json.load(f)}
    return DEFAULT_PREFERENCES.copy()

def save_preferences(prefs: dict):
    """Save user preferences to file."""
    with open(PREFERENCES_FILE, "w") as f:
        json.dump(prefs, f, indent=2)

# =============================================================================
# Analysis
# =============================================================================

def analyze_instruction(instruction: str) -> AnalysisResult:
    """
    Analyze a raw instruction for missing information, ambiguity, etc.
    
    Identifies:
    - Missing context or constraints
    - Unstated assumptions
    - Potential failure modes
    """
    instruction_lower = instruction.lower()
    words = instruction_lower.split()
    
    missing = []
    assumptions = []
    risks = []
    
    # Very short instruction
    if len(words) < 5:
        missing.append("Very brief - may lack necessary context")
    
    # No output format
    format_indicators = ["format", "output", "return", "give", "show", "list", "explain", "write"]
    if not any(word in instruction_lower for word in format_indicators):
        missing.append("No output format specified")
    
    # No constraints
    constraint_words = ["must", "should", "only", "don't", "avoid", "limit", "exactly", "under"]
    if not any(word in instruction_lower for word in constraint_words):
        missing.append("No constraints or limitations stated")
    
    # No audience
    audience_words = ["for", "audience", "beginner", "expert", "technical", "someone", "who"]
    if not any(word in instruction_lower for word in audience_words):
        missing.append("Target audience not specified")
    
    # No language/tool specified for technical tasks
    if any(word in instruction_lower for word in ["code", "function", "script", "api", "database"]):
        tech_lang = ["python", "javascript", "typescript", "java", "go", "rust", "sql", "bash"]
        if not any(word in instruction_lower for word in tech_lang):
            assumptions.append("No language/framework specified")
    
    # Question without context
    if "?" in instruction and len(words) < 15:
        risks.append("Question without context - may get generic answers")
    
    # Incomplete instruction
    if instruction.endswith("..."):
        risks.append("Incomplete instruction - may be cut off")
    
    # Assumptions about task type
    if "fix" in instruction_lower or "debug" in instruction_lower:
        assumptions.append("No specific error message or location provided")
    
    return {
        "missing": missing,
        "assumptions": assumptions,
        "risks": risks,
        "word_count": len(words),
    }

# =============================================================================
# Version Generation
# =============================================================================

def generate_optimized_versions(instruction: str, count: int = 3) -> list[VersionResult]:
    """
    Generate 3 optimized versions of the instruction:
    - A: Concise (direct, minimal)
    - B: Detailed (full context, examples)
    - C: Structured (step-by-step, numbered)
    """
    stripped = instruction.strip()
    
    versions: list[VersionResult] = []
    
    # Version A: Concise
    versions.append({
        "type": "A (Concise)",
        "description": "Direct, minimal context, no fluff",
        "template": f"""{stripped}

Requirements:
- Be direct and concise
- No preamble or explanation
- Output only what's asked"""
    })
    
    # Version B: Detailed
    versions.append({
        "type": "B (Detailed)",
        "description": "Full context, examples, clear constraints",
        "template": f"""Task: {stripped}

Context:
[Explain the background or situation]

Requirements:
- [Specific requirement 1]
- [Specific requirement 2]
- [Format specification if needed]

Examples:
- [Example 1] → [Expected output]
- [Example 2] → [Expected output]

Expected Output:
[Describe what success looks like]"""
    })
    
    # Version C: Structured
    versions.append({
        "type": "C (Structured)",
        "description": "Step-by-step, numbered, clear I/O",
        "template": f"""## Task
{stripped}

## Input
[What I will provide]

## Constraints
- [Limitation 1]
- [Limitation 2]

## Output Format
```[json/yaml/markdown/code]
[Format specification]
```

## Success Criteria
- [Criterion 1]
- [Criterion 2]"""
    })
    
    return versions[:count]

# =============================================================================
# Evaluation
# =============================================================================

def evaluate_version(version_text: str, analysis: AnalysisResult) -> EvaluationResult:
    """
    Evaluate a version on clarity, specificity, and completeness.
    Scores 1-10 for each dimension.
    """
    word_count = len(version_text.split())
    text_lower = version_text.lower()
    
    # Clarity: appropriate length, clear structure
    if word_count < 10:
        clarity = 5  # Too brief
    elif word_count < 30:
        clarity = 7
    elif word_count < 80:
        clarity = 9  # Good balance
    elif word_count < 150:
        clarity = 8
    else:
        clarity = 7  # Getting verbose
    
    # Specificity: has concrete requirements
    specificity_keywords = [
        "specific", "exactly", "must", "should", "format", "example",
        "json", "list", "step", "constraint", "limitation"
    ]
    specificity = min(10, 4 + sum(1 for kw in specificity_keywords if kw in text_lower) * 1.5)
    
    # Completeness: addresses missing elements from analysis
    missing = analysis.get("missing", [])
    if not missing:
        completeness = 9
    else:
        addressed = 0
        for m in missing:
            m_words = m.lower().split()
            # Check if any significant word from missing item appears in version
            if any(w in text_lower for w in m_words if len(w) > 4):
                addressed += 1
        completeness = min(10, int(10 * addressed / len(missing)) if missing else 10)
    
    # Calculate overall
    overall = (clarity + specificity + completeness) / 3
    
    # Determine grade
    if overall >= 8.5:
        grade = "A"
    elif overall >= 7:
        grade = "B"
    elif overall >= 5:
        grade = "C"
    else:
        grade = "D"
    
    return {
        "scores": {
            "clarity": clarity,
            "specificity": specificity,
            "completeness": completeness,
        },
        "overall": round(overall, 1),
        "grade": grade,
    }

def recommend_version(evaluations: list[EvaluationResult]) -> int:
    """Return index of best version based on evaluations."""
    best_idx = 0
    best_score = 0
    
    for i, eval_result in enumerate(evaluations):
        if eval_result["overall"] > best_score:
            best_score = eval_result["overall"]
            best_idx = i
    
    return best_idx

# =============================================================================
# Main Pipeline
# =============================================================================

def optimize(instruction: str) -> OptimizationResult:
    """
    Main optimization pipeline.
    
    Args:
        instruction: The raw instruction to optimize
    
    Returns:
        OptimizationResult with all versions, evaluations, and recommendation
    """
    # Step 1: Analyze
    analysis = analyze_instruction(instruction)
    
    # Step 2: Generate versions
    versions = generate_optimized_versions(instruction)
    
    # Step 3: Evaluate each
    evaluations = [evaluate_version(v["template"], analysis) for v in versions]
    
    # Step 4: Recommend
    recommended_idx = recommend_version(evaluations)
    
    return {
        "original": instruction,
        "analysis": analysis,
        "versions": versions,
        "evaluations": evaluations,
        "recommended_idx": recommended_idx,
        "recommended_version": versions[recommended_idx],
        "recommended_evaluation": evaluations[recommended_idx],
    }

# =============================================================================
# Feedback & Learning
# =============================================================================

def record_feedback(
    instruction: str,
    chosen_idx: int,
    feedback: Optional[str] = None,
    improvement: Optional[str] = None,
) -> dict:
    """
    Record user feedback to improve future recommendations.
    
    Args:
        instruction: Original instruction
        chosen_idx: Which version was chosen (0=A, 1=B, 2=C)
        feedback: Free-text feedback
        improvement: What could be improved
    
    Returns:
        Updated preferences
    """
    prefs = load_preferences()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "instruction": instruction[:100],  # Truncate long instructions
        "chosen_version": ["A", "B", "C"][chosen_idx],
        "feedback": feedback,
        "improvement": improvement,
    }
    
    prefs["feedback_history"].append(entry)
    
    # Extract patterns from feedback
    if improvement:
        imp_lower = improvement.lower()
        if "concise" in imp_lower or "shorter" in imp_lower or "brief" in imp_lower:
            prefs["format_preference"] = "concise"
        elif "detail" in imp_lower or "more" in imp_lower or "explain" in imp_lower:
            prefs["format_preference"] = "detailed"
        elif "step" in imp_lower or "structur" in imp_lower:
            prefs["format_preference"] = "structured"
    
    # Extract commonly missing elements
    analysis = analyze_instruction(instruction)
    for m in analysis.get("missing", []):
        m_key = m.split()[0]  # First significant word
        if m_key not in prefs.get("common_missing", []):
            prefs.setdefault("common_missing", []).append(m_key)
    
    save_preferences(prefs)
    return prefs

# =============================================================================
# Template Management
# =============================================================================

TemplateData = dict  # Simplified for now

def save_template(
    name: str,
    prompt: str,
    tags: Optional[list[str]] = None,
    description: Optional[str] = None,
) -> TemplateData:
    """Save a prompt as reusable template."""
    template = {
        "name": name,
        "prompt": prompt,
        "tags": tags or [],
        "description": description or "",
        "created": datetime.now().isoformat(),
        "use_count": 0,
    }
    
    safe_name = name.lower().replace(" ", "-")
    filepath = TEMPLATES_DIR / f"{safe_name}.json"
    
    with open(filepath, "w") as f:
        json.dump(template, f, indent=2)
    
    return template

def list_templates() -> list[TemplateData]:
    """List all saved templates."""
    templates = []
    for filepath in TEMPLATES_DIR.glob("*.json"):
        with open(filepath, "r") as f:
            templates.append(json.load(f))
    return sorted(templates, key=lambda t: t.get("use_count", 0), reverse=True)

def search_templates(query: str) -> list[TemplateData]:
    """Search templates by name, tag, or prompt content."""
    query_lower = query.lower()
    all_templates = list_templates()
    
    results = []
    for t in all_templates:
        if (query_lower in t.get("name", "").lower() or
            query_lower in t.get("prompt", "").lower() or
            any(query_lower in tag.lower() for tag in t.get("tags", []))):
            results.append(t)
    
    return results

def get_template(name: str) -> Optional[TemplateData]:
    """Get a template by name."""
    safe_name = name.lower().replace(" ", "-")
    filepath = TEMPLATES_DIR / f"{safe_name}.json"
    
    if filepath.exists():
        with open(filepath, "r") as f:
            return json.load(f)
    return None

def increment_template_usage(name: str):
    """Increment usage count for a template."""
    template = get_template(name)
    if template:
        template["use_count"] = template.get("use_count", 0) + 1
        safe_name = name.lower().replace(" ", "-")
        filepath = TEMPLATES_DIR / f"{safe_name}.json"
        with open(filepath, "w") as f:
            json.dump(template, f, indent=2)
