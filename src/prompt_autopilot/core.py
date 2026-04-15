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
    instruction_type: str  # code, writing, explanation, question, etc.
    language: str  # zh, en, or mixed

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

def detect_language(text: str) -> str:
    """Detect if instruction is primarily Chinese, English, or mixed."""
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_words = len([w for w in text.split() if w.isascii()])
    
    if chinese_chars > english_words * 1.5:
        return "zh"
    elif english_words > chinese_chars * 1.5:
        return "en"
    return "mixed"

def detect_instruction_type(instruction: str) -> str:
    """Detect what type of instruction this is."""
    instruction_lower = instruction.lower()
    
    # Code-related
    code_keywords = [
        "code", "function", "script", "implement", "debug", "fix", "refactor",
        "api", "database", "sql", "python", "javascript", "java", "golang", "rust",
        "写代码", "函数", "调试", "算法", "排序", "缓存", "队列", "栈",
        "实现", "编程", "代码", "class", "method", "module",
        "lr", "cache", "queue", "stack", "hash", "tree", "graph"
    ]
    if any(word in instruction_lower for word in code_keywords):
        return "code"
    
    # Writing
    if any(word in instruction_lower for word in ["write", "compose", "draft", "email", "letter", "article", "blog", "写", "文章", "邮件", "文案"]):
        return "writing"
    
    # Explanation
    if any(word in instruction_lower for word in ["explain", "what", "how", "why", "difference", "解释", "说明", "什么是", "为什么"]):
        return "explanation"
    
    # Question
    if instruction.strip().endswith("?") or "吗" in instruction or "?" in instruction:
        return "question"
    
    # Data processing
    if any(word in instruction_lower for word in ["process", "analyze", "data", "csv", "json", "parse", "处理", "分析", "数据"]):
        return "data"
    
    return "general"

def analyze_instruction(instruction: str) -> AnalysisResult:
    """
    Analyze a raw instruction for missing information, ambiguity, etc.
    """
    instruction_lower = instruction.lower()
    words = instruction_lower.split()
    lang = detect_language(instruction)
    instr_type = detect_instruction_type(instruction)
    
    missing = []
    assumptions = []
    risks = []
    
    # Very short instruction
    if len(words) < 5:
        missing.append("Very brief - may lack necessary context")
    
    # No output format
    format_indicators = ["format", "output", "return", "give", "show", "list", "explain", "write", "生成", "输出", "返回", "解释", "写"]
    if not any(word in instruction_lower for word in format_indicators):
        missing.append("No output format specified")
    
    # No constraints
    constraint_words = ["must", "should", "only", "don't", "avoid", "limit", "exactly", "under", "必须", "应该", "不要", "避免", "限制"]
    if not any(word in instruction_lower for word in constraint_words):
        missing.append("No constraints or limitations stated")
    
    # No audience (only for non-code tasks)
    audience_words = ["for", "audience", "beginner", "expert", "technical", "someone", "who", "给", "面向", "受众"]
    if instr_type != "code" and not any(word in instruction_lower for word in audience_words):
        missing.append("Target audience not specified")
    
    # Language/tool specific (code tasks)
    if instr_type == "code":
        tech_langs = ["python", "javascript", "typescript", "java", "go", "rust", "sql", "bash", "c++", "ruby", "php", "python", "js", "ts", "代码", "语言"]
        if not any(word in instruction_lower for word in tech_langs):
            assumptions.append("No programming language specified")
        
        if "function" in instruction_lower or "函数" in instruction_lower:
            if "input" not in instruction_lower and "参数" not in instruction_lower:
                missing.append("No input/parameter specification")
            if "output" not in instruction_lower and "返回" not in instruction_lower:
                missing.append("No output specification")
    
    # Writing tasks
    if instr_type == "writing":
        writing_elements = ["收件人", "收件", "语气", "正式", "口语", "长度", "字数", "recipient", "tone", "length", "formal", "casual"]
        if not any(word in instruction_lower for word in writing_elements):
            missing.append("No writing style/length specified")
    
    # Question tasks
    if instr_type == "question":
        if len(words) < 10:
            missing.append("Question too brief - may get generic answer")
        if "level" not in instruction_lower and "程度" not in instruction_lower:
            assumptions.append("Assumed general knowledge level")
    
    # Data tasks
    if instr_type == "data":
        if "input" not in instruction_lower and "format" not in instruction_lower:
            missing.append("No input data format specified")
    
    # Risks
    if "?" in instruction and len(words) < 15:
        risks.append("Question without context - may get generic answers")
    
    if instruction.endswith("..."):
        risks.append("Incomplete instruction - may be cut off")
    
    return {
        "missing": missing,
        "assumptions": assumptions,
        "risks": risks,
        "word_count": len(words),
        "instruction_type": instr_type,
        "language": lang,
    }

# =============================================================================
# Smart Version Generation
# =============================================================================

def generate_context_fillers(analysis: AnalysisResult, instruction: str) -> dict:
    """Generate specific context fillers based on analysis."""
    instr_type = analysis["instruction_type"]
    lang = analysis["language"]
    missing = analysis["missing"]
    
    fillers = {}
    
    if lang == "zh":
        if instr_type == "code":
            fillers = {
                "input_spec": "输入格式：JSON / 列表 / 字典等",
                "output_spec": "输出格式：返回值类型和内容",
                "error_handling": "错误处理：异常情况如何处理",
                "example": "示例：输入 → 输出",
            }
        elif instr_type == "writing":
            fillers = {
                "recipient": "谁？（同事/客户/朋友）",
                "reason": "发生了什么？",
                "relationship": "亲密/一般/正式",
                "tone": "真诚/正式/轻松",
                "length": "多少字？",
            }
        elif instr_type == "explanation":
            fillers = {
                "audience": "谁？（初学者/学生/专业人士）",
                "level": "小白/有基础/专家",
                "depth": "简单概念/详细解释/技术细节",
                "format": "口语/书面/带例子",
            }
        else:
            fillers = {
                "context": "背景：什么场景？",
                "constraints": "约束：有哪些限制？",
                "goal": "目标：想达到什么效果？",
            }
    else:  # English or mixed
        if instr_type == "code":
            fillers = {
                "input_spec": "Input format: JSON / list / dict / etc.",
                "output_spec": "Output: return type and content",
                "error_handling": "Error handling: how to handle exceptions",
                "example": "Example: input → output",
            }
        elif instr_type == "writing":
            fillers = {
                "recipient": "Recipient: who? (colleague/client/friend)",
                "reason": "Reason: what happened?",
                "relationship": "Relationship: close/casual/formal",
                "tone": "Tone: sincere/formal/casual",
                "length": "Length: how many words?",
            }
        elif instr_type == "explanation":
            fillers = {
                "audience": "who? (beginner/student/expert)",
                "level": "basic/intermediate/advanced",
                "depth": "concept/explanation/technical",
                "format": "spoken/written/with examples",
            }
        else:
            fillers = {
                "context": "Context: what setting?",
                "constraints": "Constraints: any limitations?",
                "goal": "Goal: what to achieve?",
            }
    
    return fillers

def generate_optimized_versions(instruction: str, count: int = 3) -> list[VersionResult]:
    """
    Generate 3 optimized versions with context-aware placeholders.
    """
    # First analyze to understand the instruction
    analysis = analyze_instruction(instruction)
    fillers = generate_context_fillers(analysis, instruction)
    instr_type = analysis["instruction_type"]
    lang = analysis["language"]
    stripped = instruction.strip()
    
    versions = []
    
    # Version A: Concise (minimal but useful)
    if lang == "zh":
        version_a = f"""{stripped}

要求：
- 语言简洁，不要废话
- 直接给出结果"""
    else:
        version_a = f"""{stripped}

Requirements:
- Be concise and direct
- No preamble, just the answer"""
    
    versions.append({
        "type": "A (Concise)",
        "description": "Direct, minimal context, no fluff",
        "template": version_a,
    })
    
    # Version B: Detailed (context-aware)
    if instr_type == "code":
        if lang == "zh":
            version_b = f"""任务：{stripped}

输入规范：
{fillers.get('input_spec', '[输入格式]')}

输出规范：
{fillers.get('output_spec', '[输出格式]')}

约束条件：
- {fillers.get('error_handling', '[错误处理方式]')}
- 运行效率要求（如有）

示例：
{fillers.get('example', '[输入 → 输出 示例]')}"""
        else:
            version_b = f"""Task: {stripped}

Input Specification:
{fillers.get('input_spec', '[Input format]')}

Output Specification:
{fillers.get('output_spec', '[Output format]')}

Constraints:
- {fillers.get('error_handling', '[Error handling]')}
- Performance requirements (if any)

Example:
{fillers.get('example', '[input → output example]')}"""
    elif instr_type == "writing":
        if lang == "zh":
            version_b = f"""任务：{stripped}

背景信息：
- {fillers.get('recipient', '[收件人]')}
- {fillers.get('reason', '[道歉原因]')}
- {fillers.get('relationship', '[关系]')}

写作要求：
- 语气：{fillers.get('tone', '[真诚/正式/轻松]')}
- 长度：{fillers.get('length', '[字数要求]')}
- 格式：邮件/私信/正式信函

预期输出：
完整通顺的文本内容"""
        else:
            version_b = f"""Task: {stripped}

Context:
- {fillers.get('recipient', '[Recipient]')}
- {fillers.get('reason', '[Reason]')}
- {fillers.get('relationship', '[Relationship]')}

Requirements:
- Tone: {fillers.get('tone', '[sincere/formal/casual]')}
- Length: {fillers.get('length', '[word count]')}
- Format: {fillers.get('format', '[email/message/formal letter]')}

Expected Output:
Complete, well-written text"""
    elif instr_type == "explanation":
        if lang == "zh":
            version_b = f"""任务：{stripped}

受众信息：
- {fillers.get('audience', '[目标读者]')}
- {fillers.get('level', '[知识水平]')}

解释要求：
- 深度：{fillers.get('depth', '[简单/详细/技术]')}
- 格式：{fillers.get('format', '[口语/书面/带例子]')}
- 是否需要图示或代码示例？

预期输出：
清晰易懂的解释内容"""
        else:
            version_b = f"""Task: {stripped}

Audience:
- {fillers.get('audience', '[Target reader]')}
- {fillers.get('level', '[Knowledge level]')}

Requirements:
- Depth: {fillers.get('depth', '[simple/detailed/technical]')}
- Format: {fillers.get('format', '[oral/written/with examples]')}
- Include diagrams or code examples if helpful?

Expected Output:
Clear and understandable explanation"""
    else:
        if lang == "zh":
            version_b = f"""任务：{stripped}

背景：
{fillers.get('context', '[背景信息]')}

约束：
{fillers.get('constraints', '[限制条件]')}

目标：
{fillers.get('goal', '[预期结果]')}

请按要求完成。"""
        else:
            version_b = f"""Task: {stripped}

Context:
{fillers.get('context', '[Background]')}

Constraints:
{fillers.get('constraints', '[Limitations]')}

Goal:
{fillers.get('goal', '[Expected outcome]')}

Please complete as requested."""
    
    versions.append({
        "type": "B (Detailed)",
        "description": "Full context, specific placeholders, clear constraints",
        "template": version_b,
    })
    
    # Version C: Structured (step-by-step)
    if instr_type == "code":
        if lang == "zh":
            version_c = f"""## 任务
{stripped}

## 输入
{fillers.get('input_spec', '[输入数据]')}

## 输出  
{fillers.get('output_spec', '[输出数据]')}

## 约束
- {fillers.get('error_handling', '[错误处理]')}
- 时间/空间复杂度（如有要求）

## 实现步骤
1. [步骤1]
2. [步骤2]
3. [步骤3]

## 验收标准
- [标准1]
- [标准2]"""
        else:
            version_c = f"""## Task
{stripped}

## Input
{fillers.get('input_spec', '[Input data]')}

## Output
{fillers.get('output_spec', '[Output data]')}

## Constraints
- {fillers.get('error_handling', '[Error handling]')}
- Time/space complexity (if required)

## Implementation Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Acceptance Criteria
- [Criterion 1]
- [Criterion 2]"""
    elif instr_type == "writing":
        if lang == "zh":
            version_c = f"""## 写作任务
{stripped}

## 基本信息
- 收件人：{fillers.get('recipient', '[谁]')}
- 场合：{fillers.get('context', '[什么场景]')}

## 风格要求
- 语气：{fillers.get('tone', '[语气]')}
- 长度：{fillers.get('length', '[字数]')}
- 格式：{fillers.get('format', '[格式]')}

## 内容要点
1. [要点1]
2. [要点2]
3. [要点3]

## 结尾
- [如何收尾]"""
        else:
            version_c = f"""## Writing Task
{stripped}

## Basic Info
- Recipient: {fillers.get('recipient', '[who]')}
- Occasion: {fillers.get('context', '[what occasion]')}

## Style
- Tone: {fillers.get('tone', '[tone]')}
- Length: {fillers.get('length', '[length]')}
- Format: {fillers.get('format', '[format]')}

## Key Points
1. [Point 1]
2. [Point 2]
3. [Point 3]

## Closing
- [How to end]"""
    else:
        if lang == "zh":
            version_c = f"""## 任务
{stripped}

## 背景
{fillers.get('context', '[背景信息]')}

## 约束条件
- {fillers.get('constraints', '[限制]')}

## 执行步骤
1. [第一步]
2. [第二步]
3. [第三步]

## 交付标准
- [标准1]
- [标准2]"""
        else:
            version_c = f"""## Task
{stripped}

## Background
{fillers.get('context', '[Background]')}

## Constraints
- {fillers.get('constraints', '[Constraints]')}

## Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Deliverables
- [Criterion 1]
- [Criterion 2]"""
    
    versions.append({
        "type": "C (Structured)",
        "description": "Step-by-step, numbered, clear I/O",
        "template": version_c,
    })
    
    return versions[:count]

# =============================================================================
# Evaluation
# =============================================================================

def evaluate_version(version_text: str, analysis: AnalysisResult) -> EvaluationResult:
    """
    Evaluate a version on whether it properly addresses the instruction's gaps.
    
    Scoring measures: Does the template help fill in missing information?
    A well-structured template addressing gaps should score well even for brief instructions.
    """
    word_count = len(version_text.split())
    text_lower = version_text.lower()
    missing = analysis.get("missing", [])
    
    # === CLARITY: Template structure and appropriate length ===
    # Well-structured templates (numbered steps, clear sections) get higher scores
    has_sections = text_lower.count("## ") > 0
    has_numbered = text_lower.count("1.") > 0 or text_lower.count("1)") > 0
    has_bullets = text_lower.count("- ") > 0 or text_lower.count("• ") > 0
    
    clarity = 5  # Base score
    if has_sections:
        clarity += 1
    if has_numbered:
        clarity += 1
    if has_bullets:
        clarity += 0.5
    
    # Template length should be appropriate (not too short)
    if word_count < 50:
        clarity -= 1
    elif word_count > 200:
        clarity += 0.5
    
    # === SPECIFICITY: Template prompts for specific information ===
    # Does the template ask for concrete details about the missing elements?
    specificity_prompts = [
        "who", "what", "when", "where", "why", "how",
        "input", "output", "format", "example",
        "audience", "tone", "length", "style",
        "constraint", "limit", "requirement",
        "收件人", "语气", "长度", "受众", "背景", "原因"
    ]
    prompt_count = sum(1 for p in specificity_prompts if p in text_lower)
    
    # Penalize templates with too many generic placeholders
    generic_ph = text_lower.count("[") + text_lower.count("]")
    placeholder_ratio = generic_ph / max(word_count, 1)
    
    specificity = 4 + min(prompt_count * 0.5, 3)  # Base 4, max 7
    specificity -= placeholder_ratio * 2  # Penalize dense placeholder use
    specificity = max(3, min(8, specificity))
    
    # === COMPLETENESS: Addresses the detected missing elements ===
    # Does the template explicitly ask about what the analysis flagged as missing?
    if not missing:
        completeness = 7  # No missing = good
    else:
        addressed = 0
        for m in missing:
            # Check if template has prompts/questions about this missing element
            m_words = [w.lower() for w in m.split() if len(w) > 3]
            for w in m_words:
                if w in text_lower:
                    addressed += 0.5
                    break
        
        # Completeness = how well template prompts for the missing info
        completeness = 3 + min(addressed, len(missing)) * 1.0  # Base 3, max 8
        completeness = max(3, min(8, completeness))
    
    # === Calculate overall ===
    overall = clarity * 0.30 + specificity * 0.35 + completeness * 0.35
    
    # Grade thresholds - moderate
    if overall >= 7.5:
        grade = "A"
    elif overall >= 6:
        grade = "B"
    elif overall >= 4.5:
        grade = "C"
    elif overall >= 3:
        grade = "D"
    else:
        grade = "F"
    
    return {
        "scores": {
            "clarity": round(clarity, 1),
            "specificity": round(specificity, 1),
            "completeness": round(completeness, 1),
        },
        "overall": round(overall, 1),
        "grade": grade,
    }

def recommend_version(evaluations: list[EvaluationResult], analysis: AnalysisResult) -> int:
    """
    Recommend the best version based on evaluations and instruction type.
    """
    # First pick the highest scored
    best_idx = 0
    best_score = 0
    
    for i, eval_result in enumerate(evaluations):
        if eval_result["overall"] > best_score:
            best_score = eval_result["overall"]
            best_idx = i
    
    # Adjust based on instruction type
    # Code tasks -> prefer structured (C) if within 0.5
    # Writing -> ALWAYS prefer detailed (B), structured is wrong format for prose
    # Questions/Explanation -> prefer detailed (B) if within 1.0
    instr_type = analysis.get("instruction_type", "general")
    
    if instr_type == "code" and evaluations[2]["overall"] >= evaluations[best_idx]["overall"] - 0.5:
        best_idx = 2  # Structured for code
    elif instr_type == "writing":
        # Writing tasks should ALWAYS use detailed format (B)
        # Structured format is completely wrong for blog posts, emails, articles
        best_idx = 1  # Detailed for writing
    elif instr_type == "explanation" and evaluations[1]["overall"] >= evaluations[best_idx]["overall"] - 1.0:
        best_idx = 1  # Detailed for explanation
    
    return best_idx

# =============================================================================
# Main Pipeline
# =============================================================================

def optimize(instruction: str) -> OptimizationResult:
    """
    Main optimization pipeline.
    """
    # Step 1: Analyze
    analysis = analyze_instruction(instruction)
    
    # Step 2: Generate versions (with smart context)
    versions = generate_optimized_versions(instruction)
    
    # Step 3: Evaluate each
    evaluations = [evaluate_version(v["template"], analysis) for v in versions]
    
    # Step 4: Recommend (considering instruction type)
    recommended_idx = recommend_version(evaluations, analysis)
    
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
    """
    prefs = load_preferences()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "instruction": instruction[:100],
        "chosen_version": ["A", "B", "C"][chosen_idx],
        "feedback": feedback,
        "improvement": improvement,
    }
    
    prefs["feedback_history"].append(entry)
    
    # Extract patterns from feedback
    if improvement:
        imp_lower = improvement.lower()
        if any(word in imp_lower for word in ["concise", "shorter", "brief", "简洁"]):
            prefs["format_preference"] = "concise"
        elif any(word in imp_lower for word in ["detail", "more", "explain", "详细"]):
            prefs["format_preference"] = "detailed"
        elif any(word in imp_lower for word in ["step", "structur", "结构"]):
            prefs["format_preference"] = "structured"
    
    save_preferences(prefs)
    return prefs

# =============================================================================
# Template Management
# =============================================================================

TemplateData = dict

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
