"""
Core optimization logic for prompt-autopilot v2.

Philosophy: Direct answers, not templates. The tool should complete tasks,
not create more work for the user.
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
        "登录", "注册", "用户", "验证", "auth", "login", "register"
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
        func_name = ''.join(c for c in topic if c.isalnum() or c == '_')
        return f"""```python
# {topic}
def {func_name}():
    pass
```
提示: 较简单，请补充细节"""
    return f"""```python
# {instruction}
def process():
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
        func_name = ''.join(c for c in topic if c.isalnum() or c == '_')
        return f"""```python
# {topic}
def {func_name}():
    """
    处理: {topic}
    """
    pass
```

**提示**: 指令较简单，如需特定实现请补充更多细节"""
    return f"""```python
# {instruction}
def process():
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
    
    # Email templates
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
        return f'''## 关于"[instruction]"的内容框架

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
            direct_output = f"**直接回答**：{stripped}\n\n[基于指令生成的具体内容]"
        
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
            "scores": {"fit": 10, "completeness": 8},
            "overall": 9.0,
            "grade": "A"
        }
    elif not version["is_direct"] and complexity == "simple":
        # Template for simple task = overkill
        return {
            "scores": {"fit": 4, "completeness": 6},
            "overall": 5.0,
            "grade": "C"
        }
    elif version["is_direct"]:
        return {
            "scores": {"fit": 7, "completeness": 7},
            "overall": 7.0,
            "grade": "B"
        }
    else:
        return {
            "scores": {"fit": 6, "completeness": 7},
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
# Main Pipeline
# =============================================================================

def optimize(instruction: str) -> OptimizationResult:
    """Main optimization pipeline."""
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
