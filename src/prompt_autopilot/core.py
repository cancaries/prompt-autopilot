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

# =============================================================================
# LLM-Enhanced Prompt Generation Prompts
# =============================================================================

PROMPT_GENERATION_SYSTEM = '''你是一个专业的 prompt 工程专家，擅长将模糊的用户需求转化为完整、精确的 prompt。

你的工作哲学：
- 不要问用户问题，直接推理并填充合理的默认值
- 宁可多做，不要少做
- 用户说"做个登录功能"，你要想到：注册、密码找回、第三方登录、JWT、数据库、安全...
- 深度推理比规则匹配好 100 倍'''

CODE_GENERATION_PROMPT = '''你是一个 prompt 工程专家。用户想要：

{instruction}

请深度思考并生成：

1. 【意图理解】用户真正想要的是什么？不是字面，而是背后目的。"做个登录功能" 背后可能是：一个需要用户认证的系统，可能是 Web/APP/后端服务的一部分。

2. 【盲点发现】用户没想到但很重要的东西有哪些？
   例如：
   - "做个登录" → 可能需要：注册功能、密码找回、第三方登录（微信/Google）、会话管理、JWT/ Session、数据库设计、密码加密（bcrypt）、防暴力破解...
   - "写个排序" → 可能需要：数据规模、是否需要稳定排序、是否需要自定义比较、空间限制...

3. 【优化后的 prompt】生成一个完整的、专业的 prompt，包含：
   - 清晰的任务描述（用一句话描述你要 AI 做什么）
   - 具体的约束条件（输入/输出/性能/安全等）
   - 相关的背景信息（项目背景、使用场景、目标用户）
   - 质量标准（什么样的结果算好）
   - 边界情况（如何处理异常）

4. 【before/after】给出优化前后的对比

直接输出优化后的 prompt 和对比，不要解释你的思考过程。
用自然段落组织，不要分点列举。'''

WRITING_GENERATION_PROMPT = '''你是写作专家，擅长生成能产生好内容的写作指令。

用户想要：{instruction}

请生成"优化后的写作 prompt"，包含：
1. 受众是谁（年龄/职业/阅读习惯）
2. 写作目的（说服/通知/娱乐/教育）
3. 语气风格（正式/轻松/专业/亲切）
4. 文章结构（开头/主体/结尾的要求）
5. 字数要求（如有）
6. 禁止事项（不要写什么）

生成"优化后的 prompt"，不要直接写文章内容。'''

EXPLANATION_GENERATION_PROMPT = '''你是一位老师，擅长把复杂概念讲得通俗易懂。

用户想要理解：{instruction}

请生成一个"优化后的 prompt"，让 AI 能够给出好的解释。

优化后的 prompt 应该包含：
1. 受众是谁（年龄/背景/知识水平）
2. 解释深度（科普/专业/深入）
3. 需要讲清楚的核心概念（1-3个）
4. 生活类比/场景（必须有一个身边的例子）
5. 避免的误区（常见误解）

生成"优化后的 prompt"，而不是直接解释。'''

GENERAL_GENERATION_PROMPT = '''你是一个 prompt 工程专家。用户想要：

{instruction}

请深度思考并生成：

1. 【意图理解】用户真正想完成的是什么？不是字面，而是背后目的。

2. 【盲点发现】用户没想到但很重要的东西有哪些？

3. 【优化后的 prompt】生成一个完整的、专业的 prompt，包含：
   - 清晰的任务描述
   - 具体的约束条件
   - 相关的背景信息
   - 质量标准

4. 【before/after】对比

直接输出，不要解释你的思考过程。'''

SELF_REFLECTION_PROMPT = '''你是 prompt-autopilot 的创造者。审视当前系统：

当前系统输出：
{recent_output}

请深度反思：
1. 这个输出专业吗？哪里不够好？
2. 对标 linshenkx/prompt-optimizer，我们差在哪里？
3. 如果你是用户，你会满意吗？为什么？
4. 最需要改进的一个点是什么？

诚实、严格地自我批判。直接输出反思结果。'''

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

def get_llm_config() -> dict:
    """Get LLM config with priority: env vars > config file > defaults.
    
    Environment variables:
    - PROMPT_AUTOPILOT_API_KEY: LLM API key
    - PROMPT_AUTOPILOT_MODEL: Model name (default: gpt-4)
    - PROMPT_AUTOPILOT_ENDPOINT: API endpoint URL
    """
    cfg = {}
    # Load from config file as base (only keys not in env)
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
    # Ensure defaults
    cfg.setdefault("llm_api_key", None)
    cfg.setdefault("llm_model", "gpt-4")
    cfg.setdefault("llm_endpoint", "https://api.openai.com/v1/chat/completions")
    return cfg


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
    
    # Code review / code analysis (check BEFORE generic code keywords)
    code_review_keywords = [
        "review", "review代码", "代码review", "cr", "代码审查", "代码分析",
        "性能review", "review这段", "代码审查", "review一下", "review下"
    ]
    if any(word in instruction_lower for word in code_review_keywords):
        return "code_review"
    
    # Test generation (check BEFORE writing keywords)
    test_generation_keywords = [
        "单元测试", "unit test", "测试用例", "写测试", "test case",
        "pytest", "jest", "testing", "测试代码"
    ]
    if any(word in instruction_lower for word in test_generation_keywords):
        return "test_generation"
    
    # Code (generic)
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
    
    # ---- Email sub-type detection (before generic writing) ----
    # More specific → less specific order to avoid false positives
    if any(w in instruction_lower for w in ["拒绝", "谢绝", "无法录用", "面试结果", "不录用"]):
        return "rejection_email"
    if any(w in instruction_lower for w in ["道歉", "sorry", "apologize", "致歉"]):
        return "apology_email"
    if any(w in instruction_lower for w in ["周报", "月报", "日报", "进度汇报", "项目报告"]):
        return "report_email"
    if any(w in instruction_lower for w in ["通知", "notification", "告知", "通报"]):
        return "notification_email"
    if any(w in instruction_lower for w in ["投诉", "complaint", "客户投诉", "申诉"]):
        return "complaint_email"
    
    # Writing (generic)
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
    # JSON array / list processing
    ("json", "数组", "list"): {
        "lang": "Python",
        "input": "JSON 数组或 Python 列表",
        "output": "数值（平均值）",
        "constraints": "时间复杂度 O(n)，空间复杂度 O(1)",
        "boundary": "空数组返回 0 或空列表",
        "optional": "支持嵌套数组？支持过滤条件？",
    },
    # Square / power
    ("平方", "square", "幂", "power"): {
        "lang": "Python",
        "input": "数值或列表",
        "output": "数值或列表（平方）",
        "constraints": "时间复杂度 O(n)",
        "boundary": "负数平方、正负数混合列表",
        "optional": "支持复数？支持矩阵？",
    },
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


def generate_inferred_prompt_via_llm(instruction: str, instruction_type: str) -> str | None:
    """
    When rule-based matching fails, use LLM to infer context and fill a structured template.
    Returns None if no API key is available.
    """
    cfg = get_llm_config()
    api_key = cfg.get("llm_api_key")
    if not api_key:
        return None

    model = cfg.get("llm_model", "gpt-4")
    endpoint = cfg.get("llm_endpoint", "https://api.openai.com/v1/chat/completions")

    type_labels = {
        "code": "编程/算法任务",
        "code_review": "代码审查/分析",
        "test_generation": "测试代码生成",
        "writing": "写作任务",
        "explanation": "解释/说明",
        "general": "通用任务",
    }
    label = type_labels.get(instruction_type, "通用任务")

    llm_prompt = f"""用户想要完成以下{label}，但描述比较模糊：

{instruction}

请根据你的深度推理能力，填充以下结构化模板（根据任务类型选择合适的章节）：

## 🎯 任务
[根据 instruction 推断的精确任务描述]

## 📥 输入
- 类型：[推断的数据类型]
- 范围：[推断的数据规模/范围]
- 示例：[一个具体示例]

## 📤 输出
- 类型：[推断的输出类型]
- 示例：[对应的输出示例]

## ⚡ 性能要求（如适用）
- 时间复杂度：[如有要求]
- 空间复杂度：[如有要求]

## 🛡️ 边界情况
- [从 instruction 推断的边界情况]

直接输出填充好的模板内容，不要解释。"""

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
                    {"role": "system", "content": "你是一个专业的 prompt 工程专家。直接输出填充好的模板，不要解释你的思考过程。"},
                    {"role": "user", "content": llm_prompt},
                ],
                "temperature": 0.3,
            },
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def generate_fallback_prompt(instruction: str, instruction_type: str) -> str:
    """
    不用 LLM 时，生成结构化的 prompt 文本模板。
    对于常见任务类型，智能推断合理的默认规范，减少用户填写负担。
    绝不输出空白占位符，所有推断必须有实际值。
    当规则匹配失败且 LLM API key 可用时，调用 LLM 推断并填充模板。
    """
    # ---- Auto-fill tone/audience from instruction for writing tasks ----
    def _extract_tone(instruction: str) -> str:
        instruction_lower = instruction.lower()
        tones = []
        if "专业" in instruction_lower:
            tones.append("专业")
        if any(w in instruction_lower for w in ["友善", "友好"]):
            tones.append("友善")
        if any(w in instruction_lower for w in ["轻松", "活泼"]):
            tones.append("轻松")
        if "正式" in instruction_lower:
            tones.append("正式")
        if "亲切" in instruction_lower:
            tones.append("亲切")
        return "".join(tones) if tones else "[根据受众和场景选择]"

    def _extract_audience(instruction: str) -> str:
        if any(w in instruction.lower() for w in ["工程师", "developer", "程序员", "技术"]):
            return "工程师/技术人员"
        if any(w in instruction for w in ["老板", "管理层", "manager"]):
            return "管理层/决策者"
        if any(w in instruction for w in ["客户", "客户"]):
            return "客户"
        if any(w in instruction for w in ["用户", "使用者"]):
            return "终端用户"
        return "[描述读者背景、职业、关注点]"

    if instruction_type == "code_review":
        return f"""## 🎯 任务
审查以下代码：{instruction}

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
为以下代码编写单元测试：{instruction}

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
        defaults = _infer_code_defaults(instruction)
        if defaults:
            # Smart inferred fallback — has real content, no placeholders
            lang = defaults['lang']
            task_desc = instruction

            # Build performance section
            perf_parts = []
            if '时间复杂度' in defaults.get('constraints', ''):
                perf_parts.append(defaults['constraints'])
            if '边界' in defaults and defaults['boundary']:
                perf_parts.append(f"边界：{defaults['boundary']}")

            # Build boundary section from defaults
            boundary_map = {
                ('排序', 'sort'): "- 空数组 → 返回 []\n- 单元素 → 返回 [x]\n- 重复元素 → 保持相对顺序",
                ('登录', 'login', '登陆', 'auth'): "- 用户不存在 → 返回明确错误信息\n- 密码错误 → 提示「密码错误」，不暴露具体原因\n- 账号锁定 → 锁定后需管理员解锁或等待 30 分钟",
                ('斐波那契', 'fibonacci', 'dp', '动态规划'): "- n = 0 → 返回 0\n- n = 1 → 返回 1\n- n 特别大 → 使用大数运算或矩阵快速幂",
                ('二分', 'binary search'): "- 数组为空 → 返回 -1\n- 目标不存在 → 返回 -1\n- 单元素数组 → 直接比较",
            }
            for kws, boundary_text in boundary_map.items():
                if any(kw in instruction.lower() for kw in kws):
                    boundary = boundary_text
                    break
            else:
                boundary = defaults.get('boundary', '请补充边界情况处理')

            _default_constraints = '时间复杂度：O(n)\n- 空间复杂度：O(1)'
            perf_section = f"- {defaults.get('constraints', _default_constraints)}"

            # Detect if this is a sorting-like task
            is_sorting = any(kw in instruction.lower() for kw in ('排序', 'sort', 'quicksort', 'mergesort'))
            if is_sorting:
                return f"""## 🎯 任务
用 {lang} 实现快速排序算法

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
{boundary}"""

            # Detect login/auth
            is_login = any(kw in instruction.lower() for kw in ('登录', 'login', '登陆', 'auth'))
            if is_login:
                return f"""## 🎯 任务
用 {lang} 实现用户认证系统，支持登录

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
{boundary}"""

            # Generic code fallback with real defaults
            return f"""## 🎯 任务
用 {lang} 实现：{task_desc}

## 📥 输入
- {defaults.get('input', '由调用方提供')}

## 📤 输出
- {defaults.get('output', '根据任务目标确定')}

## ⚡ 性能要求
{perf_section}

## 🛡️ 边界情况
{boundary}"""
        else:
            # Try LLM inference when rule-based matching fails
            llm_result = generate_inferred_prompt_via_llm(instruction, instruction_type)
            if llm_result:
                return llm_result
            # Generic fallback — still has some structure, no blank [请补充]
            return f"""## 🎯 任务
用 Python 实现：{instruction}

## 📥 输入
- 类型：[请描述输入数据类型和格式]
- 范围：[请描述数据范围或规模]
- 示例：[提供一个具体输入示例]

## 📤 输出
- 类型：[请描述输出数据类型和格式]
- 示例：[提供对应的输出示例]

## ⚡ 性能要求
- 时间复杂度：[如有要求，如 O(n log n)]
- 空间复杂度：[如有要求]

## 🛡️ 边界情况
- 空输入 →
- 异常值 →
- 大规模数据 →"""
    # ---- Email-specific sub-types ----
    elif instruction_type == "rejection_email":
        return f"""## 🎯 任务
写一封拒绝候选人的邮件

## 📧 邮件结构
1. **称呼**（感谢投递，如"尊敬的张三同学"）
2. **开场**（简短感谢参加面试）
3. **正文**（面试反馈，1-2 句正面评价）
4. **拒绝**（委婉表达"暂不推进"，可选具体原因）
5. **祝福**（祝愿职业发展）
6. **签名**（发件人姓名、职位、日期）

## ✍️ 语气要求
- 专业友善，不伤人
- 简洁明了，不留模糊希望
- 不用"很遗憾""抱歉"等过度负面词

## ✅ 参考模板
尊敬的 [姓名]：

感谢您参加 [公司名称] [职位名称] 的面试。

[简短正面评价，如：您的技术能力和项目经验给我们留下了深刻印象。]

经过慎重考虑，我们决定暂不推进您的申请。[可选原因：目前团队需求不匹配 / 已有更合适的候选人]

再次感谢您的时间和努力。祝愿您未来职业发展顺利！

此致
[姓名]
[职位]
[日期]"""

    elif instruction_type == "apology_email":
        return f"""## 🎯 任务
写一封道歉邮件

## 📧 邮件结构
1. **称呼**
2. **承认问题**（简明说明发生了什么问题）
3. **说明原因**（如不适合展开，可简略带过）
4. **道歉**（真诚、具体）
5. **补救措施**（打算如何弥补或防止再犯）
6. **承诺/邀请反馈**
7. **签名**

## ✍️ 语气要求
- 真诚，不找借口，不过度解释
- 具体说明对什么道歉
- 提出切实补救措施
- 不要用"但是""不过"等转折词削弱道歉诚意

## ✅ 参考模板
尊敬的 [收件人]：

就 [具体事件/问题] 而言，我们对此给您带来的不便深表歉意。

[简要说明发生了什么，及原因（如合适）]

我们对这次的问题负全部责任，对此深感抱歉。

为弥补此次失误，我们[将采取的补救措施，如：全额退款 / 已安排重新发货 / 已加强内部审核流程]。

如您有任何进一步的疑问或建议，请随时与我们联系。

此致
[姓名]
[职位]
[日期]"""

    elif instruction_type == "notification_email":
        return f"""## 🎯 任务
写一封团队/组织内部通知邮件

## 📧 邮件结构
1. **标题**（简洁明了，一眼看出内容）
2. **称呼**（如"各位同事""团队成员"等）
3. **正文**（通知内容，重要信息靠前）
   - 事件/决定说明
   - 关键信息（时间/地点/人员）
   - 原因/背景（如需要）
4. **行动要求**（需要收件人做什么，清晰列出）
5. **联系方式**（如有疑问联系谁）
6. **签名**

## ✍️ 语气要求
- 清晰、准确、不含糊
- 重要信息加粗或列点
- 行动要求明确（谁、何时、如何）
- 正式但不冷漠

## ✅ 参考模板
**主题：[通知标题，如"关于 Q2 季度会议的通知"]**

各位同事：

[通知核心内容，1-2 段说明：什么事、时间、地点、谁参加]

**请注意：**
- [关键要点 1]
- [关键要点 2]

如有疑问，请联系 [联系人姓名]（[联系方式]）。

感谢大家的配合！

[姓名]
[部门/职位]
[日期]"""

    elif instruction_type == "complaint_email":
        return f"""## 🎯 任务
回复一封客户投诉邮件

## 📧 邮件结构
1. **称呼**（感谢来信，表明收到）
2. **确认问题**（复述客户投诉的核心问题，显示理解）
3. **道歉**（对造成的不便真诚道歉）
4. **调查说明**（我们已采取/正在采取的措施）
5. **解决方案**（具体补救/赔偿方案）
6. **预防承诺**（如何防止类似问题再发生）
7. **邀请反馈**（是否满意解决方案）
8. **签名**

## ✍️ 语气要求
- 真诚倾听，不防御
- 不推卸责任
- 解决方案具体、可操作
- 表达继续服务的诚意

## ✅ 参考模板
尊敬的 [客户姓名]：

感谢您向我们反馈 [问题描述，如"订单延迟交付的问题"]。

我们已确认问题：[复述客户投诉的核心]

对此给您带来的不便，我们深表歉意。

我们已经 [已采取的措施，如：紧急补发商品 / 退还运费 / 给予补偿优惠券]。

为防止类似问题再次发生，我们 [预防措施，如：已升级库存管理系统 / 已与物流公司沟通加强时效]。

如果您对以上解决方案有任何疑问，欢迎随时联系我们。

此致
[姓名]
[职位]
[公司名称]
[日期]"""

    elif instruction_type == "report_email":
        return f"""## 🎯 任务
写一份工作周报/月报

## 📧 周报/报告结构
1. **标题**（如"[姓名] [2024-01-01 ~ 2024-01-05] 周报"）
2. **本周完成**（列出 3-5 项已完成任务，含结果/产出）
3. **进行中**（正在推进的任务及当前进度 %）
4. **下周计划**（预计开展的工作）
5. **风险/阻塞**（如有，列出阻碍和需要的支持）
6. **数据指标**（如有 KPI，数据可视化或列点）

## ✍️ 风格要求
- 结果导向（不说"做了什么"，说"做成了什么"）
- 量化成果（完成 5 个功能 / 提升转化率 10%）
- 简洁，每条不超过 2 行
- 诚实报告风险，不报喜不报忧

## ✅ 参考模板
**主题：[姓名] 周报 | [日期区间]**

各位好，以下是本周工作汇报：

**✅ 本周完成**
- [任务 1] — [结果/产出，如"完成用户登录模块开发，已上线"]
- [任务 2] — [结果]
- [任务 3] — [结果]

**🔄 进行中**
- [任务 A] — 当前进度 60%，预计 [日期] 完成
- [任务 B] — 等待 [阻塞因素]，需要 [支持]

**📅 下周计划**
- [计划 1]
- [计划 2]

**⚠️ 风险/需要支持**
- [风险描述 + 需要的帮助]

[姓名] | [部门] | [日期]"""

    elif instruction_type == "writing":
        tone = _extract_tone(instruction)
        audience = _extract_audience(instruction)
        return f"""## 🎯 写作任务
{instruction}

## 👥 受众
- 目标读者：{audience}
- 读者关心什么：[他们最在意什么]
- 读者已知什么：[他们对主题了解多少]

## 🎯 核心信息
- 主要观点：[最想传达的 1-2 句话]
- 期望行动：[读完希望读者做什么？]

## 🎨 风格要求
- 语气：{tone}
- 语言：[中文/英文]
- 篇幅：[字数或段落数要求]

## 🏗️ 结构
- 开头：[如何吸引读者]
- 主体：[核心要点 1-2 个]
- 结尾：[如何收尾，行动号召]"""
    elif instruction_type == "explanation":
        return f"""## 🎯 解释任务
{instruction}

## 👤 受众画像
- 年龄/职业：[目标读者]
- 技术背景：[他们对主题了解多少]
- 关心什么：[最想了解什么]

## 🔬 解释深度
- 层次：[扫盲科普/中等理解/深入专业]
- 核心概念：[1-3 个必须讲清楚的概念]

## 🧩 讲解策略
- 类比场景：[用生活中的什么来类比]
- 讲解顺序：[从已知到未知]

## ✅ 检验理解
- 读者读完后能回答：[1-2 个检验问题]
- 常见误解：[提前澄清 1 个误区]"""
    else:
        return f"""## 🎯 任务
{instruction}

## 📋 执行要求
- 执行者：[AI / 专家 / 助手？]
- 目标：[明确要达到什么]
- 约束条件：[如有]

## ✅ 质量标准
- 什么样的结果算好：[描述标准]
- 参考案例：[有的话提供]"""


# =============================================================================
# Main Generator
# =============================================================================

def generate_optimized_versions(instruction: str, count: int = 3) -> list[VersionResult]:
    """
    Generate optimized prompt versions for the given instruction.
    All versions output structured prompt TEXT (not direct content).
    Uses generate_fallback_prompt for all email/writing subtypes to ensure
    proper specialized templates are used (rejection_email, notification_email, etc.).
    """
    analysis = analyze_instruction(instruction)
    instr_type = analysis["instruction_type"]
    lang = analysis["language"]
    stripped = instruction.strip()

    # Email subtypes use generate_fallback_prompt for ALL versions since
    # it already has complete, well-structured templates for each email type
    EMAIL_TYPES = {
        "rejection_email", "notification_email", "complaint_email",
        "apology_email", "report_email"
    }
    SPECIALIZED_TYPES = EMAIL_TYPES | {"writing", "explanation", "code"}

    versions = []

    # Version A: Structured template (baseline)
    template_a = generate_fallback_prompt(stripped, instr_type)
    versions.append({
        "type": "A (Template)",
        "description": "结构化 prompt 模板，引导补充关键信息",
        "template": template_a,
        "is_direct": False,
    })

    if count == 1:
        return versions

    # Version B: For specialized types, use fallback with more specificity
    # For generic types, use a more detailed version
    if instr_type in EMAIL_TYPES or instr_type == "writing":
        # Email/writing: fallback template is already comprehensive; add a coaching note
        template_b = generate_fallback_prompt(stripped, instr_type)
        # Add coaching section for more detail
        template_b += """

## 🔍 进阶要点（Version B 补充）
- 语气微调：[根据收件人身份调整，如 面试官/客户/上级]
- 情感控制：[避免过度负面或过度热情]
- 行动号召：[明确读者下一步该做什么]"""
    elif instr_type == "code":
        defaults = _infer_code_defaults(instruction) or {}
        lang_default = defaults.get('lang', '[编程语言，如 Python]')
        perf = defaults.get('constraints', '时间复杂度：O(n)\n- 空间复杂度：O(1)')
        boundary = defaults.get('boundary', '请补充边界情况处理')
        is_sorting = any(kw in instruction.lower() for kw in ('排序', 'sort', 'quicksort', 'mergesort'))
        if is_sorting:
            template_b = f"""## 🎯 任务
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
        elif any(kw in instruction.lower() for kw in ('登录', 'login', '登陆', 'auth')):
            template_b = f"""## 🎯 任务
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
        else:
            template_b = f"""## 🎯 任务
用 {lang_default} 实现：{stripped}

## 📥 输入
- {defaults.get('input', '由调用方提供')}

## 📤 输出
- {defaults.get('output', '根据任务目标确定')}

## ⚡ 性能要求
- {perf}

## 🛡️ 边界情况
{boundary}"""
    elif instr_type == "explanation":
        if lang == "zh":
            template_b = f"""## 🎯 解释任务
{stripped}

## 👤 受众画像
- 年龄/职业：[目标读者]
- 技术背景：[他们对主题了解多少]
- 关心什么：[最想了解什么]

## 🔬 解释深度
- 层次：[扫盲科普/中等理解/深入专业]
- 核心概念：[1-3 个必须讲清楚的概念]

## 🧩 讲解策略
- 类比场景：[用生活中的什么来类比]
- 讲解顺序：[从已知到未知]

## ✅ 检验理解
- 读者读完后能回答：[1-2 个检验问题]
- 常见误解：[提前澄清 1 个误区]"""
        else:
            template_b = f"""## 🎯 任务
Explain: {stripped}

## 👤 Audience
- Background: [target reader]
- Prior knowledge: [their level]
- Concerns: [what they want to know]

## 🔬 Depth
- Level: [popular/technical/expert]
- Core concepts: [1-3 must-understand]

## 🧩 Strategy
- Analogy: [real-life scenario]
- Sequence: [known to unknown]

## ✅ Check
- Question reader can answer after:"""
    else:
        template_b = f"""## 🎯 任务
{stripped}

## 📋 执行要求
- 执行者身份：[AI / 专家 / 助手]
- 目标：[明确要达到什么]
- 约束条件：[如有]

## ✅ 质量标准
- 什么样的结果算好：[描述标准]
- 参考案例：[有的话提供]"""

    versions.append({
        "type": "B (Detailed)",
        "description": "更详细的 prompt 模板，明确关键要素",
        "template": template_b,
        "is_direct": False,
    })

    if count <= 2:
        return versions

    # Version C: Most complete structured prompt
    if instr_type in EMAIL_TYPES:
        # Email types: use a more comprehensive version with AI persona
        template_c = generate_fallback_prompt(stripped, instr_type)
        template_c = template_c.replace(
            "## 🎯 任务",
            "## 🎯 任务\n你是一位专业商务沟通顾问，擅长撰写得体、有效的电子邮件。"
        )
        template_c += """

## 💡 高级技巧（Version C 进阶）
- 邮件主题行：[如何写一个让人想点开的邮件标题]
- 开头句式：[如何开头让人想读下去]
- 收尾句式：[如何收尾给读者正面印象]
- 长度把控：[一般不超过 5 段]"""
    elif instr_type == "code":
        defaults = _infer_code_defaults(instruction) or {}
        lang_default = defaults.get('lang', '[编程语言，如 Python]')
        is_sorting = any(kw in instruction.lower() for kw in ('排序', 'sort', 'quicksort', 'mergesort'))
        if is_sorting:
            template_c = f"""你是一位编程专家。请用 {lang_default} 实现以下功能：

【任务描述】
{stripped}

【输入规格】
- 数据类型：整数数组
- 数据范围：长度 1-100000，元素 0-10^9
- 格式要求：JSON 数组

【输出规格】
- 数据类型：整数数组（升序）
- 格式要求：JSON 数组

【功能要求】
- 核心逻辑：使用快速排序（原地分区）
- 边界情况处理：空数组、单元素、重复元素、大数组

【非功能性要求】
- 时间复杂度：O(n log n)（平均），O(n²)（最坏避免措施：随机主元）
- 空间复杂度：O(log n)（递归栈）
- 代码风格：PEP8，类型注解

【测试用例】
- [] → []
- [1] → [1]
- [3, 3, 1, 2, 1] → [1, 1, 2, 3, 3]
- [10, 9, 8, 7, 6] → [6, 7, 8, 9, 10]"""
        else:
            _perf_default = defaults.get('constraints', f'- 时间复杂度：O(n){chr(10)}- 空间复杂度：O(1)')
            template_c = f"""你是一位编程专家。请用 {lang_default} 实现以下功能：

【任务描述】
{stripped}

【输入规格】
- 数据类型：{defaults.get('input', '由调用方提供')}
- 数据范围：[根据任务推断]
- 格式要求：[如 JSON/CSV/API]

【输出规格】
- 数据类型：{defaults.get('output', '根据任务目标确定')}
- 格式要求：[根据任务推断]

【功能要求】
- 核心逻辑：[描述核心算法/逻辑]
- 边界情况处理：{defaults.get('boundary', '空输入、异常值、大规模数据')}

【非功能性要求】
{_perf_default}

【测试用例】
- [正常用例]
- [边界用例]
- [异常用例]"""
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
- 常见误解：[提前澄清 1 个误区]

【扩展阅读】
- 相关概念：[可延伸的 1-2 个相关概念]
- 推荐资源：[如书籍/视频/文章]"""
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
        template_c = f"""## 🎯 任务
{stripped}

## 📋 执行要求
- 执行者身份：[AI / 专家 / 助手]
- 目标：[明确要达到什么]
- 约束条件：[如有]

## ✅ 质量标准
- 什么样的结果算好：[描述标准]
- 参考案例：[有的话提供]"""

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
    # Only penalize truly blank/uninformative placeholders, not bracket-style template fields
    # "[姓名]" is an intentional template field, NOT a blank placeholder
    truly_blank_phrases = [
        "[请补充]", "[描述]", "[填写]", "[如 有]", "[可选]",
        "[你决定]", "[未知]", "[自定义]", "______",
        "[数据类型、格式、范围]",
        "[数据类型]", "[格式]", "[范围]",
    ]
    for phrase in truly_blank_phrases:
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

    # ---- Email subtype scoring (rejection, notification, complaint, apology, report) ----
    elif instr_type in ("rejection_email", "notification_email", "complaint_email",
                        "apology_email", "report_email"):
        # Has complete email structure (称呼, 开场, 正文, ...)
        if _has_real_content(template, ["称呼"]):
            completeness_score += 1
        if _has_real_content(template, ["正文", "正文", "内容"]):
            completeness_score += 1
        # Has tone/style guidance
        if _has_real_content(template, ["语气", "tone", "风格", "专业"]):
            specificity_score += 1
        # Has reference template or sample
        if _has_real_content(template, ["参考模板", "模板", "示例"]):
            specificity_score += 2
            completeness_score += 1
        # Has action/close guidance
        if _has_real_content(template, ["签名", "祝福", "行动", "收尾"]):
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
    Use LLM with deep reasoning to generate optimized prompt.
    Uses the LLM-Enhanced prompts for genuine deep reasoning, not template filling.
    """
    if not api_key:
        return None

    # Select the right generation prompt based on instruction type
    if instruction_type == "code":
        user_prompt = CODE_GENERATION_PROMPT.format(instruction=instruction)
    elif instruction_type == "writing":
        user_prompt = WRITING_GENERATION_PROMPT.format(instruction=instruction)
    elif instruction_type == "explanation":
        user_prompt = EXPLANATION_GENERATION_PROMPT.format(instruction=instruction)
    else:
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
                    {"role": "system", "content": PROMPT_GENERATION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.8,  # Higher temp for creative reasoning
            },
            timeout=60,  # Longer timeout for deep reasoning
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def optimize_with_llm(instruction: str, instruction_type: str = None) -> OptimizationResult:
    """Optimize using LLM when API key is configured."""
    cfg = get_llm_config()
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
        # Fallback path: generate A/B/C structured prompt versions
        versions = generate_optimized_versions(instruction, count=3)
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
