"""
Core optimization logic for prompt-autopilot v2.

Philosophy: All steps are LLM-powered. Different tiers for different complexity.

⚡ Fast LLM (simple instructions)
   - Model: MiniMax / GPT-3.5-turbo
   - Concise prompt, 1-2s response

🧠 Deep LLM (complex instructions)
   - Model: GPT-4 / Claude
   - Detailed prompt, 5-10s response
"""

import json
import os
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, TypedDict

# Storage paths
AUTOPILOT_DIR = Path.home() / ".prompt-autopilot"
CONFIG_FILE = AUTOPILOT_DIR / "config.json"
PREFERENCES_FILE = AUTOPILOT_DIR / "preferences.json"
TEMPLATES_DIR = AUTOPILOT_DIR / "templates"
HISTORY_DIR = AUTOPILOT_DIR / "history"

AUTOPILOT_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
HISTORY_DIR.mkdir(exist_ok=True)

DEFAULT_PREFERENCES = {
    "format_preference": "concise",
    "tone_preference": "casual",
    "common_missing": [],
    "feedback_history": [],
    "auto_apply": False,
}

# =============================================================================
# LLM Tier System - All steps are LLM-powered
# =============================================================================

LLM_TIERS = {
    "fast": {
        "model": "gpt-3.5-turbo",
        "timeout": 5,
        "prompt_style": "concise",
    },
    "deep": {
        "model": "gpt-4",
        "timeout": 30,
        "prompt_style": "detailed",
    }
}


def _count_chinese_chars(text: str) -> int:
    """Count Chinese characters in text."""
    return sum(1 for c in text if '\u4e00' <= c <= '\u9fff')


def get_llm_tier(instruction: str) -> str:
    """
    Auto-select LLM tier based on instruction complexity.
    
    For English: uses word count (split by whitespace)
    For Chinese: uses character count (Chinese has no spaces)
    
    Rules:
    - < 10 words / < 20 Chinese chars → fast
    - < 30 words / < 60 Chinese chars → medium
    - >= 30 words / >= 60 Chinese chars → deep
    """
    chinese_chars = _count_chinese_chars(instruction)
    total_chars = len(instruction)
    
    # Primarily Chinese text - use character count
    if chinese_chars > total_chars * 0.5:
        if chinese_chars < 20:
            return "fast"
        elif chinese_chars < 60:
            return "medium"
        else:
            return "deep"
    
    # English or mixed - use word count
    words = len(instruction.split())
    if words < 10:
        return "fast"
    elif words < 30:
        return "medium"
    else:
        return "deep"


def get_llm_config() -> dict:
    """Get LLM config with priority: env vars > config file > defaults.
    
    Environment variables:
    - PROMPT_AUTOPILOT_API_KEY: LLM API key
    - PROMPT_AUTOPILOT_MODEL: Default model name (default: gpt-4)
    - PROMPT_AUTOPILOT_ENDPOINT: API endpoint URL
    - PROMPT_AUTOPILOT_FAST_MODEL: Fast tier model (default: gpt-3.5-turbo)
    - PROMPT_AUTOPILOT_DEEP_MODEL: Deep tier model (default: gpt-4)
    """
    cfg = {}
    # Load from config file as base
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
    # Environment variables override (highest priority)
    if os.environ.get("PROMPT_AUTOPILOT_API_KEY"):
        cfg["llm_api_key"] = os.environ["PROMPT_AUTOPILOT_API_KEY"]
    if os.environ.get("PROMPT_AUTOPILOT_MODEL"):
        cfg["llm_model"] = os.environ["PROMPT_AUTOPILOT_MODEL"]
    if os.environ.get("PROMPT_AUTOPILOT_ENDPOINT"):
        cfg["llm_endpoint"] = os.environ["PROMPT_AUTOPILOT_ENDPOINT"]
    if os.environ.get("PROMPT_AUTOPILOT_FAST_MODEL"):
        cfg["fast_model"] = os.environ["PROMPT_AUTOPILOT_FAST_MODEL"]
    if os.environ.get("PROMPT_AUTOPILOT_DEEP_MODEL"):
        cfg["deep_model"] = os.environ["PROMPT_AUTOPILOT_DEEP_MODEL"]
    # Ensure defaults
    cfg.setdefault("llm_api_key", None)
    cfg.setdefault("llm_model", "gpt-4")
    cfg.setdefault("llm_endpoint", "https://api.openai.com/v1/chat/completions")
    cfg.setdefault("fast_model", "gpt-3.5-turbo")
    cfg.setdefault("deep_model", "gpt-4")
    cfg.setdefault("default_tier", "auto")
    return cfg


def call_llm(prompt: str, tier: str = "deep", system: str = None) -> Optional[str]:
    """
    Unified LLM call with tier-specific model selection.
    
    Args:
        prompt: User prompt content
        tier: "fast" or "deep" (model selection based on this)
        system: Optional system prompt override
    """
    cfg = get_llm_config()
    api_key = cfg.get("llm_api_key")
    if not api_key:
        return None

    # Select model based on tier
    if tier == "fast":
        model = cfg.get("fast_model", "gpt-3.5-turbo")
        timeout = LLM_TIERS["fast"]["timeout"]
    else:
        model = cfg.get("deep_model", "gpt-4")
        timeout = LLM_TIERS["deep"]["timeout"]

    endpoint = cfg.get("llm_endpoint", "https://api.openai.com/v1/chat/completions")
    default_system = "你是一个专业的 prompt 工程专家，擅长将模糊的用户需求转化为完整、精确的 prompt。你的工作哲学：不要问用户问题，直接推理并填充合理的默认值；宁可多做，不要少做；深度推理比规则匹配好 100 倍。"
    
    try:
        response = requests.post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system or default_system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


# =============================================================================
# LLM-Enhanced Analysis & Generation Prompts (by tier)
# =============================================================================

# Fast tier prompts (concise, for simple instructions)
FAST_ANALYSIS_PROMPT = '''分析以下用户指令，简短输出 JSON：
{{"type": "任务类型", "missing": ["缺失要素"], "assumptions": ["假设"], "complexity": "simple/medium/complex"}}

指令：{instruction}

直接输出 JSON，不要解释。'''

FAST_GENERATION_PROMPT = '''用户想要：{instruction}

生成优化后的完整 prompt，包含：
- 任务描述
- 约束条件
- 质量标准

直接输出 prompt 文本，不要解释。'''

# Deep tier prompts (detailed, for complex instructions)
DEEP_ANALYSIS_PROMPT = '''你是 prompt 工程专家。深度分析以下用户指令：

{instruction}

请输出 JSON：
{{
  "type": "任务类型（code/writing/explanation/general等）",
  "missing": ["用户没说明但需要补充的要素"],
  "assumptions": ["你做的合理假设"],
  "risks": ["潜在风险或问题"],
  "complexity": "simple/medium/complex",
  "language": "zh/en/mixed",
  "word_count": 词数
}}

要求：
- 深度推理，挖掘用户真正想要的是什么
- 假设要有道理，不要过度假设
- complexity: simple=5句话内完成, medium=需要一些结构, complex=需要完整模板

直接输出 JSON。'''

DEEP_GENERATION_PROMPT = '''你是一个 prompt 工程专家。用户想要：

{instruction}

请深度思考并生成优化后的 prompt：

1. 【意图理解】用户真正想要的是什么？不是字面，而是背后目的。

2. 【盲点发现】用户没想到但很重要的东西有哪些？

3. 【优化后的 prompt】生成一个完整的、专业的 prompt，包含：
   - 清晰的任务描述（用一句话描述你要 AI 做什么）
   - 具体的约束条件（输入/输出/性能/安全等）
   - 相关的背景信息（项目背景、使用场景、目标用户）
   - 质量标准（什么样的结果算好）
   - 边界情况（如何处理异常）

4. 【before/after】给出优化前后的对比

直接输出优化后的 prompt 和对比，用自然段落组织，不要分点列举。'''

# Medium tier - uses fast model but with deep analysis prompt
MEDIUM_ANALYSIS_PROMPT = DEEP_ANALYSIS_PROMPT
MEDIUM_GENERATION_PROMPT = DEEP_GENERATION_PROMPT  # Use deep prompts even for medium


# =============================================================================
# Types
# =============================================================================

class AnalysisResult(TypedDict):
    missing: list[str]
    assumptions: list[str]
    risks: list[str]
    word_count: int
    instruction_type: str
    language: str
    task_complexity: str  # simple, medium, complex

class VersionResult(TypedDict):
    type: str
    description: str
    template: str
    is_direct: bool
    applicable_techniques: str
    examples: str

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
    llm_tier: str  # which tier was used

# =============================================================================
# Preferences
# =============================================================================

def load_config() -> dict:
    """Load LLM configuration (legacy, wraps get_llm_config)."""
    return get_llm_config()

def save_config(cfg: dict):
    """Save LLM configuration."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def load_preferences() -> dict:
    if PREFERENCES_FILE.exists():
        with open(PREFERENCES_FILE, "r") as f:
            return {**DEFAULT_PREFERENCES, **json.load(f)}
    return DEFAULT_PREFERENCES.copy()

def save_preferences(prefs: dict):
    with open(PREFERENCES_FILE, "w") as f:
        json.dump(prefs, f, indent=2)

# =============================================================================
# Analysis - All LLM-powered with tier selection
# =============================================================================

def detect_language(text: str) -> str:
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_words = len([w for w in text.split() if w.isascii()])
    if chinese_chars > english_words * 1.5:
        return "zh"
    elif english_words > chinese_chars * 1.5:
        return "en"
    return "mixed"


def _strip_emoji(text: str) -> str:
    """Remove emoji characters before classification."""
    import re
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", text)


def _extract_core_concept(instruction: str) -> str:
    """Extract the core concept from an explanation-style instruction.
    
    Examples:
    - "解释机器学习" -> "机器学习"
    - "给初级工程师解释什么是闭包" -> "闭包"
    - "教我理解什么是闭包" -> "闭包"
    - "什么是HTTP协议" -> "HTTP协议"
    - "讲讲Python的特点" -> "Python"
    - "explain how blockchain works" -> "blockchain"
    - "what is machine learning" -> "machine learning"
    """
    text = instruction.strip()
    
    # First, check if instruction starts with "什么是" pattern (e.g., "什么是量子纠缠")
    if text.startswith("什么是"):
        return text[3:].strip()
    
    # Check for "X是什么意思" pattern
    if "是什么意思" in text:
        idx = text.find("是什么意思")
        return text[:idx].strip()
    
    # Strip common explanation prefixes
    strip_prefixes = [
        "给初级工程师解释什么是", "给工程师解释什么是", "给程序员解释什么是",
        "给小白解释什么是", "解释什么是", "解释一下什么是", "解释一下",
        "介绍一下", "通俗地介绍", "用通俗语言介绍", "深入讲解", "讲解一下",
        "普及一下", "告诉你有关", "讲讲", "告诉我有关", "说说什么是", "说一说",
        # Additional prefixes for common patterns
        "解释", "讲解", "介绍", "说明", "教我理解", "帮我理解",
        "让我了解", "让我们了解", "请解释", "请讲解", "请介绍",
    ]
    for prefix in strip_prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    
    # Strip common suffixes
    strip_suffixes = [
        "的定义", "的定义、原理", "的定义、原理、应用", "的原理",
        "的原理和应用", "的概念", "的相关知识", "的一切", "的特点",
        "的工作原理", "是如何工作的", "是如何实现的",
    ]
    for suffix in strip_suffixes:
        if text.endswith(suffix):
            text = text[:-len(suffix)]
            break
    
    # If we extracted something meaningful from Chinese patterns, return it
    # (But don't return early for English - we need to check English patterns first)
    original_text = instruction.strip()
    if text.strip() and text.strip() != original_text:
        return text.strip()
    
    # Handle English patterns BEFORE returning original text
    text_lower = text.lower()
    
    # Pattern: "explain how X works" -> extract X
    if text_lower.startswith("explain how "):
        rest = text[12:]  # "explain how " is 12 chars
        if " works" in rest:
            return rest[:rest.find(" works")].strip()
        return rest.strip()
    
    # Pattern: "what is X" / "what are X" -> extract X
    if text_lower.startswith("what is "):
        rest = text[8:]  # "what is " is 8 chars
        # Remove trailing question mark or other punctuation
        rest = rest.rstrip('?').strip()
        return rest
    if text_lower.startswith("what are "):
        rest = text[9:]  # "what are " is 9 chars
        rest = rest.rstrip('?').strip()
        return rest
    
    # Pattern: "tell me about X" / "explain X" -> extract X
    if text_lower.startswith("tell me about "):
        return text[14:].strip()  # "tell me about " is 14 chars
    if text_lower.startswith("explain "):
        rest = text[7:].strip()  # "explain " is 7 chars
        # If followed by "what is" or "how", strip that
        if rest.lower().startswith("what is "):
            rest = rest[8:]
        if rest.lower().startswith("how "):
            parts = rest.split(" how ", 1)
            if len(parts) > 1:
                rest = parts[1]
                if rest.startswith("is ") or rest.startswith("are "):
                    rest = rest[3:]
        return rest.rstrip('?').strip()
    
    return instruction


def detect_instruction_type(instruction: str) -> str:
    """Rule-based type detection as fallback when LLM unavailable."""
    text = _strip_emoji(instruction)
    text_lower = text.lower()
    
    code_review_keywords = [
        "review", "review代码", "代码review", "cr", "代码审查", "代码分析",
        "性能review", "review这段", "代码审查", "review一下", "review下"
    ]
    if any(word in text_lower for word in code_review_keywords):
        return "code_review"
    
    test_generation_keywords = [
        "单元测试", "unit test", "测试用例", "写测试", "test case",
        "pytest", "jest", "testing", "测试代码"
    ]
    if any(word in text_lower for word in test_generation_keywords):
        return "test_generation"
    
    code_keywords = [
        "code", "function", "script", "implement", "debug", "fix", "refactor",
        "api", "database", "sql", "python", "javascript", "java", "golang", "rust",
        "写代码", "函数", "调试", "算法", "排序", "缓存", "队列", "栈",
        "实现", "编程", "代码", "class", "method", "module",
        "lr", "cache", "queue", "stack", "hash", "tree", "graph",
        "登录", "注册", "用户", "验证", "auth", "login", "register",
        "斐波那契", "fibonacci", "quicksort", "mergesort",
        "脚本", "代码脚本", "游戏脚本", "程序脚本",
    ]
    # Check explanation BEFORE code, because single words like "api", "python" 
    # might appear in explanation contexts (e.g., "什么是RESTful API")
    if any(word in text_lower for word in [
        "explain", "what", "how", "why", "difference", "解释", "说明", "是什么", "什么是", "为什么", "介绍",
        "理解", "懂得", "搞清楚", "弄明白",
    ]):
        return "explanation"
    
    if any(word in text_lower for word in code_keywords):
        return "code"
    
    if any(w in text_lower for w in ["拒绝", "谢绝", "无法录用", "面试结果", "不录用"]):
        return "rejection_email"
    if any(w in text_lower for w in ["道歉", "sorry", "apologize", "致歉"]):
        return "apology_email"
    if any(w in text_lower for w in ["周报", "月报", "日报", "进度汇报", "项目报告"]):
        return "report_email"
    if any(w in text_lower for w in ["通知", "notification", "告知", "通报"]):
        return "notification_email"
    if any(w in text_lower for w in ["投诉", "complaint", "客户投诉", "申诉"]):
        return "complaint_email"
    
    creative_writing_keywords = [
        "小说", "fiction", "story", "开头", "科幻", "奇幻", "悬疑",
        "散文", "poetry", "poem", "短篇", "长篇", "故事", "narrative",
        "脚本", "scenario", "剧本", "台词", "dialogue"
    ]
    if any(w in text_lower for w in creative_writing_keywords):
        return "creative_writing"
    
    academic_writing_keywords = [
        "文献综述", "摘要", "abstract", "论文", "学术", "研究", "研究论文",
        "dissertation", "thesis", "学术论文", "sci", "期刊文章",
        "literature review", "research paper"
    ]
    if any(w in text_lower for w in academic_writing_keywords):
        return "academic_writing"
    
    writing_keywords = [
        "write", "compose", "draft", "email", "letter", "article", "blog",
        "写", "文章", "邮件", "文案", "汇报", "报告", "总结"
    ]
    if any(word in text_lower for word in writing_keywords):
        return "writing"
    
    if "?" in text or "吗" in text or "？" in text:
        return "question"
    
    return "general"


def analyze_instruction(instruction: str, tier: str = None) -> AnalysisResult:
    """
    Analyze instruction using LLM (with tier selection).
    Falls back to rule-based if LLM unavailable.
    
    Args:
        instruction: The user instruction to analyze
        tier: "auto" (default), "fast", "medium", "deep"
            - auto: selects tier based on instruction complexity
            - fast: use fast model (gpt-3.5-turbo)
            - medium: use fast model with detailed prompt
            - deep: use deep model (gpt-4) with detailed prompt
    """
    # Auto-select tier if not specified
    if tier is None or tier == "auto":
        tier = get_llm_tier(instruction)
    
    # Map medium to fast (we use fast model but enhanced prompt)
    effective_tier = "fast" if tier == "medium" else tier
    
    # Select appropriate prompt based on tier
    if effective_tier == "fast":
        prompt_template = FAST_ANALYSIS_PROMPT
    else:
        prompt_template = DEEP_ANALYSIS_PROMPT
    
    # Try LLM-based analysis
    llm_result = call_llm(
        prompt_template.format(instruction=instruction),
        tier=effective_tier
    )
    
    if llm_result:
        try:
            # Try to parse JSON from LLM response
            import re
            json_match = re.search(r'\{[^{}]*\}', llm_result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return AnalysisResult(
                    missing=data.get("missing", []),
                    assumptions=data.get("assumptions", []),
                    risks=data.get("risks", []),
                    word_count=data.get("word_count", len(instruction.split())),
                    instruction_type=data.get("type", detect_instruction_type(instruction)),
                    language=data.get("language", detect_language(instruction)),
                    task_complexity=data.get("complexity", "medium"),
                )
        except (json.JSONDecodeError, KeyError):
            pass  # Fall through to rule-based
    
    # Fallback to rule-based analysis when LLM unavailable
    return _rule_based_analysis(instruction)


def _rule_based_analysis(instruction: str) -> AnalysisResult:
    """Rule-based analysis fallback when LLM unavailable."""
    instruction_lower = instruction.lower()
    words = instruction_lower.split()
    lang = detect_language(instruction)
    instr_type = detect_instruction_type(instruction)
    
    # Compute effective word count: use Chinese char count for Chinese text
    # (English word split gives meaningful count; Chinese split() gives 1 for entire string)
    chinese_chars = _count_chinese_chars(instruction)
    if lang == "zh" and chinese_chars > 0:
        # For Chinese: use char count as "word count" proxy
        effective_word_count = chinese_chars
    else:
        effective_word_count = len(words)
    
    # Determine complexity based on length and type
    if effective_word_count <= 10 and instr_type in ["code", "writing", "explanation"]:
        complexity = "simple"
    elif any(phrase in instruction for phrase in ["具体", "详细", "一步步", "step by step", "详细说明"]):
        complexity = "complex"
    elif effective_word_count <= 20:
        complexity = "simple"
    else:
        complexity = "medium"
    
    missing = []
    assumptions = []
    risks = []
    
    if complexity == "simple":
        if instr_type == "code":
            if "python" not in instruction_lower and "js" not in instruction_lower:
                assumptions.append("Language not specified")
        return AnalysisResult(
            missing=missing,
            assumptions=assumptions,
            risks=risks,
            word_count=effective_word_count,
            instruction_type=instr_type,
            language=lang,
            task_complexity=complexity,
        )
    
    if effective_word_count < 10:
        missing.append("Context too brief")
    
    if instr_type == "code":
        if not any(l in instruction_lower for l in ["python", "javascript", "java", "sql", "api"]):
            missing.append("Language/framework not specified")
    
    if instr_type == "writing":
        if not any(w in instruction_lower for w in ["收件", "recipient", "对象"]):
            assumptions.append("Audience not specified")
    
    return AnalysisResult(
        missing=missing,
        assumptions=assumptions,
        risks=risks,
        word_count=effective_word_count,
        instruction_type=instr_type,
        language=lang,
        task_complexity=complexity,
    )


# =============================================================================
# Fallback Prompt Templates (no LLM required, preserved for simple cases)
# =============================================================================

# Code task inference map
_CODE_DEFAULTS = {
    ("json", "数组", "list"): {
        "lang": "Python",
        "input": "JSON 数组或 Python 列表",
        "output": "数值（平均值）",
        "constraints": "时间复杂度 O(n)，空间复杂度 O(1)",
        "boundary": "空数组应返回 None（因为平均值对空集无定义），调用方需自行处理空数组输入",
    },
    ("平方", "square", "幂", "power"): {
        "lang": "Python",
        "input": "数值或列表",
        "output": "数值或列表（平方）",
        "constraints": "时间复杂度 O(n)",
        "boundary": "负数平方、正负数混合列表",
    },
    ("排序", "sort"): {
        "lang": "Python",
        "input": "整数数组，长度 1-100000，元素范围 0-10^9",
        "output": "升序排列的整数数组",
        "constraints": "平均时间复杂度 O(n log n)，空间复杂度 O(log n)",
        "boundary": "空数组返回空数组",
    },
    ("二分", "binary search"): {
        "lang": "Python",
        "input": "有序整数数组 + 目标值",
        "output": "目标值的下标（不存在返回 -1）",
        "constraints": "时间复杂度 O(log n)",
        "boundary": "数组为空、目标不存在、单元素数组",
    },
    ("斐波那契", "fibonacci", "dp", "动态规划"): {
        "lang": "Python",
        "input": "整数 n（0 ≤ n ≤ 1000）",
        "output": "第 n 个斐波那契数",
        "constraints": "时间复杂度 O(n)，空间复杂度 O(1)",
        "boundary": "n=0, n=1, n 特别大",
    },
    ("登录", "login", "登陆", "auth"): {
        "lang": "Python + Flask",
        "input": "用户名（字符串）+ 密码（字符串）",
        "output": "成功返回 JWT token，失败返回错误信息",
        "constraints": "密码需 bcrypt 哈希存储，JWT 有效期 24h",
        "boundary": "用户不存在、密码错误、账号锁定",
    },
    ("api", "接口", "endpoint", "rest"): {
        "lang": "Python + Flask / FastAPI",
        "input": "HTTP 请求参数（JSON/query/path）",
        "output": "JSON 响应 {code, message, data}",
        "constraints": "RESTful 规范，状态码正确，参数校验",
        "boundary": "参数缺失、格式错误、未授权访问",
    },
    # Issue #1 fix: Add missing entries for LRU cache, game scripts, and data processing
    ("lru", "cache", "缓存"): {
        "lang": "Python",
        "input": "整数 key（任意类型）+ 任意类型 value",
        "output": "按 LRU 策略存储和返回 value，超容量时淘汰最久未使用的条目",
        "constraints": "时间复杂度 O(1) 的 get 和 put 操作",
        "boundary": "容量为 0、key 不存在、重复插入同一 key",
    },
    ("游戏", "game", "脚本", "script"): {
        "lang": "Python + Pygame / 终端游戏",
        "input": "用户输入（键盘/鼠标/命令行）",
        "output": "游戏画面更新或文本输出",
        "constraints": "流畅运行，无明显卡顿",
        "boundary": "非法输入、游戏结束条件、暂停/恢复",
    },
    ("function", "函数", "method", "方法"): {
        "lang": "Python",
        "input": "函数参数（类型和含义由调用方指定）",
        "output": "函数返回值（类型和含义由调用方指定）",
        "constraints": "代码清晰，注释完善",
        "boundary": "非法输入类型、空输入、边界值",
    },
    ("user", "data", "数据", "用户"): {
        "lang": "Python",
        "input": "用户数据对象（字典/JSON/数据库记录）",
        "output": "处理后的数据（视任务目标而定）",
        "constraints": "数据验证，异常处理",
        "boundary": "空数据、格式错误、缺失字段",
    },
}


def _infer_code_defaults(instruction: str) -> dict | None:
    """Try to find a matching default spec for the instruction."""
    instruction_lower = instruction.lower()
    for keywords, spec in _CODE_DEFAULTS.items():
        if any(kw in instruction_lower for kw in keywords):
            return spec
    return None


def _extract_info(instruction: str, instruction_type: str = None) -> dict:
    """Extract useful info from instruction for template filling."""
    info = {
        "topic": None,
        "depth": "扫盲科普",
        "style": "通俗易懂",
        "audience": "一般读者",
        "format": "文章",
        "language": "中文",
        "analogy": "用生活中的例子说明",
        "tone": "通俗易懂，适合科普",
    }
    inst_stripped = _strip_emoji(instruction)
    inst_lower = inst_stripped.lower()

    # P1-B fix: detect language properly using detect_language(), not hardcoded "中文"
    detected_lang = detect_language(instruction)
    if detected_lang == "en":
        info["language"] = "英文"
    elif detected_lang == "mixed":
        info["language"] = "中英双语"
    # else: keep "中文" default

    topic_keywords = {
        "AI": "AI（人工智能）", "人工智能": "AI（人工智能）",
        "区块链": "区块链", "比特币": "区块链",
        "Python": "Python", "Java": "Java", "Go": "Go",
        "机器学习": "机器学习", "深度学习": "深度学习",
        "大模型": "大模型", "LLM": "大语言模型",
        "云计算": "云计算", "边缘计算": "边缘计算",
        "物联网": "物联网", "5G": "5G",
        "网络安全": "网络安全", "黑客": "网络安全",
        "量子计算": "量子计算", "量子": "量子计算",
    }
    for kw, label in topic_keywords.items():
        if kw in inst_lower or kw in inst_stripped:
            info["topic"] = label
            break
    if info["topic"] is None:
        words = inst_stripped.split()
        info["topic"] = " ".join(words[:5]) if len(words) > 3 else inst_stripped
        if not info["topic"] or info["topic"].strip(" ，、.") == "":
            info["topic"] = "该主题"

    if any(w in inst_lower for w in ["专业", "深入", "高级", "源码", "原理"]):
        info["depth"] = "深入专业"
        info["style"] = "专业严谨"
    if any(w in inst_lower for w in ["通俗", "入门", "扫盲", "科普", "小白"]):
        info["depth"] = "扫盲科普"
        info["style"] = "通俗易懂"
    if any(w in inst_lower for w in ["生活中的例子", "生活例子", "日常", "实例"]):
        info["analogy"] = "用生活中的例子说明"
        info["style"] = "通俗易懂，有生活气息"

    if any(w in inst_lower for w in ["工程师", "developer", "程序员", "技术", "码农"]):
        info["audience"] = "技术人员/工程师"
    elif any(w in inst_lower for w in ["老板", "管理层", "manager", "高管"]):
        info["audience"] = "管理层/决策者"
    elif any(w in inst_lower for w in ["客户"]):
        info["audience"] = "客户"
    elif any(w in inst_lower for w in ["学生", "小白", "入门"]):
        info["audience"] = "初学者/学生"
    else:
        # P2 fix: use smarter audience extraction instead of embedding full instruction
        # For creative_writing, check genre FIRST (before _extract_core_concept)
        if instruction_type == "creative_writing":
            genre_audiences = {
                "科幻": "科幻小说读者", "奇幻": "奇幻文学读者",
                "悬疑": "悬疑小说爱好者", "推理": "推理小说爱好者",
                "爱情": "爱情小说读者", "武侠": "武侠小说爱好者",
                "短篇": "短篇小说读者", "长篇": "长篇小说读者",
                "散文": "散文爱好者", "诗歌": "诗歌爱好者",
                "剧本": "戏剧/影视从业者",
            }
            for kw, aud in genre_audiences.items():
                if kw in inst_lower:
                    info["audience"] = aud
                    break
            else:
                # No genre keyword found, try _extract_core_concept
                core = _extract_core_concept(instruction)
                if core and core != instruction.strip() and len(core) < len(instruction.strip()):
                    info["audience"] = f"{core}爱好者"
                else:
                    info["audience"] = f"一般读者，对{info['topic']}有基本了解"
        else:
            core = _extract_core_concept(instruction)
            if core and core != instruction.strip() and len(core) < len(instruction.strip()):
                if instruction_type == "academic_writing":
                    info["audience"] = f"{core}领域的研究人员"
                elif instruction_type == "writing":
                    info["audience"] = f"一般读者，对{core}有兴趣"
                else:
                    info["audience"] = f"一般读者，对{core}有基本了解"
            else:
                info["audience"] = f"一般读者，对{info['topic']}有基本了解"

    if any(w in inst_lower for w in ["博客", "文章", "帖子", "公众号"]):
        info["format"] = "博客文章"
    elif any(w in inst_lower for w in ["邮件", "email", "邮件"]):
        info["format"] = "邮件"
    elif any(w in inst_lower for w in ["报告", "分析"]):
        info["format"] = "分析报告"
    elif any(w in inst_lower for w in ["PPT", "演示", "演讲"]):
        info["format"] = "演示文稿"

    if any(w in inst_stripped for w in ["英文", "English", "用英语", "write in english"]):
        info["language"] = "英文"

    # Combine tone descriptors instead of using if/elif (fixes P4: "专业" + "友善" → "专业友善")
    tone_parts = []
    if "专业" in inst_lower:
        tone_parts.append("专业")
    if "正式" in inst_lower:
        tone_parts.append("正式")
    if "轻松" in inst_lower:
        tone_parts.append("轻松")
    if "活泼" in inst_lower:
        tone_parts.append("活泼")
    if "亲切" in inst_lower:
        tone_parts.append("亲切")
    if "友善" in inst_lower:
        tone_parts.append("友善")
    if "通俗" in inst_lower:
        tone_parts.append("通俗易懂")
    if "科普" in inst_lower:
        tone_parts.append("适合科普")
    if "小白" in inst_lower:
        tone_parts.append("适合小白")
    if tone_parts:
        info["tone"] = "".join(tone_parts)
    elif "通俗" in inst_lower or "科普" in inst_lower or "小白" in inst_lower:
        info["tone"] = "通俗易懂，适合科普"

    return info


def generate_fallback_prompt(instruction: str, instruction_type: str) -> str:
    """
    Fallback template-based prompt generation (no LLM).
    Used only when API key is not configured.
    """
    stripped = instruction.strip()
    lang = detect_language(instruction)
    
    # Minimal prompt handling - if instruction is too short or too vague, return helpful message
    # But allow known explanation patterns even if short
    explanation_patterns = [
        "解释", "讲解", "介绍", "什么是", "是什么", "说明",
        "explain", "what is", "what are", "how does", "tell me about",
    ]
    is_explanation_pattern = any(stripped.startswith(p) or stripped.lower().startswith(p.lower()) 
                                  for p in explanation_patterns)
    
    if len(stripped) < 8 and not is_explanation_pattern:
        return f"""## ⚠️ 指令信息不足

您的指令「{stripped}」太简略，无法生成有针对性的优化 prompt。

### 💡 请补充更多信息

建议包括：
- **任务目标**：想要实现什么？
- **具体场景**：在什么情况下使用？
- **技术要求**：有什么特殊约束吗？

### 📝 示例

| 简短 ❌ | 详细 ✅ |
|--------|--------|
| AI | 帮我写一篇关于AI发展趋势的博客 |
| 做好这个功能 | 用Python实现用户登录功能，支持JWT认证 |
| 写代码 | 用Python写一个快速排序算法 |

### 🔧 优化后的 prompt 将包含
- 清晰的任务描述
- 具体的输入/输出规格
- 边界情况处理
- 质量标准"""

    if instruction_type == "code_review":
        return f"""## 🎯 任务
审查以下代码：{stripped}

## 🔍 待审查代码
[请提供代码，或描述代码所在模块/功能]

## 🔎 审查维度
- **正确性**：逻辑是否正确，边界情况是否处理
- **性能**：时间/空间复杂度，是否有优化空间
- **安全性**：是否有安全漏洞（注入、XSS、敏感信息泄露等）
- **可读性**：命名、注释、结构是否清晰
- **最佳实践**：是否符合语言/框架的推荐写法

## ✅ 审查输出
- 发现的问题列表（按严重程度：高/中/低）
- 改进建议
- 优化后的参考代码（如适用）"""

    if instruction_type == "test_generation":
        return f"""## 🎯 任务
为以下代码编写单元测试：{stripped}

## 🔍 待测代码
[从上下文中推断或描述]

## 📋 测试要求
- 测试框架：[如 pytest, unittest, Jest]
- 覆盖要求：[正常用例 + 边界用例 + 异常用例]
- Mock 使用：[如需要]

## ✅ 验收标准
- 所有测试通过
- 覆盖核心逻辑路径"""

    if instruction_type == "code":
        defaults = _infer_code_defaults(stripped)
        if defaults:
            lang_default = defaults['lang']
            perf = defaults.get('constraints', '时间复杂度：O(n)\n- 空间复杂度：O(1)')
            boundary = defaults.get('boundary', '请补充边界情况处理')
            
            is_sorting = any(kw in stripped.lower() for kw in ('排序', 'sort', 'quicksort', 'mergesort'))
            if is_sorting:
                return f"""## 🎯 任务
用 {lang_default} 实现快速排序算法

## 📥 输入
- 类型：整数数组
- 范围：长度 1-100000，元素 0-10^9
- 示例：[3, 6, 8, 10, 1, 2, 1]

## 📤 输出
- 类型：整数数组（升序）
- 示例：[1, 1, 2, 3, 6, 8, 10]

## ⚡ 性能要求
- 时间复杂度：O(n log n)（平均），O(n²)（最坏）
- 空间复杂度：O(log n)

## 🛡️ 边界情况
- 空数组 → 返回 []
- 单元素 → 返回 [x]
- 重复元素 → 保持相对顺序"""
            
            is_login = any(kw in stripped.lower() for kw in ('登录', 'login', '登陆', 'auth'))
            if is_login:
                return f"""## 🎯 任务
用 {lang_default} 实现用户认证系统，支持登录

## 📥 输入
- 用户名（字符串，3-20 字符）
- 密码（字符串，8-32 字符，明文输入）

## 📤 输出
- 成功：返回 JWT token（有效期 24 小时）
- 失败：返回明确错误信息

## ⚡ 性能要求
- 密码验证：bcrypt 哈希（每条密码验证 < 100ms）
- JWT 签发：< 10ms

## 🛡️ 边界情况
- 用户不存在 → 返回明确错误信息
- 密码错误 → 提示「密码错误」，不暴露具体原因
- 账号锁定 → 锁定后需等待 30 分钟"""

            # Generic code fallback
            instr_lower = stripped.lower()
            specific_reqs = []
            if any(w in instr_lower for w in ['平均', 'average', 'mean']):
                specific_reqs.append('计算平均值')
            if any(w in instr_lower for w in ['求和', 'sum', '合计']):
                specific_reqs.append('计算总和')
            if any(w in instr_lower for w in ['最大', 'max', '最小', 'min']):
                specific_reqs.append('找最大/最小值')
            if any(w in instr_lower for w in ['去重', 'unique', 'distinct']):
                specific_reqs.append('去重处理')
            if any(w in instr_lower for w in ['排序', 'sort', '升序', '降序']):
                specific_reqs.append('排序处理')
            
            # Only use default output if user explicitly mentioned an operation
            # Otherwise, generate a description based on what user actually asked for
            if specific_reqs:
                output_desc = ' + '.join(specific_reqs)
            elif any(w in instr_lower for w in ['json']):
                # User mentioned JSON but not the operation - generic JSON processing
                output_desc = '根据处理需求确定（如转换、提取、验证等）'
            else:
                output_desc = '根据任务目标确定'
            
            # Issue #6 fix: if both input and output are generic placeholders,
            # the instruction is too vague - return "指令信息不足" warning
            input_desc = defaults.get('input', '由调用方提供')
            # Generic input patterns - contain "由调用方", "具体输入", "类型和数据范围", etc.
            GENERIC_INPUT_PATTERNS = [
                '由调用方提供', '由调用方指定',
                '类型和数据范围（根据任务描述推断）',
                '具体输入示例', '具体输入',
                'Input type and format (inferred from task)',
                'Concrete input example',
                '函数参数（类型和含义由调用方指定）',
                '函数参数（',  # generic function parameter description
            ]
            # Generic output patterns - contain "根据任务目标", "任务目标", "对应输出", etc.
            GENERIC_OUTPUT_PATTERNS = [
                '根据任务目标确定', '任务目标的处理结果',
                '对应输出示例', '根据处理需求确定',
                'Expected output based on task goal',
                'Corresponding output example',
                '函数返回值（类型和含义由调用方指定）',
                '函数返回值（',  # generic function return description
            ]
            is_input_generic = any(p in input_desc for p in GENERIC_INPUT_PATTERNS)
            is_output_generic = any(p in output_desc for p in GENERIC_OUTPUT_PATTERNS)
            if is_input_generic and is_output_generic:
                if lang == 'zh':
                    return f"""## ⚠️ 指令信息不足

您的指令「{stripped}」信息不足，无法生成有针对性的优化 prompt。

### 💡 请补充更多信息

建议包括：
- **任务目标**：想要实现什么？
- **具体场景**：在什么情况下使用？
- **输入数据**：输入是什么格式？有哪些字段？
- **输出结果**：期望输出什么？
- **技术要求**：有什么特殊约束吗？

### 📝 示例

| 简短 ❌ | 详细 ✅ |
|--------|--------|
| 写一个函数 | 用 Python 写一个函数，接收用户名列表，返回最长的用户名 |
| LRU 缓存 | 用 Python 实现 LRU 缓存，容量 100，支持 get/put 操作，O(1) 时间复杂度 |
| 游戏脚本 | 用 Python + Pygame 写一个贪吃蛇游戏，支持方向键控制 |

### 🔧 优化后的 prompt 将包含
- 清晰的任务描述
- 具体的输入/输出规格
- 边界情况处理
- 质量标准"""
                else:
                    return f"""## ⚠️ Insufficient Instruction Information

Your instruction "{stripped}" lacks sufficient detail to generate a targeted optimized prompt.

### 💡 Please provide more information

Consider including:
- **Task goal**: What do you want to implement?
- **Specific scenario**: In what context will it be used?
- **Input data**: What format is the input? What fields?
- **Expected output**: What should the output look like?
- **Technical requirements**: Any specific constraints?

### 📝 Examples

| Vague ❌ | Specific ✅ |
|----------|-------------|
| write a function | Write a Python function that receives a list of usernames and returns the longest one |
| LRU cache | Implement an LRU cache in Python with capacity 100, supporting get/put operations with O(1) time complexity |
| game script | Write a Snake game using Python + Pygame with arrow key controls |

### 🔧 An optimized prompt will include
- Clear task description
- Specific input/output specifications
- Boundary condition handling
- Quality standards"""
            
            return f"""## 🎯 任务
用 {lang_default} 实现：{stripped}

## 📥 输入
- {defaults.get('input', '由调用方提供')}

## 📤 输出
- {output_desc}

## ⚡ 性能要求
- {perf}

## 🛡️ 边界情况
{boundary}"""
        # Issue #6 fix: if _infer_code_defaults returned None or both input/output
        # are generic placeholders, the instruction is too vague - return warning
        if lang == 'zh':
            return f"""## ⚠️ 指令信息不足

您的指令「{stripped}」信息不足，无法生成有针对性的优化 prompt。

### 💡 请补充更多信息

建议包括：
- **任务目标**：想要实现什么？
- **具体场景**：在什么情况下使用？
- **输入数据**：输入是什么格式？有哪些字段？
- **输出结果**：期望输出什么？
- **技术要求**：有什么特殊约束吗？

### 📝 示例

| 简短 ❌ | 详细 ✅ |
|--------|--------|
| 写一个函数 | 用 Python 写一个函数，接收用户名列表，返回最长的用户名 |
| LRU 缓存 | 用 Python 实现 LRU 缓存，容量 100，支持 get/put 操作，O(1) 时间复杂度 |
| 游戏脚本 | 用 Python + Pygame 写一个贪吃蛇游戏，支持方向键控制 |

### 🔧 优化后的 prompt 将包含
- 清晰的任务描述
- 具体的输入/输出规格
- 边界情况处理
- 质量标准"""
        else:
            return f"""## ⚠️ Insufficient Instruction Information

Your instruction "{stripped}" lacks sufficient detail to generate a targeted optimized prompt.

### 💡 Please provide more information

Consider including:
- **Task goal**: What do you want to implement?
- **Specific scenario**: In what context will it be used?
- **Input data**: What format is the input? What fields?
- **Expected output**: What should the output look like?
- **Technical requirements**: Any specific constraints?

### 📝 Examples

| Vague ❌ | Specific ✅ |
|----------|-------------|
| write a function | Write a Python function that receives a list of usernames and returns the longest one |
| LRU cache | Implement an LRU cache in Python with capacity 100, supporting get/put operations with O(1) time complexity |
| game script | Write a Snake game using Python + Pygame with arrow key controls |

### 🔧 An optimized prompt will include
- Clear task description
- Specific input/output specifications
- Boundary condition handling
- Quality standards"""

    # Email types
    if instruction_type == "rejection_email":
        return f"""## 🎯 任务
写一封拒绝候选人的邮件

## 📧 邮件结构
1. **称呼**（感谢投递，如"尊敬的张三同学"）
2. **开场**（简短感谢参加面试）
3. **正文**（面试反馈，1-2 句正面评价）
4. **拒绝**（委婉表达"暂不推进"）
5. **祝福**（祝愿职业发展）
6. **签名**（发件人姓名、职位、日期）

## ✍️ 语气要求
- 专业友善，不伤人
- 简洁明了，不留模糊希望
- 不用"很遗憾""抱歉"等过度负面词"""

    if instruction_type == "apology_email":
        return f"""## 🎯 任务
写一封道歉邮件

## 📧 邮件结构
1. **称呼**
2. **承认问题**（简明说明发生了什么问题）
3. **说明原因**（如不适合展开，可简略带过）
4. **道歉**（真诚、具体）
5. **补救措施**（打算如何弥补或防止再犯）
6. **邀请反馈**
7. **签名**

## ✍️ 语气要求
- 真诚，不找借口，不过度解释
- 具体说明对什么道歉
- 提出切实补救措施"""

    if instruction_type == "notification_email":
        return f"""## 🎯 任务
写一封团队/组织内部通知邮件

## 📧 邮件结构
1. **标题**（简洁明了，一眼看出内容）
2. **称呼**
3. **正文**（通知内容，重要信息靠前）
4. **行动要求**（需要收件人做什么，清晰列出）
5. **联系方式**
6. **签名**

## ✍️ 语气要求
- 清晰、准确、不含糊
- 重要信息加粗或列点"""

    if instruction_type == "complaint_email":
        return f"""## 🎯 任务
回复一封客户投诉邮件

## 📧 邮件结构
1. **称呼**（感谢来信，表明收到）
2. **确认问题**（复述客户投诉的核心问题）
3. **道歉**
4. **调查说明**（我们已采取/正在采取的措施）
5. **解决方案**（具体补救/赔偿方案）
6. **预防承诺**
7. **邀请反馈**
8. **签名**

## ✍️ 语气要求
- 真诚倾听，不防御
- 不推卸责任
- 解决方案具体、可操作"""

    if instruction_type == "report_email":
        return f"""## 🎯 任务
写一份工作周报/月报

## 📧 周报结构
1. **标题**（如"[姓名] [日期区间] 周报"）
2. **本周完成**（列出 3-5 项已完成任务，含结果/产出）
3. **进行中**（正在推进的任务及当前进度 %）
4. **下周计划**
5. **风险/阻塞**（如有）
6. **数据指标**（如有 KPI）

## ✍️ 风格要求
- 结果导向（不说"做了什么"，说"做成了什么"）
- 量化成果
- 简洁"""

    if instruction_type == "creative_writing":
        info = _extract_info(stripped, instruction_type)
        return f"""## 🎯 创作任务
{stripped}

## 📖 题材与形式
- 类型：[小说/散文/短篇/科幻/奇幻/悬疑/剧本]
- 风格：{info['style']}
- 视角：第三人称

## 👥 目标读者
- 受众群体：{info['audience']}
- 期待体验：读者读完后的情感共鸣或收获

## 🏗️ 结构要求
- 开头：先声夺人
- 发展：通过冲突/情节推进故事
- 结尾：令人回味/出乎意料/留白

## ✍️ 写作风格
- 语气：{info['tone']}
- 语言：{info['language']}"""

    if instruction_type == "academic_writing":
        info = _extract_info(stripped, instruction_type)
        return f"""## 🎯 学术写作任务
{stripped}

## 📄 文章类型
- 类型：文献综述
- 学术领域：计算机科学

## 📋 摘要结构
1. **背景**（该领域现状和研究空白）
2. **目的/研究问题**
3. **方法**（数据集/模型/实验/分析）
4. **主要发现**（量化优先）
5. **结论**（意义、局限性、未来方向）

## ✍️ 写作规范
- 语言：{info['language']}
- 语气：学术严谨、客观"""

    if instruction_type == "writing":
        info = _extract_info(stripped, instruction_type)
        return f"""## 🎯 写作任务
{stripped}

## 👥 受众
- 目标读者：{info['audience']}
- 读者关心什么：{info['topic']} 的核心价值和应用

## 🎯 核心信息
- 主要观点：围绕 {info['topic']} 展开
- 期望行动：让读者了解并能实际应用

## 🎨 风格要求
- 语气：{info['tone']}
- 语言：{info['language']}
- 篇幅：800-1500 字

## 🏗️ 结构
- 开头：先用问题或现象引入
- 主体：围绕核心要点展开
- 结尾：总结要点，行动引导"""

    if instruction_type == "explanation":
        info = _extract_info(stripped, instruction_type)
        core_concept = _extract_core_concept(stripped)
        return f"""## 🎯 解释任务
{stripped}

## 👤 受众画像
- 年龄/职业：{info['audience']}
- 技术背景：一般读者，对 {core_concept} 有基本了解
- 关心什么：{core_concept} 是什么、如何工作、有什么应用场景

## 🔬 解释深度
- 层次：{info['depth']}
- 核心概念：{core_concept} 的定义、原理、应用场景

## 🧩 讲解策略
- 类比场景：{info['analogy']}
- 讲解顺序：从已知到未知，逐步深入

## ✅ 检验理解
- 读者读完后能回答：{core_concept} 是什么？有什么应用场景？"""

    return f"""## 🎯 任务
{stripped}

## 📋 执行要求
- 执行者：[AI / 专家 / 助手？]
- 目标：[明确要达到什么]
- 约束条件：[如有]

## ✅ 质量标准
- 什么样的结果算好：[描述标准]
- 参考案例：[有的话提供]"""


# =============================================================================
# Technique Recommendations
# =============================================================================

def get_technique_recommendations(instr_type: str, instruction: str) -> tuple[str, str]:
    """Return (applicable_techniques, examples) for a given instruction type."""
    recommendations = []
    examples = []

    if instr_type == "code":
        recommendations.append("- Chain-of-Thought：先分析最优子结构再写")
        recommendations.append("- Few-shot：给1-2个输入输出示例")
        recommendations.append("- Role：扮演资深工程师")
        if any(kw in instruction.lower() for kw in ('排序', 'sort', 'quicksort', 'mergesort')):
            examples.append("输入：[3, 1, 2] → 输出：[1, 2, 3]")
            examples.append("输入：[5, 2, 9, 1] → 输出：[1, 2, 5, 9]")
        elif any(kw in instruction.lower() for kw in ('登录', 'login', '登陆', 'auth')):
            examples.append("输入：用户名=alice，密码=Pass1234 → 输出：JWT token")
            examples.append("输入：用户名=unknown，密码=Pass1234 → 输出：用户不存在")
        elif any(kw in instruction.lower() for kw in ('斐波那契', 'fibonacci')):
            examples.append("输入：n=0 → 输出：0")
            examples.append("输入：n=6 → 输出：8")
        elif any(kw in instruction.lower() for kw in ('平方', 'square', '幂', 'power')):
            examples.append("输入：3 → 输出：9")
            examples.append("输入：[1, 2, 3] → 输出：[1, 4, 9]")
        elif any(kw in instruction.lower() for kw in ('json', '数组', 'list')):
            # T10: generic JSON/array processing — NOT averaging (that's T11)
            examples.append("输入：{\"name\": \"Alice\", \"age\": 30} → 输出：提取 name 字段 → \"Alice\"")
            examples.append("输入：[1, \"hello\", {\"a\": 1}] → 输出：验证 JSON 格式合法 → True")
        elif any(kw in instruction.lower() for kw in ('lru', 'cache', '缓存')):
            examples.append("输入：set(1,'a'), get(1), set(2,'b') → 输出：'a', None（key=2未命中）")
            examples.append("输入：capacity=2, set(1,'x'), set(2,'y'), set(3,'z') → 输出：key=1被淘汰")
        elif any(kw in instruction.lower() for kw in ('游戏', 'game', '脚本', 'script')):
            examples.append("输入：蛇游戏 初始方向→右 → 输出：蛇头坐标+1")
            examples.append("输入：2048 合并相同数字 → 输出：棋盘状态更新")
        elif any(kw in instruction.lower() for kw in ('二分', 'binary search')):
            examples.append("输入：[1,3,5,7,9], target=7 → 输出：3（下标）")
            examples.append("输入：[1,3,5,7,9], target=4 → 输出：-1（不存在）")
        elif any(kw in instruction.lower() for kw in ('api', 'rest', '接口', 'endpoint')):
            examples.append("输入：GET /users/1 → 输出：{code:0, data:{id:1,name:'alice'}}")
            examples.append("输入：POST /users {name:'bob'} → 输出：{code:0, data:{id:2}}")
        elif any(kw in instruction.lower() for kw in ('dp', '动态规划', '爬楼梯')):
            examples.append("输入：n=5 → 输出：8（爬楼梯方法数）")
            examples.append("输入：n=0 → 输出：1（边界）")
        else:
            # P1-A fix: provide meaningful examples based on code keywords, not generic placeholders
            instr_lower = instruction.lower()
            if any(kw in instr_lower for kw in ('sql', '数据库', 'db', 'database', 'select', 'insert', 'update', 'delete')):
                examples.append("输入：SELECT * FROM users WHERE id = 1 → 输出：用户 alice 的完整信息")
                examples.append("输入：INSERT INTO orders VALUES (1, 'item', 100) → 输出：插入成功，返回订单ID")
            elif any(kw in instr_lower for kw in ('function', '函数', 'method', '方法', 'procedure')):
                examples.append("输入：[1, 2, 3] → 输出：[1, 3]（过滤偶数）")
                examples.append("输入：'hello world' → 输出：'HELLO WORLD'（转大写）")
            elif any(kw in instr_lower for kw in ('user', 'data', '数据', '处理', 'process')):
                examples.append("输入：{'name': 'alice', 'age': 30} → 输出：验证必填字段存在 → True")
                examples.append("输入：{'email': 'bad'} → 输出：格式校验失败 → {'error': 'invalid email'}")
            else:
                # Generic fallback with concrete IO format
                examples.append("输入：[1, 2, 3] → 输出：[1, 3]（过滤偶数）")
                examples.append("输入：'hello' → 输出：'HELLO'（转大写）")

    elif instr_type == "explanation":
        recommendations.append("- Role：扮演耐心的老师")
        recommendations.append("- Chain-of-Thought：按认知顺序逐步拆解")
        recommendations.append("- Few-shot：给1个理解过程的示例")
        # Issue #5 fix: Use topic-relevant analogies instead of generic ones
        instr_lower = instruction.lower()
        if any(kw in instr_lower for kw in ["量子", "quantum", "纠缠", "entangle"]):
            examples.append('类比：两个粒子无论相隔多远，一个动另一个同时动——像心灵感应的双胞胎')
            examples.append('类比：想象两个人各拿一枚总是朝向相反的硬币')
        elif any(kw in instr_lower for kw in ["机器学习", "machine learning", "ml", "监督学习", "分类", "回归"]):
            examples.append('类比：教小孩认识猫——给他看很多猫的照片，下次他就能认出猫了')
            examples.append('类比：学生做题后看答案纠正思路，逐渐学会解题方法')
        elif any(kw in instr_lower for kw in ["区块链", "blockchain", "比特币", "bitcoin"]):
            examples.append('类比：把"区块链去中心化"比作"村民共同记账"')
            examples.append('类比：区块链像一本无法撕页、无法篡改的公共账本')
        elif any(kw in instr_lower for kw in ["数据库", "index", "索引", "database"]):
            examples.append('类比：数据库索引就像书的目录，找内容不用翻完整本书')
            examples.append('类比：图书馆索引柜告诉你书籍在哪个区域')
        elif any(kw in instr_lower for kw in ["api", "rest", "接口", "restful"]):
            examples.append('类比：API 就像餐厅服务员——你告诉服务员要什么菜，他去厨房拿给你')
            examples.append('类比：API 是软件之间的"对话窗口"，双方按约定格式交流')
        elif any(kw in instr_lower for kw in ["微服务", "microservice", "云计算", "cloud"]):
            examples.append('类比：微服务就像分工明确的团队，每人做专长的事')
            examples.append('类比：云计算像用电——不用自己发电，按需付费')
        else:
            examples.append('类比：用生活中的例子说明，把复杂概念类比为熟悉的事物')
            examples.append('类比：从已知到未知，按认知顺序逐步拆解')

    elif instr_type == "writing":
        recommendations.append("- Few-shot：给1篇范文参考")
        recommendations.append("- Chain-of-Thought：先列提纲再写")
        recommendations.append("- Role：扮演专业文案撰写者")
        examples.append('风格参考：开头用"你是否也遇到过..."引发共鸣')
        examples.append('语气示例：面向程序员用"无需多余配置"')

    elif instr_type in ("rejection_email", "notification_email", "complaint_email",
                         "apology_email", "report_email"):
        recommendations.append("- Few-shot：给1封同类邮件参考")
        recommendations.append("- Role：扮演专业商务沟通顾问")
        recommendations.append("- Chain-of-Thought：明确目的→组织结构→措辞选择")
        examples.append("参考结构：称呼→开门见山→核心内容→积极收尾")

    else:
        recommendations.append("- Zero-shot：直接给出清晰指令")
        recommendations.append("- Chain-of-Thought：分步骤描述任务")
        recommendations.append("- Role：明确期望的执行者身份")

    return "\n".join(recommendations), "\n".join(examples)


# =============================================================================
# Main Generator - All LLM-powered with tier selection
# =============================================================================

def generate_optimized_prompt(instruction: str, tier: str = None) -> str:
    """
    Generate optimized prompt using LLM with tier selection.
    
    Args:
        instruction: The user instruction to optimize
        tier: "auto" (default), "fast", "medium", "deep"
    
    Returns:
        Optimized prompt text
    """
    if tier is None or tier == "auto":
        tier = get_llm_tier(instruction)
    
    effective_tier = "fast" if tier == "medium" else tier
    
    # Select appropriate prompt template
    if effective_tier == "fast":
        prompt_template = FAST_GENERATION_PROMPT
    else:
        prompt_template = DEEP_GENERATION_PROMPT
    
    # Try LLM generation
    result = call_llm(
        prompt_template.format(instruction=instruction),
        tier=effective_tier
    )
    
    if result:
        return result
    
    # Fallback to template-based generation
    instr_type = detect_instruction_type(instruction)
    return generate_fallback_prompt(instruction, instr_type)


def generate_optimized_versions(instruction: str, count: int = 3, tier: str = None) -> list[VersionResult]:
    """
    Generate optimized prompt versions for the given instruction.
    All versions use LLM with tier selection.
    """
    if tier is None or tier == "auto":
        tier = get_llm_tier(instruction)
    
    analysis = analyze_instruction(instruction, tier=tier)
    instr_type = analysis["instruction_type"]
    stripped = instruction.strip()

    applicable_techniques, examples = get_technique_recommendations(instr_type, stripped)
    versions = []

    # Version A: LLM-generated (primary)
    generated_a = generate_optimized_prompt(stripped, tier=tier)
    versions.append({
        "type": "A (LLM Optimized)",
        "description": "LLM 生成的优化 prompt",
        "template": generated_a,
        "is_direct": False,
        "applicable_techniques": applicable_techniques,
        "examples": examples,
    })

    if count == 1:
        return versions

    # Version B: More detailed version
    # Use deep tier for version B if available
    if tier == "fast":
        generated_b = generate_optimized_prompt(stripped, tier="medium")
    else:
        # Same tier but different angle - add specificity
        cfg = get_llm_config()
        api_key = cfg.get("llm_api_key")
        if api_key:
            # Ask LLM for a more detailed variant
            detailed_prompt = f"""用户想要：{stripped}

请生成一个更详细、更具体的优化 prompt 版本，包含：
- 更精确的约束条件
- 更明确的输入输出规格
- 更具体的边界情况处理
- 性能要求（时间/空间复杂度）

直接输出 prompt 文本。"""
            result = call_llm(detailed_prompt, tier="deep" if tier == "deep" else "fast")
            generated_b = result if result else generate_fallback_prompt(stripped, instr_type)
        else:
            generated_b = generate_fallback_prompt(stripped, instr_type)

    versions.append({
        "type": "B (Detailed)",
        "description": "更详细的 prompt 模板，明确关键要素",
        "template": generated_b,
        "is_direct": False,
        "applicable_techniques": applicable_techniques,
        "examples": examples,
    })

    if count <= 2:
        return versions

    # Version C: Most complete
    # Use deep tier for version C
    if tier in ("fast", "medium"):
        generated_c = generate_optimized_prompt(stripped, tier="deep")
    else:
        # Ask for most comprehensive version
        cfg = get_llm_config()
        api_key = cfg.get("llm_api_key")
        if api_key:
            comprehensive_prompt = f"""用户想要：{stripped}

请生成一个最完整的优化 prompt，包含：
- 完整的任务描述
- 所有可能的约束条件
- 边界情况和异常处理
- 质量标准和验收条件
- 相关的最佳实践建议

直接输出 prompt 文本。"""
            result = call_llm(comprehensive_prompt, tier="deep")
            generated_c = result if result else generate_fallback_prompt(stripped, instr_type)
        else:
            generated_c = generate_fallback_prompt(stripped, instr_type)

    versions.append({
        "type": "C (Complete)",
        "description": "最完整的 prompt，覆盖所有关键维度",
        "template": generated_c,
        "is_direct": False,
        "applicable_techniques": applicable_techniques,
        "examples": examples,
    })

    return versions[:count]


# =============================================================================
# Evaluation (Simplified)
# =============================================================================

def evaluate_version(version: VersionResult, analysis: AnalysisResult) -> EvaluationResult:
    """Content-based evaluation that differentiates quality.
    
    Issue #2 fix: Make scoring sensitive to input specificity.
    - For Chinese instructions: use Chinese character count (not word count)
    - For English instructions: use word count
    - Strongly penalize generic placeholders
    - Reward concrete, quantified specifications
    """
    template = version["template"]
    instr_type = analysis["instruction_type"]
    lang = analysis.get("language", "zh")
    
    # Use Chinese char count for Chinese instructions (word_count from split() is always 1 for Chinese)
    if lang == "zh":
        # Chinese char count; threshold for vagueness: < 10 chars = vague
        # This is approximate - we don't have the original instruction here,
        # but the word_count in analysis can serve as a proxy for specificity
        word_count = analysis.get("word_count", 10)
        # For Chinese: word_count is always 1 from split().
        # Use the analysis['word_count'] as-is but cap at a reasonable max
        # The REAL specificity signal comes from whether the template has concrete content
        effective_count = word_count
    else:
        effective_count = analysis.get("word_count", 10)
    
    # Base score from instruction vagueness - lower for vague instructions
    vagueness_penalty = max(0, (10 - effective_count) * 0.3)
    
    clarity_score = max(1, round(7.0 - vagueness_penalty, 2))
    specificity_score = max(1, round(7.0 - vagueness_penalty, 2))
    completeness_score = max(1, round(7.0 - vagueness_penalty, 2))

    # Penalty for generic placeholder phrases (both English and Chinese)
    truly_blank_phrases = [
        "[请补充]", "[描述]", "[填写]", "[如 有]", "[可选]",
        "[你决定]", "[未知]", "[自定义]", "______",
        "[数据类型、格式、范围]", "[数据类型]", "[格式]", "[范围]",
        "类型和数据范围（根据任务描述推断）",  # Chinese generic placeholder
        "任务目标的处理结果",  # Chinese generic placeholder
        "具体输入示例",  # Chinese generic placeholder
        "对应输出示例",  # Chinese generic placeholder
        "如有要求请注明",  # Chinese generic placeholder
        "空输入 → 如何处理",  # Chinese generic placeholder
        "异常值 → 如何处理",  # Chinese generic placeholder
    ]
    for phrase in truly_blank_phrases:
        if phrase in template:
            blank_count = template.count(phrase)
            specificity_score -= blank_count * 0.8
            completeness_score -= blank_count * 0.8

    if instr_type == "code":
        # Strong bonus for real input/output specs (not generic placeholders)
        if _has_real_content(template, ["输入", "input", "参数"]):
            specificity_score += 2.5
            completeness_score += 1.5
        if _has_real_content(template, ["输出", "output", "返回"]):
            specificity_score += 1.5
            completeness_score += 1.5
        # Strong bonus for quantified constraints (time/space complexity)
        if _has_quantified_constraint(template):
            specificity_score += 3.0
            completeness_score += 1.5
        # Bonus for explicit language specification
        if _has_explicit_language(template, ["python", "javascript", "java", "go", "rust", "sql"]):
            specificity_score += 1.5
        # Bonus for boundary case handling
        if _has_real_content(template, ["边界", "edge", "空输入", "异常"]):
            completeness_score += 2.0
            specificity_score += 1.0
        # Bonus for concrete code examples in template
        if "```" in template or "def " in template or "function " in template:
            specificity_score += 2.0
            completeness_score += 1.0

    elif instr_type == "writing":
        if _has_real_content(template, ["受众", "读者", "audience"]):
            specificity_score += 2.5
            completeness_score += 1.5
        if _has_real_content(template, ["写作目的", "核心", "key point"]):
            specificity_score += 1.5
            completeness_score += 1.5

    elif instr_type == "explanation":
        if _has_real_content(template, ["受众", "背景", "audience"]):
            specificity_score += 2.5
            completeness_score += 1.5
        if _has_real_content(template, ["类比", "analogy"]):
            completeness_score += 1.5
            specificity_score += 1.0

    elif instr_type in ("rejection_email", "notification_email", "complaint_email",
                        "apology_email", "report_email"):
        if _has_real_content(template, ["称呼"]):
            completeness_score += 1.5
        if _has_real_content(template, ["正文", "内容"]):
            completeness_score += 1.5
        if _has_real_content(template, ["语气", "tone", "风格"]):
            specificity_score += 1.5
        if _has_real_content(template, ["参考模板", "模板", "示例"]):
            specificity_score += 2.5
            completeness_score += 1.5

    clarity_score = max(1, min(10, clarity_score))
    specificity_score = max(1, min(10, specificity_score))
    completeness_score = max(1, min(10, completeness_score))

    overall = round(
        clarity_score * 0.25 + specificity_score * 0.40 + completeness_score * 0.35,
        2
    )

    if overall >= 8.0:
        grade = "A"
    elif overall >= 6.5:
        grade = "B"
    elif overall >= 5.0:
        grade = "C"
    else:
        grade = "D"

    return {
        "scores": {
            "clarity": clarity_score,
            "specificity": specificity_score,
            "completeness": completeness_score,
        },
        "overall": overall,
        "grade": grade,
    }


def _has_real_content(template: str, keywords: list[str]) -> bool:
    """Check if template contains non-generic content around given keywords."""
    generic_phrases = {
        "[数据类型、格式、范围]", "[描述]", "[填写]", "[请补充]",
        "[数据类型]", "[格式]", "[范围]", "______", "[如 有]",
    }
    template_lower = template.lower()
    for kw in keywords:
        idx = template_lower.find(kw.lower())
        if idx == -1:
            continue
        start = max(0, idx - 5)
        end = min(len(template), idx + 20)
        snippet = template[start:end]
        for ph in generic_phrases:
            if ph in snippet:
                return False
        return True
    return False


def _has_quantified_constraint(template: str) -> bool:
    """Check if template has quantified constraints."""
    import re
    quantified_patterns = [
        r"O\([^)]+\)",
        r"\d+\s*-\s*\d+",
        r"\d+\s*个",
        r"\d+k",
        r"\d+M",
        r"时间复杂度",
        r"空间复杂度",
        r"\d+\s*小时",
        r"\d+\s*分钟",
        r"\d+\s*秒",
    ]
    for pat in quantified_patterns:
        if re.search(pat, template, re.IGNORECASE):
            return True
    return False


def _has_explicit_language(template: str, langs: list[str]) -> bool:
    """Check if template explicitly names a programming language."""
    template_lower = template.lower()
    for lang in langs:
        if lang in template_lower:
            return True
    return False


def recommend_version(evaluations: list[EvaluationResult], analysis: AnalysisResult) -> int:
    """Recommend based on task complexity."""
    complexity = analysis["task_complexity"]
    
    if complexity == "simple":
        for i, eval_result in enumerate(evaluations):
            if eval_result["overall"] >= 8.0:
                return i
    else:
        for i, eval_result in enumerate(evaluations):
            if eval_result["overall"] >= 6.0:
                return i
    
    return 0


# =============================================================================
# LLM Generation (legacy, wraps call_llm)
# =============================================================================

def generate_with_llm(instruction: str, api_key: str = None, model: str = "gpt-4",
                      endpoint: str = "https://api.openai.com/v1/chat/completions",
                      instruction_type: str = None) -> Optional[str]:
    """
    Legacy LLM generation function.
    Use generate_optimized_prompt() instead for tier-aware generation.
    """
    if not api_key:
        cfg = get_llm_config()
        api_key = cfg.get("llm_api_key")
        model = cfg.get("llm_model", "gpt-4")
        endpoint = cfg.get("llm_endpoint", "https://api.openai.com/v1/chat/completions")

    system = """你是一个专业的 prompt 工程专家，擅长将模糊的用户需求转化为完整、精确的 prompt。
你的工作哲学：不要问用户问题，直接推理并填充合理的默认值；宁可多做，不要少做；深度推理比规则匹配好 100 倍。"""

    type_prompts = {
        "code": f"""你是一个 prompt 工程专家。用户想要：\n\n{instruction}\n\n请深度思考并生成优化后的 prompt。直接输出，不要解释。""",
        "writing": f"""你是写作专家，擅长生成能产生好内容的写作指令。用户想要：\n\n{instruction}\n\n请生成优化后的写作 prompt。直接输出，不要解释。""",
        "explanation": f"""你是一位老师，擅长把复杂概念讲得通俗易懂。用户想要理解：\n\n{instruction}\n\n请生成优化后的解释 prompt。直接输出，不要解释。""",
    }
    
    user_prompt = type_prompts.get(instruction_type, f"""用户想要：\n\n{instruction}\n\n请深度思考并生成优化后的 prompt。直接输出，不要解释。""")

    try:
        response = requests.post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.8,
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def optimize_with_llm(instruction: str, instruction_type: str = None) -> OptimizationResult:
    """Optimize using LLM when API key is configured. Legacy function."""
    cfg = get_llm_config()
    api_key = cfg.get("llm_api_key")
    model = cfg.get("llm_model", "gpt-4")
    endpoint = cfg.get("llm_endpoint", "https://api.openai.com/v1/chat/completions")

    analysis = analyze_instruction(instruction, tier="deep")
    instr_type = instruction_type or analysis["instruction_type"]

    if not api_key:
        generated = generate_fallback_prompt(instruction, instr_type)
        version: VersionResult = {
            "type": "Fallback (No API)",
            "description": "结构化模板（未配置 API key，使用内置模板）",
            "template": generated,
            "is_direct": False,
            "applicable_techniques": "",
            "examples": "",
        }
        evaluation = evaluate_version(version, analysis)
        return {
            "original": instruction,
            "analysis": analysis,
            "versions": [version],
            "evaluations": [evaluation],
            "recommended_idx": 0,
            "recommended_version": version,
            "recommended_evaluation": evaluation,
            "llm_tier": "none",
        }

    generated = generate_with_llm(instruction, api_key, model, endpoint, instr_type)
    if not generated:
        generated = generate_fallback_prompt(instruction, instr_type)
        version = {
            "type": "Fallback (LLM Failed)",
            "description": "结构化模板（LLM 调用失败，使用内置模板）",
            "template": generated,
            "is_direct": False,
            "applicable_techniques": "",
            "examples": "",
        }
    else:
        version = {
            "type": "LLM Optimized",
            "description": "LLM 生成的优化 prompt",
            "template": generated,
            "is_direct": False,
            "applicable_techniques": "",
            "examples": "",
        }

    evaluation = evaluate_version(version, analysis)
    return {
        "original": instruction,
        "analysis": analysis,
        "versions": [version],
        "evaluations": [evaluation],
        "recommended_idx": 0,
        "recommended_version": version,
        "recommended_evaluation": evaluation,
        "llm_tier": "deep",
    }


# =============================================================================
# Main Pipeline
# =============================================================================

def optimize(instruction: str, use_llm: bool = False, tier: str = None) -> OptimizationResult:
    """
    Main optimization pipeline. All steps use LLM with tier selection.
    
    Args:
        instruction: The instruction to optimize
        use_llm: Legacy flag, use tier instead (tier="deep" if True)
        tier: "auto" (default), "fast", "medium", "deep"
            - auto: selects tier based on instruction complexity
            - fast: use fast model (gpt-3.5-turbo)
            - medium: use fast model with detailed prompt
            - deep: use deep model (gpt-4) with detailed prompt
    
    Returns:
        OptimizationResult with analysis, versions, evaluations, and recommended version
    """
    # Handle legacy use_llm flag
    if use_llm and tier is None:
        tier = "deep"
    
    # Default to auto tier selection
    if tier is None:
        tier = "auto"
    
    # Determine effective tier for analysis
    effective_tier = tier
    if tier == "auto":
        effective_tier = get_llm_tier(instruction)
    
    analysis = analyze_instruction(instruction, tier=effective_tier)
    instr_type = analysis["instruction_type"]

    # Check if API key is available
    cfg = get_llm_config()
    has_api_key = bool(cfg.get("llm_api_key"))
    
    if not has_api_key:
        # No API key: use fallback templates
        versions = generate_optimized_versions(instruction, count=3, tier="fast")
        evaluations = [evaluate_version(v, analysis) for v in versions]
        recommended_idx = recommend_version(evaluations, analysis)
        return {
            "original": instruction,
            "analysis": analysis,
            "versions": versions,
            "evaluations": evaluations,
            "recommended_idx": recommended_idx,
            "recommended_version": versions[recommended_idx],
            "recommended_evaluation": evaluations[recommended_idx],
            "llm_tier": "none",
        }

    # Has API key: generate versions using LLM with tier selection
    versions = generate_optimized_versions(instruction, count=3, tier=tier)
    evaluations = [evaluate_version(v, analysis) for v in versions]
    recommended_idx = recommend_version(evaluations, analysis)
    
    return {
        "original": instruction,
        "analysis": analysis,
        "versions": versions,
        "evaluations": evaluations,
        "recommended_idx": recommended_idx,
        "recommended_version": versions[recommended_idx],
        "recommended_evaluation": evaluations[recommended_idx],
        "llm_tier": effective_tier,
    }


# =============================================================================
# Feedback & Learning
# =============================================================================

def record_feedback(instruction: str, chosen_idx: int, feedback: Optional[str] = None,
                   improvement: Optional[str] = None) -> dict:
    """Record user feedback to improve future recommendations."""
    prefs = load_preferences()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "instruction": instruction[:100],
        "chosen_version": ["A", "B", "C"][chosen_idx],
        "feedback": feedback,
        "improvement": improvement,
    }
    
    prefs["feedback_history"].append(entry)
    
    if improvement:
        imp_lower = improvement.lower()
        if any(w in imp_lower for w in ["simple", "concise", "直接"]):
            prefs["format_preference"] = "direct"
        elif any(w in imp_lower for w in ["detail", "详细", "复杂"]):
            prefs["format_preference"] = "detailed"
    
    save_preferences(prefs)
    return prefs

# =============================================================================
# Template Management
# =============================================================================

def save_template(name: str, prompt: str, tags: Optional[list[str]] = None,
                  description: Optional[str] = None) -> dict:
    template = {
        "name": name,
        "prompt": prompt,
        "tags": tags or [],
        "description": description or "",
        "created": datetime.now().isoformat(),
        "use_count": 0,
    }
    safe_name = name.lower().replace(" ", "-")
    with open(TEMPLATES_DIR / f"{safe_name}.json", "w") as f:
        json.dump(template, f, indent=2)
    return template

def list_templates() -> list[dict]:
    templates = []
    for filepath in TEMPLATES_DIR.glob("*.json"):
        with open(filepath, "r") as f:
            templates.append(json.load(f))
    return sorted(templates, key=lambda t: t.get("use_count", 0), reverse=True)

def search_templates(query: str) -> list[dict]:
    query_lower = query.lower()
    return [t for t in list_templates()
            if query_lower in t.get("name", "").lower()
            or query_lower in t.get("prompt", "").lower()]
