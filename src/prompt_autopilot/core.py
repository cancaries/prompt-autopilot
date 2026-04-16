"""
Core optimization logic for prompt-autopilot v2.

Philosophy: Direct answers, not templates. The tool should complete tasks,
not create more work for the user.
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
# Category-Specific Generation Prompt Templates
# =============================================================================

CODE_GENERATION_PROMPT = '''你是编程专家，擅长生成高质量的编程指令。

【用户需求】
{instruction}

【判断标准】
差 prompt："写个排序算法" → 太模糊，缺少上下文
好 prompt："用 Python 实现快速排序，支持自定义比较函数，用于处理大量金融数据"

【必须包含的要素】（全部需要）
□ 编程语言/框架（必须明确，如 Python/JavaScript/Go）
□ 输入规格（输入是什么？类型、格式、范围）
□ 输出规格（输出是什么？类型、格式、示例）
□ 核心逻辑要求（算法、数据结构、架构设计）
□ 边界情况处理（空输入、异常值、大规模数据）
□ 性能要求（时间/空间复杂度，如有）
□ 安全要求（如有：输入校验、SQL注入防护等）

【禁止出现】
× "写个XX功能" → 必须改为 "用X语言实现X，支持X场景"
× 模糊的约束条件 → 必须量化（如 "支持100万条数据"）
× 缺少错误处理的设计

【输出格式】
直接输出优化后的 prompt，包含以上所有要素，用自然段落组织，不要分点列举。'''

WRITING_GENERATION_PROMPT = '''你是写作专家，擅长生成清晰的写作指令。

【用户需求】
{instruction}

【判断标准】
差 prompt："写一封邮件" → 缺少对象、目的、语气
好 prompt："写一封给投资人的项目进展邮件，汇报Q3业绩未达标，说明原因并提出下季度改进措施，语气专业但坦诚"

【必须包含的要素】（全部需要）
□ 受众是谁（投资人/客户/同事/上级？年龄/职位/背景）
□ 写作目的（汇报/说服/道歉/通知/解释？）
□ 核心信息（必须传达的3个要点）
□ 语气风格（正式/亲切/严肃/轻松？中文还是英文？）
□ 结构要求（总分总/清单/书信格式？）
□ 字数/长度要求（如有）
□ 禁止事项（不要提到XX，不要用XX语气）

【禁止出现】
× "写一封邮件" → 必须改为 "写一封给XX的，关于XX的邮件"
× 模糊受众 → 必须明确（"技术人员" vs "CEO" 完全不同）
× 缺少行动指引 → 邮件需要明确期望读者做什么

【输出格式】
直接输出优化后的 prompt，自然段落形式。'''

EXPLANATION_GENERATION_PROMPT = '''你是一位老师，擅长用通俗易懂的方式解释复杂概念。

【用户需求】
{instruction}

【判断标准】
差 prompt："解释一下区块链" → 太宽泛，没有重点
好 prompt："向没有技术背景的 30-40 岁职场人士解释区块链，用他们熟悉的银行转账做类比，重点讲清去中心化和不可篡改这两个核心特性"

【必须包含的要素】（全部需要）
□ 受众是谁（年龄、教育背景、技术敏感度）
□ 解释深度（科普/专业/学术？）
□ 核心概念（1-3个必须讲清楚的概念）
□ 类比/生活场景（必须有一个身边的例子）
□ 关键要点（3个以内，读完能记住的）
□ 常见误解（1-2个，写在最后作为提醒）

【禁止出现】
× "解释XX是什么" → 必须改为 "向XX解释XX，重点是XX"
× 过多专业术语 → 必须用通俗语言
× 只讲what不讲why → 要解释原理

【输出格式】
直接输出优化后的 prompt，自然段落形式。'''

GENERAL_GENERATION_PROMPT = '''你是指令优化专家。用户想要：{instruction}

【判断标准】
差 prompt："帮我处理这个" → 不知所云
好 prompt：明确who、what、why、how

【必须包含的要素】
□ 执行者是谁（AI/人类？什么角色？）
□ 具体要做什么（明确的动作和目标）
□ 上下文/背景（为什么需要做这件事）
□ 质量标准（什么样的结果算好？）
□ 约束条件（不能做什么？有什么限制？）

【禁止出现】
× 模糊的动作描述 → 必须明确具体
× 缺少上下文 → 说明为什么需要做这件事
× 缺少成功标准 → 说明什么样的结果算好

【输出格式】
直接输出优化后的 prompt，自然段落形式。'''

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
    is_direct: bool  # True = directly usable output

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

def load_config() -> dict:
    """Load LLM configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"llm_api_key": None, "llm_model": "gpt-4", "llm_endpoint": "https://api.openai.com/v1"}

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
# Analysis
# =============================================================================

def detect_language(text: str) -> str:
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_words = len([w for w in text.split() if w.isascii()])
    if chinese_chars > english_words * 1.5:
        return "zh"
    elif english_words > chinese_chars * 1.5:
        return "en"
    return "mixed"

def detect_task_complexity(instruction: str, instruction_type: str) -> str:
    """
    Determine if task is simple enough to complete directly.
    Simple = can be done in a few lines/sentences
    Medium = needs some structure but can still provide framework
    Complex = truly needs a template to fill out
    """
    words = instruction.split()
    
    # Short + action words = likely simple
    if len(words) <= 5 and instruction_type in ["code", "writing", "explanation"]:
        return "simple"
    
    # Explicit multi-step requests = complex
    if any(phrase in instruction for phrase in ["具体", "详细", "一步步", "step by step", "详细说明"]):
        return "complex"
    
    # Very short vague requests = simple (just do it directly)
    if len(words) <= 8:
        return "simple"
    
    # Medium length with multiple requirements = medium
    return "medium"

def detect_instruction_type(instruction: str) -> str:
    instruction_lower = instruction.lower()
    
    # Code
    code_keywords = [
        "code", "function", "script", "implement", "debug", "fix", "refactor",
        "api", "database", "sql", "python", "javascript", "java", "golang", "rust",
        "写代码", "函数", "调试", "算法", "排序", "缓存", "队列", "栈",
        "实现", "编程", "代码", "class", "method", "module",
        "lr", "cache", "queue", "stack", "hash", "tree", "graph",
        "登录", "注册", "用户", "验证", "auth", "login", "register",
        "斐波那契", "fibonacci", "quicksort", "mergesort"
    ]
    if any(word in instruction_lower for word in code_keywords):
        return "code"
    
    # Writing
    writing_keywords = [
        "write", "compose", "draft", "email", "letter", "article", "blog",
        "写", "文章", "邮件", "文案", "汇报", "报告", "总结", "摘要"
    ]
    if any(word in instruction_lower for word in writing_keywords):
        return "writing"
    
    # Explanation
    if any(word in instruction_lower for word in [
        "explain", "what", "how", "why", "difference", "解释", "说明", "是什么", "什么是", "为什么", "介绍"
    ]):
        return "explanation"
    
    # Question
    if "?" in instruction or "吗" in instruction or "？" in instruction:
        return "question"
    
    return "general"

def analyze_instruction(instruction: str) -> AnalysisResult:
    instruction_lower = instruction.lower()
    words = instruction_lower.split()
    lang = detect_language(instruction)
    instr_type = detect_instruction_type(instruction)
    complexity = detect_task_complexity(instruction, instr_type)
    
    missing = []
    assumptions = []
    risks = []
    
    # Complexity-based analysis
    if complexity == "simple":
        # For simple tasks, only note if something critical is missing
        if instr_type == "code":
            if "python" not in instruction_lower and "js" not in instruction_lower:
                assumptions.append("Language not specified")
        return {
            "missing": missing,
            "assumptions": assumptions,
            "risks": risks,
            "word_count": len(words),
            "instruction_type": instr_type,
            "language": lang,
            "task_complexity": complexity,
        }
    
    # Medium/Complex tasks - note what's missing
    if len(words) < 5:
        missing.append("Context too brief")
    
    if instr_type == "code":
        if not any(lang in instruction_lower for lang in ["python", "javascript", "java", "sql", "api"]):
            missing.append("Language/framework not specified")
    
    if instr_type == "writing":
        if instr_type == "writing" and not any(w in instruction_lower for w in ["收件", "recipient", "对象"]):
            assumptions.append("Audience not specified")
    
    return {
        "missing": missing,
        "assumptions": assumptions,
        "risks": risks,
        "word_count": len(words),
        "instruction_type": instr_type,
        "language": lang,
        "task_complexity": complexity,
    }

# =============================================================================
# Output Generation - Direct when possible
# =============================================================================

# DEPRECATED: These functions generated content directly instead of optimized prompts.
# Use generate_fallback_prompt() or generate_with_llm() instead.
# (generate_direct_code, generate_direct_explanation, generate_direct_writing removed)


# =============================================================================
# Fallback: Structured Prompt Templates (no LLM required)
# =============================================================================

# ---------------------------------------------------------------------------#
# Smart default inference engine for fallback prompts
# Maps common task keywords → reasonable default specifications
# ---------------------------------------------------------------------------#

# Code task inference map: (keywords) → (language, input, output, constraints)
_CODE_DEFAULTS = {
    # Sorting
    ("排序", "sort"): {
        "lang": "Python",
        "input": "整数数组，长度 1-100000，元素范围 0-10^9",
        "output": "升序排列的整数数组",
        "constraints": "平均时间复杂度 O(n log n)，空间复杂度 O(log n)",
        "boundary": "空数组返回空数组，大数组需避免栈溢出",
        "optional": "归并排序？堆排序？支持自定义比较函数？",
    },
    # Binary search
    ("二分", "binary search"): {
        "lang": "Python",
        "input": "有序整数数组 + 目标值",
        "output": "目标值的下标（不存在返回 -1）",
        "constraints": "时间复杂度 O(log n)",
        "boundary": "数组为空、目标不存在、单元素数组",
        "optional": "返回第一个/最后一个匹配位置？",
    },
    # Fibonacci / DP
    ("斐波那契", "fibonacci", "dp", "动态规划"): {
        "lang": "Python",
        "input": "整数 n（0 ≤ n ≤ 1000）",
        "output": "第 n 个斐波那契数",
        "constraints": "时间复杂度 O(n)，空间复杂度 O(1)（滚动数组）",
        "boundary": "n=0, n=1, n 特别大（考虑大数）",
        "optional": "记忆化递归？矩阵快速幂？",
    },
    # Login / Auth
    ("登录", "login", "登陆", "auth"): {
        "lang": "Python + Flask",
        "input": "用户名（字符串）+ 密码（字符串）",
        "output": "成功返回 JWT token，失败返回错误信息",
        "constraints": "密码需 bcrypt 哈希存储，JWT 有效期 24h",
        "boundary": "用户不存在、密码错误、账号锁定",
        "optional": "第三方登录（微信/Google）？注册功能？",
    },
    # API endpoint
    ("api", "接口", "endpoint", "rest"): {
        "lang": "Python + Flask / FastAPI",
        "input": "HTTP 请求参数（JSON/query/path）",
        "output": "JSON 响应 {code, message, data}",
        "constraints": "RESTful 规范，状态码正确，参数校验",
        "boundary": "参数缺失、格式错误、未授权访问",
        "optional": "分页？限流？文档（Swagger）？",
    },
    # Linked list
    ("链表", "linked list"): {
        "lang": "Python",
        "input": "链表节点值数组 + 操作类型",
        "output": "操作后的链表或结果值",
        "constraints": "需处理环检测、O(1) 空间（不允许修改节点）",
        "boundary": "空链表、单节点、环、循环链表",
        "optional": "反转链表？检测环？合并有序链表？",
    },
    # Tree / BST
    ("树", "tree", "bst", "二叉树"): {
        "lang": "Python",
        "input": "树的节点值列表（如层序数组）",
        "output": "遍历结果或操作结果",
        "constraints": "递归实现需防栈溢出，大树用迭代",
        "boundary": "空树、单节点、退化为链表",
        "optional": "前/中/后序遍历？层序遍历？求深度？",
    },
    # Hash / Dict
    ("哈希", "hash", "字典", "dict"): {
        "lang": "Python",
        "input": "键值对数组或字符串",
        "output": "哈希表或操作结果",
        "constraints": "处理哈希冲突（链地址法或开放地址）",
        "boundary": "键不存在、重复键、负载因子过大",
        "optional": "自定义哈希函数？扩容策略？",
    },
    # Graph
    ("图", "graph", "最短路径", "dijkstra"): {
        "lang": "Python",
        "input": "邻接表或邻接矩阵表示的图",
        "output": "最短路径长度或路径本身",
        "constraints": "时间复杂度 O((V+E) log V) for Dijkstra",
        "boundary": "图不连通、负权边、单源或多源",
        "optional": "BFS？Floyd-Warshall？拓扑排序？",
    },
    # Stack / Queue
    ("栈", "stack", "队列", "queue"): {
        "lang": "Python",
        "input": "操作序列或初始数据",
        "output": "操作后的栈/队列状态或顶部/队首元素",
        "constraints": "线程安全？容量限制？",
        "boundary": "空栈/空队列、溢出",
        "optional": "单调栈？循环队列？优先队列（堆）？",
    },
    # Database / SQL
    ("数据库", "sql", "db", "增删改查", "crud"): {
        "lang": "Python + SQL",
        "input": "表结构 + 查询条件或数据",
        "output": "查询结果或受影响的行数",
        "constraints": "防止 SQL 注入，使用参数化查询",
        "boundary": "表为空、结果为空、并发写入冲突",
        "optional": "事务？索引？分页查询？",
    },
    # Cache
    ("缓存", "cache", "lru"): {
        "lang": "Python",
        "input": "缓存容量 + 操作序列（get/put）",
        "output": "LRU 缓存操作结果",
        "constraints": "O(1) 时间复杂度",
        "boundary": "容量满、key 不存在、相同 key 重复访问",
        "optional": "LFU？TTL 过期？并发缓存？",
    },
    # String manipulation
    ("字符串", "string", "正则", "regex"): {
        "lang": "Python",
        "input": "输入字符串",
        "output": "处理后的字符串",
        "constraints": "Unicode 处理、大字符串高效",
        "boundary": "空字符串、特殊字符、超长输入",
        "optional": "正则表达式？KMP？马拉车算法？",
    },
}


def _infer_code_defaults(instruction: str) -> dict | None:
    """Try to find a matching default spec for the instruction."""
    instruction_lower = instruction.lower()
    for keywords, spec in _CODE_DEFAULTS.items():
        if any(kw in instruction_lower for kw in keywords):
            return spec
    return None


def generate_fallback_prompt(instruction: str, instruction_type: str) -> str:
    """
    不用 LLM 时，生成结构化的 prompt 文本模板。
    对于常见任务类型，智能推断合理的默认规范，减少用户填写负担。
    """
    if instruction_type == "code":
        defaults = _infer_code_defaults(instruction)
        if defaults:
            # Smart inferred fallback — has real content
            return f"""优化后的编程指令：

【任务】
用 {defaults['lang']} 实现{instruction}

【约束】
- 输入：{defaults['input']}
- 输出：{defaults['output']}
- 性能：{defaults['constraints']}
- 边界：{defaults['boundary']}

【可选补充】
- {defaults['optional']}"""
        else:
            # Generic fallback — still better than pure blanks
            return f"""优化后的编程指令：

【任务】
{instruction}

【约束】（以下请补充或确认）
- 输入规格：[数据类型、格式、范围]
- 输出规格：[数据类型、格式]
- 性能要求：[如有，如 时间复杂度 O(n log n)]
- 边界情况：[空输入、异常值、大规模数据]

【可选补充】
- 编程语言/框架偏好？
- 测试用例需要覆盖哪些场景？"""
    elif instruction_type == "writing":
        return f"""优化后的写作指令：

【任务】
{instruction}

【约束】
- 受众：[谁会读这篇？年龄/职业/背景]
- 写作目的：[说服/通知/解释/记录？]
- 语气风格：[正式/亲切/专业/轻松]
- 核心要点：[必须传达的 2-3 个要点]

【可选补充】
- 字数要求或篇幅限制？
- 结构偏好（总分总/清单/时间顺序）？"""
    elif instruction_type == "explanation":
        return f"""优化后的解释指令：

【任务】
{instruction}

【约束】
- 受众背景：[年龄、技术背景、认知水平]
- 解释深度：[扫盲科普/中等理解/深入专业]
- 核心概念：[1-3 个必须讲清楚的概念]

【可选补充】
- 需要什么类比/生活场景？
- 常见误解要提前澄清吗？"""
    else:
        return f"""优化后的指令：

【任务】
{instruction}

【约束】
- 执行者：[AI/专家/助手？]
- 目标：[明确要达到什么]
- 约束条件：[如有限制]

【可选补充】
- 质量标准：[什么样的结果算好？]
- 参考案例：[有的话可以提供]"""


# =============================================================================
# Main Generator
# =============================================================================

def generate_optimized_versions(instruction: str, count: int = 3) -> list[VersionResult]:
    """
    Generate optimized prompt versions for the given instruction.
    All versions output structured prompt TEXT (not direct content).
    """
    analysis = analyze_instruction(instruction)
    instr_type = analysis["instruction_type"]
    lang = analysis["language"]
    stripped = instruction.strip()

    versions = []

    # Version A: Structured template (baseline)
    template_a = generate_fallback_prompt(stripped, instr_type)
    versions.append({
        "type": "A (Template)",
        "description": "结构化 prompt 模板，引导补充关键信息",
        "template": template_a,
        "is_direct": False,
    })

    # Version B: More detailed structured prompt
    if instr_type == "code":
        if lang == "zh":
            template_b = f"""用 Python 实现以下编程任务：

{stripped}

具体要求：
- 输入：[描述输入格式，如 整数数组]
- 输出：[描述输出格式，如 排序后的整数数组]
- 边界情况：[如 空数组、重复元素、大规模数据]
- 性能要求：[如有，如 时间复杂度 O(n log n)]"""
        else:
            template_b = f"""Implement the following task:

{stripped}

Requirements:
- Input: [describe input format]
- Output: [describe output format]
- Edge cases: [describe]
- Performance: [if applicable]"""
    elif instr_type == "writing":
        if lang == "zh":
            template_b = f"""请写一篇关于以下主题的文章：

{stripped}

写作要求：
- 受众：[描述目标读者]
- 语气：[正式/亲切/专业/轻松]
- 核心信息：[列出 2-3 个必须传达的要点]
- 字数：[如有限制]"""
        else:
            template_b = f"""Write about the following topic:

{stripped}

Requirements:
- Audience: [describe]
- Tone: [formal/casual/professional]
- Key points: [list 2-3]
- Length: [if specified]"""
    elif instr_type == "explanation":
        if lang == "zh":
            template_b = f"""向以下受众解释：

{stripped}

要求：
- 受众背景：[年龄、技术背景、认知水平]
- 解释深度：[科普/中等/专业]
- 核心概念：[1-3 个必须讲清楚的概念]
- 类比场景：[用生活中的什么来类比]"""
        else:
            template_b = f"""Explain the following to your audience:

{stripped}

Requirements:
- Audience background: [describe]
- Depth: [popular/technical/expert]
- Core concepts: [1-3 must-understand concepts]
- Analogy: [real-life scenario to use]"""
    else:
        template_b = f"""请帮我完成以下任务：

{stripped}

具体要求：
- 执行者身份：[AI/专家/助手]
- 目标：[明确要达到什么]
- 约束条件：[如有]"""

    versions.append({
        "type": "B (Detailed)",
        "description": "更详细的 prompt 模板，明确关键要素",
        "template": template_b,
        "is_direct": False,
    })

    # Version C: Most complete structured prompt
    if instr_type == "code":
        if lang == "zh":
            template_c = f"""你是一位编程专家。请用 [编程语言] 实现以下功能：

【任务描述】
{stripped}

【输入规格】
- 数据类型：[如 整数、字符串、数组]
- 数据范围：[如 0-10000]
- 格式要求：[如 JSON/CSV]

【输出规格】
- 数据类型：
- 格式要求：

【功能要求】
- 核心逻辑：
- 边界情况处理：[空输入、异常值、大规模数据]

【非功能性要求】
- 时间复杂度：
- 空间复杂度：
- 代码风格：[如 PEP8]"""
        else:
            template_c = f"""You are a programming expert. Implement the following in [language]:

【Task】
{stripped}

【Input Spec】
- Data type:
- Range:
- Format:

【Output Spec】
- Data type:
- Format:

【Requirements】
- Core logic:
- Edge cases:

【Non-functional】
- Time complexity:
- Space complexity:"""
    elif instr_type == "writing":
        if lang == "zh":
            template_c = f"""你是一位专业写作顾问。请撰写以下内容：

【写作任务】
{stripped}

【受众分析】
- 目标读者：[年龄、职业、背景]
- 读者关心什么：
- 读者已知什么：

【写作目的】
- 核心信息：[必须传达的 1-2 句话]
- 期望读者采取的行动：[如有]

【风格要求】
- 语气：[正式/亲切/严肃/轻松]
- 语言：[中文/英文]
- 结构：[总分总/时间顺序/问题-解决方案]

【内容框架】
1. [开头：如何吸引读者]
2. [主体要点 1]
3. [主体要点 2]
4. [结尾：如何收尾]"""
        else:
            template_c = f"""You are a professional writing consultant. Write the following:

【Task】
{stripped}

【Audience】
- Target reader: [age, profession, background]
- What they care about:
- What they already know:

【Purpose】
- Core message:
- Desired action:

【Style】
- Tone: [formal/casual/serious/playful]
- Language: [Chinese/English]
- Structure: [conclusion-first/narrative/problem-solution]

【Content Framework】
1. [Opening hook]
2. [Point 1]
3. [Point 2]
4. [Closing]"""
    elif instr_type == "explanation":
        if lang == "zh":
            template_c = f"""你是一位擅长用通俗语言解释复杂概念的老师。请解释：

【解释主题】
{stripped}

【受众画像】
- 背景：[年龄、职业、技术敏感度]
- 已有哪些知识：
- 关心什么问题：

【解释深度】
- 层次：[科普扫盲/中等理解/深入分析]
- 重点概念：[1-3 个核心概念，必须讲清楚]

【解释策略】
- 类比场景：[用生活中的什么来类比]
- 讲解顺序：[从已知到未知]

【检验理解】
- 读者读完后能回答：[1-2 个检验问题]
- 常见误解：[提前澄清 1 个误区]"""
        else:
            template_c = f"""You are a teacher skilled at explaining complex concepts simply. Explain:

【Topic】
{stripped}

【Audience Profile】
- Background: [age, profession, tech savviness]
- Prior knowledge:
- Concerns:

【Depth】
- Level: [popular/technical/in-depth]
- Core concepts: [1-3 must-understand]

【Strategy】
- Analogy: [real-life scenario]
- Sequence: [known to unknown]

【Check Understanding】
- Key question reader can answer after:"""
    else:
        template_c = f"""请帮我完成以下任务：

【任务】
{stripped}

【背景】
- 执行者身份：
- 目标：
- 约束条件：

【质量标准】
- 什么样的结果算好："""

    versions.append({
        "type": "C (Complete)",
        "description": "最完整的 prompt 模板，覆盖所有关键维度",
        "template": template_c,
        "is_direct": False,
    })

    return versions[:count]

# =============================================================================
# Evaluation (Simplified)
# =============================================================================

def evaluate_version(version: VersionResult, analysis: AnalysisResult) -> EvaluationResult:
    """
    Content-based evaluation that actually differentiates quality.

    Scoring rules:
    - Has real content (not blank placeholder) → +2/section
    - Constraints are specific & quantified → +2/section
    - Language/framework is explicit → +1/section
    - Blank placeholder → -1/placeholder
    - Has optional/follow-up prompts → +0.5 (engagement signal)
    """
    template = version["template"]
    instr_type = analysis["instruction_type"]

    clarity_score = 5
    specificity_score = 5
    completeness_score = 5

    # ---- Blank placeholder penalty ----
    placeholder_count = template.count("：") + template.count(":")
    blank_phrases = [
        "[请补充]", "[描述]", "[填写]", "[如 有]", "[可选]",
        "[你决定]", "[未知]", "[自定义]", "______",
        "[数据类型、格式、范围]",  # generic code placeholder
        "[数据类型]", "[格式]", "[范围]",
    ]
    for phrase in blank_phrases:
        if phrase in template:
            blank_penalty = template.count(phrase)
            specificity_score -= blank_penalty
            completeness_score -= blank_penalty

    # ---- Content presence bonus ----
    # For code tasks: check for real input/output/constraint specs
    if instr_type == "code":
        # Has non-generic input spec
        if _has_real_content(template, ["输入", "input", "参数"]):
            specificity_score += 2
            completeness_score += 1
        # Has non-generic output spec
        if _has_real_content(template, ["输出", "output", "返回"]):
            specificity_score += 1
            completeness_score += 1
        # Has quantified constraints (O(n), 复杂度, 范围)
        if _has_quantified_constraint(template):
            specificity_score += 2
        # Has explicit language
        if _has_explicit_language(template, ["python", "javascript", "java", "go", "rust", "sql"]):
            specificity_score += 1
        # Has boundary handling
        if _has_real_content(template, ["边界", "edge", "空输入", "异常"]):
            completeness_score += 1
        # Has optional follow-up prompts
        if "【可选" in template or "【可选补充" in template or "optional" in template.lower():
            completeness_score += 0.5

    elif instr_type == "writing":
        if _has_real_content(template, ["受众", "读者", "audience"]):
            specificity_score += 2
            completeness_score += 1
        if _has_real_content(template, ["写作目的", "核心", "key point"]):
            specificity_score += 1
            completeness_score += 1
        if _has_real_content(template, ["语气", "tone", "风格"]):
            specificity_score += 1

    elif instr_type == "explanation":
        if _has_real_content(template, ["受众", "背景", "audience"]):
            specificity_score += 2
            completeness_score += 1
        if _has_real_content(template, ["解释深度", "depth", "层次"]):
            specificity_score += 1
        if _has_real_content(template, ["类比", "analogy"]):
            completeness_score += 1

    # ---- Clamp scores ----
    clarity_score = max(1, min(10, clarity_score))
    specificity_score = max(1, min(10, specificity_score))
    completeness_score = max(1, min(10, completeness_score))

    # ---- Overall score (weighted average) ----
    overall = round(
        clarity_score * 0.25 + specificity_score * 0.40 + completeness_score * 0.35,
        2
    )

    # ---- Grade ----
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
        # Check surrounding 20 chars for generic placeholders
        start = max(0, idx - 5)
        end = min(len(template), idx + 20)
        snippet = template[start:end]
        # If snippet contains generic placeholder, count as empty
        for ph in generic_phrases:
            if ph in snippet:
                return False
        return True
    return False


def _has_quantified_constraint(template: str) -> bool:
    """Check if template has quantified constraints like O(n), ranges, limits."""
    quantified_patterns = [
        r"O\([^)]+\)",       # O(n log n), O(n^2)
        r"\d+\s*-\s*\d+", # 1-100000
        r"\d+\s*个",        # 100万个
        r"\d+k",             # 10k, 100k
        r"\d+M",             # 1M
        r"时间复杂度",
        r"空间复杂度",
        r"\d+\s*小时",
        r"\d+\s*分钟",
        r"\d+\s*秒",
    ]
    import re
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
        # For simple tasks, prefer direct output
        for i, eval_result in enumerate(evaluations):
            if eval_result["overall"] >= 8.0:
                return i
    else:
        # For complex tasks, use framework/template
        for i, eval_result in enumerate(evaluations):
            if eval_result["overall"] >= 6.0:
                return i
    
    return 0

# =============================================================================
# LLM Generation
# =============================================================================

def generate_with_llm(instruction: str, api_key: str = None, model: str = "gpt-4",
                      endpoint: str = "https://api.openai.com/v1/chat/completions",
                      instruction_type: str = None) -> Optional[str]:
    """
    Use LLM with category-specific prompt to generate optimized prompt.
    Requires user to provide their own API key.
    Falls back to None if API key not provided or call fails.
    """
    if not api_key:
        return None

    # 根据类型选择生成 prompt
    if instruction_type == "code":
        system_prompt = "你是一个编程专家，擅长生成高质量的编程指令。"
        user_prompt = CODE_GENERATION_PROMPT.format(instruction=instruction)
    elif instruction_type == "writing":
        system_prompt = "你是一个写作专家，擅长生成清晰的写作指令。"
        user_prompt = WRITING_GENERATION_PROMPT.format(instruction=instruction)
    elif instruction_type == "explanation":
        system_prompt = "你是一位老师，擅长用通俗易懂的方式解释复杂概念。"
        user_prompt = EXPLANATION_GENERATION_PROMPT.format(instruction=instruction)
    else:
        system_prompt = "你是一个指令优化专家。"
        user_prompt = GENERAL_GENERATION_PROMPT.format(instruction=instruction)

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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
            },
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def optimize_with_llm(instruction: str, instruction_type: str = None) -> OptimizationResult:
    """Optimize using LLM when API key is configured."""
    cfg = load_config()
    api_key = cfg.get("llm_api_key")
    model = cfg.get("llm_model", "gpt-4")
    endpoint = cfg.get("llm_endpoint", "https://api.openai.com/v1/chat/completions")

    analysis = analyze_instruction(instruction)
    instr_type = instruction_type or analysis["instruction_type"]

    # No API key: fall back to structured template
    if not api_key:
        generated = generate_fallback_prompt(instruction, instr_type)
        version: VersionResult = {
            "type": "Fallback (No API)",
            "description": "结构化模板（未配置 API key，使用内置模板）",
            "template": generated,
            "is_direct": False,
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
        }

    generated = generate_with_llm(instruction, api_key, model, endpoint, instr_type)
    # LLM call failed: fall back to structured template
    if not generated:
        generated = generate_fallback_prompt(instruction, instr_type)
        version = {
            "type": "Fallback (LLM Failed)",
            "description": "结构化模板（LLM 调用失败，使用内置模板）",
            "template": generated,
            "is_direct": False,
        }
    else:
        version = {
            "type": "LLM Optimized",
            "description": "LLM 生成的优化 prompt（需配置 API key）",
            "template": generated,
            "is_direct": False,
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
    }


# =============================================================================
# Main Pipeline
# =============================================================================

def optimize(instruction: str, use_llm: bool = False) -> OptimizationResult:
    """
    Main optimization pipeline. Set use_llm=True to prefer LLM generation.
    
    Always outputs "优化后的 prompt 文本" (optimized prompt text),
    not direct content (code/email/explanation).
    """
    analysis = analyze_instruction(instruction)
    instr_type = analysis["instruction_type"]

    if use_llm:
        # LLM path: generate truly optimized prompt
        return optimize_with_llm(instruction, instruction_type=instr_type)
    else:
        # Fallback path: generate structured prompt template
        generated = generate_fallback_prompt(instruction, instr_type)
        version: VersionResult = {
            "type": "Fallback (Structured)",
            "description": "结构化 prompt 模板，无需 LLM API",
            "template": generated,
            "is_direct": False,
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
