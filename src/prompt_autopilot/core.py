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

def generate_direct_code(instruction: str, lang: str) -> str:
    """Generate actual usable code for simple coding tasks."""
    instruction_lower = instruction.lower()
    
    # Sorting - most specific first
    has_sort = any(w in instruction_lower for w in ["排序", "sort", "快排", "quicksort", "mergesort"])
    
    if has_sort:
        if "快" in instruction or "quick" in instruction_lower:
            if lang == "zh":
                return """```python
# 快速排序
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

nums = [3, 6, 8, 10, 1, 2, 1]
print(quicksort(nums))
```

要点：平均O(n log n)，最坏O(n^2)"""
        if "merge" in instruction_lower or "归并" in instruction:
            if lang == "zh":
                return """```python
# 归并排序
def mergesort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    return merge(mergesort(arr[:mid]), mergesort(arr[mid:]))

def merge(left, right):
    result = []
    while left and right:
        result.append(left.pop(0) if left[0] <= right[0] else right.pop(0))
    return result + left + right

nums = [3, 6, 8, 10, 1, 2, 1]
print(mergesort(nums))
```

要点：稳定排序，总是O(n log n)"""
        if lang == "zh":
            return """```python
# 排序函数
def sort_arr(arr, method="quick"):
    if method == "quick":
        return quicksort(arr)
    elif method == "merge":
        return mergesort(arr)
    return sorted(arr)

def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    return quicksort([x for x in arr if x < pivot]) + quicksort([x for x in arr if x == pivot]) + quicksort([x for x in arr if x > pivot])
```

支持: 快排/归并/内置"""
    
    # Login
    if any(w in instruction_lower for w in ["登录", "login", "登陆"]):
        if lang == "zh":
            return """```python
def login(username, password):
    user = db.query("SELECT * FROM users WHERE username = ?", username)
    if not user:
        return {"success": False, "message": "用户不存在"}
    if not verify_password(password, user["password_hash"]):
        return {"success": False, "message": "密码错误"}
    return {"success": True, "user": {"id": user["id"], "username": user["username"]}}
```

要点：密码哈希、参数化查询、模糊错误信息"""
    
    # API
    if any(w in instruction_lower for w in ["api", "接口"]):
        if lang == "zh":
            return """```python
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/api/resource", methods=["GET"])
def get_resource():
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    resources = db.query("SELECT * FROM resources LIMIT ? OFFSET ?", (page-1)*limit, limit)
    return jsonify({"data": resources})
```"""
    
    # Generic
    if lang == "zh":
        topic = instruction.replace("帮我", "").replace("写", "").replace("一个", "").strip()
        # Use generic function name for Chinese topics (cannot derive valid Python identifier)
        func_name = 'solution'
        return f"""```python
# {topic}
def {func_name}():
    pass
```
提示: 较简单，请补充细节"""
    return f"""```python
# {instruction}
def solution():
    pass
```"""
    
    # API endpoint
    if any(w in instruction_lower for w in ["api", "接口", "endpoint"]):
        if lang == "zh":
            return '''```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@.app.route("/api/resource", methods=["GET"])
def get_resource():
    """获取资源列表"""
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 20, type=int)
    
    resources = db.query(
        "SELECT * FROM resources LIMIT ? OFFSET ?",
        (page - 1) * limit, limit
    )
    total = db.query("SELECT COUNT(*) FROM resources")[0][0]
    
    return jsonify({
        "data": resources,
        "pagination": {"page": page, "limit": limit, "total": total}
    })

@.app.route("/api/resource", methods=["POST"])
def create_resource():
    """创建资源"""
    data = request.get_json()
    # 验证必要字段
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    
    resource_id = db.insert("INSERT INTO resources (name, data) VALUES (?, ?)",
                            data["name"], json.dumps(data))
    return jsonify({"id": resource_id, **data}), 201
```'''
    
    # Sorting algorithms
    if any(w in instruction_lower for w in ["排序", "sort", "快排", "quicksort", "mergesort"]):
        if "快" in instruction or "quick" in instruction_lower:
            if lang == "zh":
                return """```python
# 快速排序
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

nums = [3, 6, 8, 10, 1, 2, 1]
print(quicksort(nums))  # [1, 1, 2, 3, 6, 8, 10]
```

**要点**：
- 平均 O(n log n)，最坏 O(n²)
- 选择中间元素作基准可减少最坏情况"""
        if "merge" in instruction_lower or "归并" in instruction:
            if lang == "zh":
                return """```python
# 归并排序
def mergesort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    return merge(mergesort(arr[:mid]), mergesort(arr[mid:]))

def merge(left, right):
    result = []
    while left and right:
        result.append(left.pop(0) if left[0] <= right[0] else right.pop(0))
    return result + left + right

nums = [3, 6, 8, 10, 1, 2, 1]
print(mergesort(nums))  # [1, 1, 2, 3, 6, 8, 10]
```

**要点**：
- 稳定排序，总是 O(n log n)
- 需要 O(n) 额外空间"""
        if lang == "zh":
            return """```python
# 排序函数
def sort_arr(arr, method="quick"):
    if method == "quick":
        return quicksort(arr)
    elif method == "merge":
        return mergesort(arr)
    return sorted(arr)

def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    return quicksort([x for x in arr if x < pivot]) + \
           [x for x in arr if x == pivot] + \
           quicksort([x for x in arr if x > pivot])
```

**支持**: 快排(quick)、归并(merge)、内置排序(sorted)"""

    # Generic code request
    if lang == "zh":
        topic = instruction.replace("帮我", "").replace("写", "").replace("一个", "").strip()
        # Use generic function name for Chinese topics (cannot derive valid Python identifier)
        func_name = 'solution'
        return f"""```python
# {topic}
def {func_name}():
    pass
```

**提示**: 指令较简单，如需特定实现请补充更多细节"""
    return f"""```python
# {instruction}
def solution():
    pass
```"""

def generate_direct_explanation(instruction: str, lang: str) -> str:
    """Generate direct explanations without templates."""
    instruction_lower = instruction.lower()
    
    # AI/ML concepts
    if any(w in instruction_lower for w in ["ai", "人工智能", "机器学习", "ml"]):
        if lang == "zh":
            return '''## AI（人工智能）是什么？

**简单说**：让计算机具有像人一样的智能，能学习、推理、做决策。

**三种类型**：
1. **弱AI**：专精单一任务（如棋类AI、语音助手）
2. **强AI**：通用智能，能像人一样思考（还未实现）
3. **超AI**：超越人类智能（科幻领域）

**核心原理**：
- **机器学习**：从数据中学习规律
- **深度学习**：用神经网络模拟人脑
- **大模型**：海量数据训练的超级大脑

**实际应用**：人脸识别、推荐系统、自动驾驶、医疗诊断'''

    if "api" in instruction_lower and lang == "zh":
        return '''## API 是什么？

**API = Application Programming Interface（应用程序接口）**

**简单比喻**：就像餐厅的菜单。厨房（系统）提供什么菜（功能），你（程序）只需要按菜单点菜（调用API），不用知道厨房怎么做的。

**实际例子**：
```
用户点外卖 → APP调用外卖平台API → 外卖平台派单 → 骑手取餐 → 送达
```

**网页API示例**：
```javascript
// 调用天气API
fetch("https://api.weather.com/today?city=北京")
  .then(r => r.json())
  .then(data => console.log(data))
```

**API让开发变简单**：不用自己造轮子，直接用别人的服务。'''

    # Generic explanation
    topic = instruction.replace("解释", "").replace("说明", "").replace("什么是", "").replace("介绍", "").strip()
    if lang == "zh":
        return f'''## {topic}是什么？

**一句话解释**：
{topic}是一种[你的理解/定义]

**核心要点**：
1. **是什么**：{topic}的精确定义
2. **为什么重要**：解决了什么问题
3. **怎么工作**：基本原理或机制

**常见用途**：
- 场景1
- 场景2

**需要注意**：
- 优点：...
- 局限：..'''
    return f'''## {topic}

**Definition**:
[Your definition here]

**Key Points**:
1. What it is
2. Why it matters
3. How it works'''

def generate_direct_writing(instruction: str, lang: str) -> str:
    """Generate usable writing templates/content."""
    instruction_lower = instruction.lower()
    
    # Email templates - check rejection BEFORE generic email/apology
    if any(w in instruction_lower for w in ["拒绝", "谢绝", "declin"]):
        if lang == "zh":
            return '''## 拒绝邮件模板

**Subject**: 关于[面试/职位/邀请]的回复

亲爱的[收件人]：

您好。

非常感谢您发来的[面试邀请/职位机会/邀请]。

经过慎重考虑，我决定[接受/拒绝]本次[面试/邀请]。

[如拒绝，说明原因，如：因个人时间安排冲突/已接受其他机会等]

再次感谢您的理解与支持，祝贵司[业务蒸蒸日上/招聘顺利]。

此致
[你的名字]
[日期]'''
    
    if any(w in instruction_lower for w in ["邮件", "email", "道歉"]):
        if lang == "zh":
            return '''## 道歉邮件模板

**Subject**: 关于[事件]的致歉

亲爱的[收件人]：

您好。

写这封邮件是想就[具体事件]向您表达诚挚的歉意。

[说明发生了什么，以及为什么会发生]

我们已经采取了以下措施防止类似问题再次发生：
- 措施1
- 措施2

再次为给您带来的不便深表歉意。

此致
[你的名字]
[日期]'''

    if any(w in instruction_lower for w in ["汇报", "报告", "项目"]):
        if lang == "zh":
            return '''## 项目进展汇报

**项目名称**：[名称]
**汇报日期**：[日期]
**负责人**：[姓名]

### 一、本周进展
- [已完成任务1]
- [已完成任务2]

### 二、关键指标
| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 进度 | 50% | 45% | ⚠️ 滞后5% |

### 三、问题与风险
- 问题1：[描述] → 解决方案
- 风险：[描述] → 应对措施

### 四、下周计划
- [计划任务1]
- [计划任务2]

### 五、资源需求
- [需要什么支持]'''

    # Generic writing
    if lang == "zh":
        return f'''## 关于"{instruction}"的内容框架

### 引言
[开场白，引出主题]

### 主体
#### 要点1
[内容]

#### 要点2
[内容]

### 结语
[总结]'''
    return f'''## Content for: {instruction}

### Introduction
[Opening]

### Main Points
- Point 1
- Point 2

### Conclusion
[Summary]'''

# =============================================================================
# Main Generator
# =============================================================================

def generate_optimized_versions(instruction: str, count: int = 3) -> list[VersionResult]:
    """
    Generate outputs based on task complexity.
    Simple = direct output
    Medium = framework with guidance
    Complex = structured template
    """
    analysis = analyze_instruction(instruction)
    complexity = analysis["task_complexity"]
    instr_type = analysis["instruction_type"]
    lang = analysis["language"]
    stripped = instruction.strip()
    
    versions = []
    
    # Version A: Direct (best for simple tasks)
    if complexity == "simple":
        if instr_type == "code":
            direct_output = generate_direct_code(instruction, lang)
        elif instr_type == "explanation":
            direct_output = generate_direct_explanation(instruction, lang)
        elif instr_type == "writing":
            direct_output = generate_direct_writing(instruction, lang)
        else:
            direct_output = f"**直接回答**：{stripped}\n\n[请补充具体内容或细节]"
        
        versions.append({
            "type": "A (Direct)",
            "description": "直接给出可用结果，不用填写任何内容",
            "template": direct_output,
            "is_direct": True,
        })
        
    # Version B: Framework (for medium tasks)
    if instr_type == "code":
        if lang == "zh":
            framework = f'''## {stripped}

**推荐实现**：
```python
# 实现代码框架
def solution():
    # 核心逻辑
    pass
```

**关键考虑**：
- 输入输出明确
- 错误处理
- 性能优化（如需要）

**扩展方向**：
- 添加缓存
- 并发支持'''
        else:
            framework = f'''## {stripped}

```python
def solution():
    # Core logic
    pass
```

**Key Considerations**:
- Input/output validation
- Error handling'''
        versions.append({
            "type": "B (Framework)",
            "description": "给出代码框架和关键考虑，需要微调",
            "template": framework,
            "is_direct": False,
        })
    
    elif instr_type == "writing":
        content = generate_direct_writing(instruction, lang)
        versions.append({
            "type": "B (Content)",
            "description": "给出实际内容框架，可直接使用",
            "template": content,
            "is_direct": True,
        })
    
    elif instr_type == "explanation":
        content = generate_direct_explanation(instruction, lang)
        versions.append({
            "type": "B (Explanation)",
            "description": "给出完整解释，可直接阅读",
            "template": content,
            "is_direct": True,
        })
    
    # Version C: Structured Template (for complex tasks)
    if instr_type == "code":
        if lang == "zh":
            template = f'''## 任务
{stripped}

## 输入规范
[具体输入格式]

## 输出规范
[具体输出格式]

## 约束条件
- [性能要求]
- [安全要求]
- [其他]

## 实现步骤
1. [步骤1]
2. [步骤2]
3. [步骤3]

## 验收标准
- [可测试的标准]'''
        else:
            template = f'''## Task
{stripped}

## Input
[Spec]

## Output
[Spec]

## Constraints
- [Performance]
- [Security]

## Steps
1. [Step 1]
2. [Step 2]

## Acceptance
- [Criterion 1]'''
        versions.append({
            "type": "C (Template)",
            "description": "结构化模板，需要填写细节",
            "template": template,
            "is_direct": False,
        })
    
    elif instr_type == "writing":
        if lang == "zh":
            template = f'''## 写作任务
{stripped}

## 基本信息
- 受众：[谁]
- 语气：[正式/亲切/专业]
- 字数：[多少]

## 内容要点
1. [要点1]
2. [要点2]
3. [要点3]

## 格式要求
[指定格式]

## 初稿
[在此起草]'''
        else:
            template = f'''## Writing Task
{stripped}

## Audience
[Who]

## Tone
[Formal/Casual/Professional]

## Key Points
1. [Point 1]
2. [Point 2]

## Draft
[Write here]'''
        versions.append({
            "type": "C (Template)",
            "description": "结构化模板，引导完成完整写作",
            "template": template,
            "is_direct": False,
        })
    
    return versions[:count]

# =============================================================================
# Evaluation (Simplified)
# =============================================================================

def evaluate_version(version: VersionResult, analysis: AnalysisResult) -> EvaluationResult:
    """Evaluate based on whether the output matches the task complexity."""
    complexity = analysis["task_complexity"]
    
    if version["is_direct"] and complexity == "simple":
        # Direct output for simple task = perfect
        return {
            "scores": {"clarity": 10, "specificity": 8, "completeness": 8},
            "overall": 9.0,
            "grade": "A"
        }
    elif not version["is_direct"] and complexity == "simple":
        # Template for simple task = overkill
        return {
            "scores": {"clarity": 4, "specificity": 5, "completeness": 6},
            "overall": 5.0,
            "grade": "C"
        }
    elif version["is_direct"]:
        return {
            "scores": {"clarity": 7, "specificity": 7, "completeness": 7},
            "overall": 7.0,
            "grade": "B"
        }
    else:
        return {
            "scores": {"clarity": 6, "specificity": 6, "completeness": 7},
            "overall": 6.5,
            "grade": "B"
        }

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

    if not api_key:
        return optimize(instruction)

    generated = generate_with_llm(instruction, api_key, model, endpoint, instruction_type)
    if not generated:
        return optimize(instruction)

    analysis = analyze_instruction(instruction)
    version: VersionResult = {
        "type": "LLM (Custom)",
        "description": "LLM 生成的优化版本（需自行配置 API key）",
        "template": generated,
        "is_direct": True,
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
    """Main optimization pipeline. Set use_llm=True to prefer LLM generation."""
    if use_llm:
        analysis = analyze_instruction(instruction)
        return optimize_with_llm(instruction, instruction_type=analysis["instruction_type"])

    analysis = analyze_instruction(instruction)
    versions = generate_optimized_versions(instruction)
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
