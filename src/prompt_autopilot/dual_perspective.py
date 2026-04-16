"""
Dual Perspective Analysis System

Two viewpoints analyze each instruction:
1. Engineer Perspective (工程师视角) - Technical completeness
2. Product Perspective (产品视角) - Real user needs

Then they challenge each other, and only show conflicts to the user.
"""

from typing import TypedDict
from dataclasses import dataclass, field
from .core import AnalysisResult  # Re-use the type

@dataclass
class PerspectiveResult:
    """Result from one perspective's analysis."""
    viewpoint: str  # "工程师" or "产品"
    understanding: str  # How this perspective understands the task
    gaps: list[str]  # Identified gaps/issues
    confidence: float  # 0-1, how confident this perspective is
    questions: list[str]  # Questions this perspective would ask

@dataclass
class ConflictResult:
    """Where the two perspectives disagree."""
    engineer_gap: str
    product_gap: str
    resolution_needed: bool  # True if user needs to decide
    question_to_user: str

@dataclass
class DualAnalysis:
    """Complete dual-perspective analysis."""
    original: str
    engineer: PerspectiveResult
    product: PerspectiveResult
    conflicts: list[ConflictResult]
    common_gaps: list[str]  # Gaps both agree on
    recommended_confidence: float  # 0-1
    auto_proceed: bool  # True if confident enough to proceed
    analysis_text: str  # Formatted analysis for display

# =============================================================================
# Engineer Perspective Analysis
# =============================================================================

def analyze_engineer(instruction: str, lang: str = "zh") -> PerspectiveResult:
    """
    Engineer perspective: Focus on technical completeness.
    
    Asks: Is this technically complete? What's missing?
    """
    instruction_lower = instruction.lower()
    
    gaps = []
    questions = []
    understanding = ""
    confidence = 0.5
    
    # Detect instruction type
    if any(w in instruction_lower for w in ["代码", "code", "函数", "function", "算法", "实现", "implement"]):
        understanding = "代码/算法实现任务"
        
        # Check technical specs
        if not any(w in instruction_lower for w in ["python", "javascript", "java", "go", "rust", "sql", "api", "sql"]):
            gaps.append("编程语言/框架未指定")
            questions.append("用什么语言实现？")
        
        if not any(w in instruction_lower for w in ["输入", "input", "参数", "parameter", "返回", "return"]):
            gaps.append("输入输出未明确")
            questions.append("函数的输入输出是什么？")
            
        if not any(w in instruction_lower for w in ["错误", "error", "异常", "exception", "验证", "validate"]):
            gaps.append("错误处理未考虑")
            questions.append("需要处理哪些异常情况？")
            
        if len(gaps) == 0:
            confidence = 0.8
            
    elif any(w in instruction_lower for w in ["登录", "注册", "auth", "login", "register", "用户"]):
        understanding = "用户认证系统"
        
        if not any(w in instruction_lower for w in ["jwt", "session", "oauth", "密码", "password", "hash"]):
            gaps.append("认证方式未指定")
            questions.append("用JWT、Session还是其他方式？")
        
        if not any(w in instruction_lower for w in ["数据库", "database", "mysql", "postgresql", "mongodb"]):
            gaps.append("数据存储未指定")
            questions.append("用户数据存在哪里？")
            
        if not any(w in instruction_lower for w in ["注册", "register", "忘记密码", "reset"]):
            gaps.append("可能缺少注册/密码重置功能")
            questions.append("只需要登录，还是注册+登录都要？")
            
        if len(gaps) <= 1:
            confidence = 0.7
            
    elif any(w in instruction_lower for w in ["网站", "web", "app", "前端", "frontend", "页面", "page"]):
        understanding = "网页/应用开发"
        
        if not any(w in instruction_lower for w in ["react", "vue", "angular", "html", "css", "框架"]):
            gaps.append("前端框架未指定")
            questions.append("用什么前端技术？")
            
        if not any(w in instruction_lower for w in ["后端", "backend", "api", "服务器"]):
            gaps.append("后端实现未指定")
            questions.append("有后端吗？还是纯前端？")
            
        if len(gaps) > 0:
            confidence = 0.4
        else:
            confidence = 0.6
            
    elif any(w in instruction_lower for w in ["分析", "analyze", "处理", "process", "数据", "data"]):
        understanding = "数据处理任务"
        
        if not any(w in instruction_lower for w in ["格式", "format", "csv", "json", "excel", "输入格式"]):
            gaps.append("数据格式未指定")
            questions.append("输入数据是什么格式？")
            
        if not any(w in instruction_lower for w in ["输出", "output", "结果", "result"]):
            gaps.append("输出格式未指定")
            questions.append("输出要什么格式？")
            
        if len(gaps) == 0:
            confidence = 0.7
            
    else:
        understanding = "通用任务"
        gaps.append("任务边界不清晰")
        questions.append("具体要实现什么？达到什么效果？")
        confidence = 0.3
    
    # Language-specific adjustments
    if lang == "en":
        understanding = understanding.replace("代码/算法实现任务", "Code/Algorithm Implementation")
        gaps = [g.replace("未指定", "not specified").replace("未明确", "not clear") for g in gaps]
        questions = [q.replace("用", "Use ").replace("是什么", " is ") for q in questions]
    
    return PerspectiveResult(
        viewpoint="工程师视角",
        understanding=understanding,
        gaps=gaps,
        confidence=confidence,
        questions=questions
    )

# =============================================================================
# Product Perspective Analysis  
# =============================================================================

def analyze_product(instruction: str, lang: str = "zh") -> PerspectiveResult:
    """
    Product perspective: Focus on real user needs.
    
    Asks: What does the user REALLY want? What might they not know they need?
    """
    instruction_lower = instruction.lower()
    
    gaps = []
    questions = []
    understanding = ""
    confidence = 0.5
    
    # "登录功能" - might actually need more
    if any(w in instruction_lower for w in ["登录", "login", "登陆"]):
        understanding = "用户需要登录能力"
        
        # User might need more than just login
        if "注册" not in instruction_lower and "register" not in instruction_lower:
            gaps.append("可能需要注册功能（用户不只是登录）")
            questions.append("用户从哪里来？需要先注册吗？")
        
        if "找回密码" not in instruction_lower and "reset" not in instruction_lower:
            gaps.append("可能需要密码找回功能")
            
        if "第三方" not in instruction_lower and "oauth" not in instruction_lower:
            gaps.append("可能需要微信/Google等第三方登录")
            
        if "注册" not in instruction_lower:
            questions.append("只用登录，还是要包括注册？")
            
        confidence = 0.6
        
    # "做个XXX" - very vague
    elif instruction_lower.startswith("做") or instruction_lower.startswith("做个"):
        understanding = "用户想做某个功能/产品"
        
        gaps.append("功能范围不明确")
        gaps.append("用户可能自己也不确定具体要什么")
        questions.append("这个功能给谁用？")
        questions.append("主要解决什么问题？")
        questions.append("有什么参考产品吗？")
        
        confidence = 0.3
        
    # "写代码" / "写个程序"
    elif any(w in instruction_lower for w in ["写代码", "写程序", "写个", "写一个"]):
        understanding = "用户需要代码"
        
        gaps.append("代码用途不明确")
        questions.append("这段代码用在什么项目里？")
        questions.append("有什么特殊要求吗？")
        
        if len(gaps) == 1:
            confidence = 0.5
            
    # Blog post / Article
    elif any(w in instruction_lower for w in ["文章", "博客", "blog", "post", "写文章"]):
        understanding = "用户需要文章/内容"
        
        gaps.append("受众不明确")
        questions.append("这篇文章给谁看？")
        questions.append("需要多长？什么风格？")
        
        if "主题" not in instruction_lower and "topic" not in instruction_lower:
            gaps.append("主题可能不明确")
            questions.append("具体要写什么主题？")
            
        confidence = 0.5
        
    # Explanation - might need depth
    elif any(w in instruction_lower for w in ["解释", "explain", "什么是", "是什么", "介绍"]):
        understanding = "用户需要理解某个概念"
        
        if "给" not in instruction_lower and "to" not in instruction_lower:
            gaps.append("受众不明确")
            questions.append("这个解释给谁看？（技术人员/普通用户/小朋友）")
            
        if len(instruction.split()) < 10:
            gaps.append("问题可能太简单或太宽泛")
            questions.append("想深入了解还是只需概述？")
            
        confidence = 0.6
        
    # API / Interface
    elif any(w in instruction_lower for w in ["api", "接口", "interface", "服务"]):
        understanding = "用户需要API/接口"
        
        gaps.append("接口规范可能不完整")
        questions.append("REST还是GraphQL？")
        questions.append("需要文档吗？")
        
        if "认证" not in instruction_lower and "auth" not in instruction_lower:
            gaps.append("可能需要API认证机制")
            
        confidence = 0.5
        
    else:
        understanding = "用户有某种需求"
        
        gaps.append("需求边界不清晰")
        questions.append("具体要解决什么问题？")
        questions.append("有什么限制条件吗？")
        
        confidence = 0.3
        
    # Language-specific
    if lang == "en":
        understanding = understanding.replace("用户需要", "User needs ")
        gaps = [g.replace("可能需要", "might also need ").replace("不明确", "unclear") for g in gaps]
        questions = [q.replace("这个", "this ").replace("给谁", "for whom") for q in questions]
    
    return PerspectiveResult(
        viewpoint="产品视角",
        understanding=understanding,
        gaps=gaps,
        confidence=confidence,
        questions=questions
    )

# =============================================================================
# Conflict Detection & Resolution
# =============================================================================

def find_conflicts(engineer: PerspectiveResult, product: PerspectiveResult) -> list[ConflictResult]:
    """
    Find where the two perspectives disagree or complement each other.
    Uses semantic matching to avoid flagging overlapping concerns as conflicts.
    """
    # Determine which gaps are truly unique to each perspective
    common_gaps = {g for g in find_common_gaps(engineer, product)}

    conflicts = []

    # Engineer-only gaps (truly unique, not semantically overlapping with product gaps)
    for gap in engineer.gaps:
        if gap not in common_gaps:
            conflicts.append(ConflictResult(
                engineer_gap=gap,
                product_gap="",
                resolution_needed=True,
                question_to_user=f"【技术细节】{gap}，这个重要吗？"
            ))

    # Product-only gaps (truly unique)
    for gap in product.gaps:
        if gap not in common_gaps:
            conflicts.append(ConflictResult(
                engineer_gap="",
                product_gap=gap,
                resolution_needed=True,
                question_to_user=f"【需求确认】{gap}，需要考虑吗？"
            ))

    return conflicts

def find_common_gaps(engineer: PerspectiveResult, product: PerspectiveResult) -> list[str]:
    """Find gaps both perspectives agree on (including semantically similar ones)."""
    common = []
    for eg in engineer.gaps:
        for pg in product.gaps:
            # Exact match
            if eg == pg:
                common.append(eg)
                break
            # Semantic overlap: same underlying topic
            eg_kw = set(eg.replace('未指定', '').replace('缺失', '').replace('可能', '').replace('需要', ''))
            pg_kw = set(pg.replace('未指定', '').replace('缺失', '').replace('可能', '').replace('需要', ''))
            if eg_kw & pg_kw and len(eg_kw & pg_kw) >= 2:
                common.append(eg)
                break
    return common

def calculate_confidence(engineer: PerspectiveResult, product: PerspectiveResult) -> tuple[float, bool]:
    """
    Calculate overall confidence and whether to auto-proceed.
    
    Returns: (confidence, auto_proceed)
    """
    # Both perspectives must be confident
    avg_confidence = (engineer.confidence + product.confidence) / 2
    
    # Reduce confidence if there are conflicts
    conflicts = find_conflicts(engineer, product)
    confidence_penalty = len(conflicts) * 0.05

    final_confidence = max(0.15, avg_confidence - confidence_penalty)
    
    # Auto-proceed if:
    # 1. Both perspectives are confident (avg > 0.6)
    # 2. Few or no conflicts
    # 3. Not too many common gaps
    
    auto_proceed = (
        final_confidence > 0.6 and
        len(conflicts) <= 1 and
        len(engineer.gaps) + len(product.gaps) <= 3
    )
    
    return final_confidence, auto_proceed

# =============================================================================
# Formatting
# =============================================================================

def format_dual_analysis(analysis: DualAnalysis) -> str:
    """Format the dual analysis for display — stunning version."""
    sep = '━' * 49
    lines = []

    # Detect task name from original instruction
    task_name = analysis.original.strip()
    if len(task_name) > 20:
        task_name = task_name[:18] + "…"

    # Header
    lines.append(sep)
    lines.append(f"🧠 双视角分析 · {task_name}")
    lines.append(sep)
    lines.append("")

    # Original instruction
    lines.append(f"📝 原始指令")
    quoted = analysis.original.strip()
    if len(quoted) > 50:
        quoted = quoted[:48] + "…"
    lines.append(f'"{quoted}"')
    lines.append("")

    # Confidence section
    lines.append(f"⚡ 置信度评估")
    lines.append(sep[:24])

    conf_pct = int(analysis.recommended_confidence * 100)
    eng_conf = int(analysis.engineer.confidence * 100)
    prod_conf = int(analysis.product.confidence * 100)

    # Progress bars
    eng_bar = '█' * (eng_conf // 10) + '░' * (10 - eng_conf // 10)
    prod_bar = '█' * (prod_conf // 10) + '░' * (10 - prod_conf // 10)

    lines.append(f"综合置信度：{conf_pct}%")
    lines.append(f"工程师视角：{eng_conf}%  {eng_bar}")
    lines.append(f"产品视角：{prod_conf}%    {prod_bar}")

    total_gaps = len(analysis.engineer.gaps) + len(analysis.product.gaps)
    if total_gaps > 0:
        lines.append(f"⚠️ 存在 {total_gaps} 个缺口，需要确认")
    else:
        lines.append("✅ 置信度高，可以直接生成")
    lines.append("")

    # Engineer view
    lines.append(f"🔧 工程师视角发现")
    lines.append(sep[:24])
    lines.append(f"✅ 理解：{analysis.engineer.understanding}")
    if analysis.engineer.gaps:
        for gap in analysis.engineer.gaps:
            lines.append(f"❌ 缺失：{gap}")
    else:
        lines.append("✅ 未发现明显技术缺口")

    # Engineer suggestions based on smart inference
    eng_suggestions = []
    instr_lower = analysis.original.lower()
    if '登录' in analysis.original or 'login' in instr_lower or 'auth' in instr_lower:
        if not any(x in instr_lower for x in ['jwt', 'session', 'oauth']):
            eng_suggestions.append("→ 用 JWT 做认证，bcrypt 哈希密码")
        if not any(x in instr_lower for x in ['数据库', 'mysql', 'postgresql', 'mongodb']):
            eng_suggestions.append("→ 用 PostgreSQL 存储用户，Redis 存 session")
    if '排序' in analysis.original or 'sort' in instr_lower:
        if not any(x in instr_lower for x in ['时间', '复杂度', 'complexity']):
            eng_suggestions.append("→ 时间复杂度建议 O(n log n)，空间 O(log n)")
    if eng_suggestions:
        lines.append("")
        lines.append("💡 建议补充：")
        for s in eng_suggestions:
            lines.append(f"  {s}")
    lines.append("")

    # Product view
    lines.append(f"🎯 产品视角发现")
    lines.append(sep[:24])
    lines.append(f"✅ 理解：{analysis.product.understanding}")
    if analysis.product.gaps:
        for gap in analysis.product.gaps:
            lines.append(f"❌ 缺失：{gap}")
    else:
        lines.append("✅ 未发现明显需求缺口")

    # Product suggestions
    prod_suggestions = []
    if '登录' in analysis.original or 'login' in instr_lower or 'auth' in instr_lower:
        if not any(x in instr_lower for x in ['注册', 'register']):
            prod_suggestions.append("→ 确认是否需要注册？还是只有已有账户能登录？")
        if not any(x in instr_lower for x in ['第三方', 'oauth', '微信', 'google']):
            prod_suggestions.append("→ 确认是否需要第三方 OAuth（微信/Google）")
    if prod_suggestions:
        lines.append("")
        lines.append("💡 建议补充：")
        for s in prod_suggestions:
            lines.append(f"  {s}")
    lines.append("")

    # Questions to confirm
    questions = []
    for c in analysis.conflicts:
        if c.resolution_needed:
            q = c.question_to_user.replace('【技术细节】', '').replace('【需求确认】', '')
            questions.append(q)

    if questions or total_gaps > 0:
        lines.append(f"📋 缺口确认")
        lines.append(sep[:24])
        for q in questions:
            lines.append(f"❓ {q}")
        # Add generic follow-up questions based on gaps
        if '登录' in analysis.original or 'login' in instr_lower:
            if not any('jwt' in x.lower() or 'session' in x.lower() for x in questions):
                lines.append("❓ 认证方式：用 JWT / Session / OAuth？")
            if not any('数据库' in x or 'postgresql' in x.lower() or 'mysql' in x.lower() for x in questions):
                lines.append("❓ 数据存储：用什么数据库？")
            if not any('注册' in x or '第三方' in x for x in questions):
                lines.append("❓ 功能范围：只登录，还是要注册/找回/第三方？")
        lines.append("")

    lines.append(sep)
    lines.append("💡 输入 'y' 继续生成 · 'n' 退出")
    lines.append(sep)

    return "\n".join(lines)

# =============================================================================
# Main Entry Point
# =============================================================================

def dual_perspective_analysis(instruction: str, lang: str = "auto") -> DualAnalysis:
    """
    Run dual-perspective analysis on an instruction.
    
    Args:
        instruction: The user's original instruction
        lang: Language ("zh", "en", or "auto")
    
    Returns:
        DualAnalysis with results from both perspectives
    """
    # Detect language if auto
    if lang == "auto":
        chinese_chars = sum(1 for c in instruction if '\u4e00' <= c <= '\u9fff')
        english_words = len([w for w in instruction.split() if w.isascii()])
        lang = "zh" if chinese_chars > english_words else "en"
    
    # Run both perspectives
    engineer = analyze_engineer(instruction, lang)
    product = analyze_product(instruction, lang)
    
    # Find conflicts and common ground
    conflicts = find_conflicts(engineer, product)
    common_gaps = find_common_gaps(engineer, product)
    
    # Calculate confidence
    confidence, auto_proceed = calculate_confidence(engineer, product)
    
    # Format analysis text
    analysis = DualAnalysis(
        original=instruction,
        engineer=engineer,
        product=product,
        conflicts=conflicts,
        common_gaps=common_gaps,
        recommended_confidence=confidence,
        auto_proceed=auto_proceed,
        analysis_text=""
    )
    
    analysis.analysis_text = format_dual_analysis(analysis)
    
    return analysis
