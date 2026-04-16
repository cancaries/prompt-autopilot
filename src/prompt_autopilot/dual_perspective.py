"""
Dual Perspective Analysis System - LLM-Enhanced Version

Two viewpoints analyze each instruction using deep LLM reasoning:
1. Engineer Perspective (工程师视角) - Technical completeness
2. Product Perspective (产品视角) - Real user needs

The LLM itself does deep reasoning, not rule matching.
"""

import requests
import re
from typing import TypedDict, Optional
from dataclasses import dataclass
from pathlib import Path
from .core import load_config

# =============================================================================
# LLM-Enhanced Deep Analysis Prompts
# =============================================================================

DUAL_ANALYSIS_PROMPT = '''你是一个批判性思维专家。分析这个指令：

{instruction}

请深度思考：
1. 【工程师视角】从技术实现角度：
   - 这个需求表面简单，但可能隐藏什么技术复杂性？
   - 有什么边界情况、异常场景没提到？
   - 架构设计时需要考虑什么？

2. 【产品视角】从用户真实需求角度：
   - 用户真正想完成的是什么？（不只是字面意思）
   - 有什么需求是用户"理所当然认为不用说"但实际很关键？
   - 用户的使用场景可能是怎样的？

3. 【缺口发现】
   - 列出 3 个最关键的缺口（不只是"没指定语言"这种）
   - 每个缺口说清楚：为什么这个很重要？

4. 【置信度】
   - 0-100%，这个指令的完整度如何？
   - 如果只有 30% 完整度，那 70% 的未知部分可能是什么？

直接输出分析结果，用结构化格式，不要解释你的思考过程。'''

LLM_REFLECTION_PROMPT = '''你是 prompt-autopilot 的创造者。审视当前系统：

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

class PerspectiveResult:
    """Result from one perspective's analysis."""
    viewpoint: str  # "工程师" or "产品"
    understanding: str  # How this perspective understands the task
    gaps: list[str]  # Identified gaps/issues
    confidence: float  # 0-1, how confident this perspective is
    questions: list[str]  # Questions this perspective would ask

    def __init__(self, viewpoint="", understanding="", gaps=None, confidence=0.5, questions=None):
        self.viewpoint = viewpoint
        self.understanding = understanding
        self.gaps = gaps or []
        self.confidence = confidence
        self.questions = questions or []

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
# LLM Call Helper
# =============================================================================

def _llm_call(prompt: str, system_role: str = "你是一个批判性思维专家。") -> Optional[str]:
    """Call LLM API with the given prompt. Returns None on failure."""
    cfg = load_config()
    api_key = cfg.get("llm_api_key")
    model = cfg.get("llm_model", "gpt-4")
    endpoint = cfg.get("llm_endpoint", "https://api.openai.com/v1/chat/completions")

    if not api_key:
        return None

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
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": prompt},
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

# =============================================================================
# LLM-Enhanced Dual Perspective Analysis
# =============================================================================

def _parse_llm_dual_analysis(instruction: str, llm_output: str) -> DualAnalysis:
    """
    Parse LLM's dual perspective analysis output into DualAnalysis structure.
    The LLM outputs structured text; we parse it into our dataclasses.
    """
    # Extract confidence
    conf_match = re.search(r'置信度[：:]\s*(\d+)%?', llm_output)
    confidence = float(conf_match.group(1)) / 100 if conf_match else 0.5
    
    # Extract gaps (3 key gaps)
    gaps = re.findall(r'[-*]\s*(?:缺口)?\s*(.{10,60})', llm_output)
    
    # Engineer perspective content
    eng_match = re.search(r'【?工程师视角】?(.*?)(?=【?产品视角|$)', llm_output, re.DOTALL)
    eng_text = eng_match.group(1) if eng_match else ""
    
    # Product perspective content  
    prod_match = re.search(r'【?产品视角】?(.*?)(?=【?缺口|【?置信度|$)', llm_output, re.DOTALL)
    prod_text = prod_match.group(1) if prod_match else ""
    
    # Extract understanding from each perspective
    eng_understanding = ""
    eng_gaps = []
    eng_questions = []
    
    prod_understanding = ""
    prod_gaps = []
    prod_questions = []
    
    # Parse engineer section
    for line in eng_text.split('\n'):
        line = line.strip()
        if '理解' in line or '任务' in line:
            eng_understanding += line
        elif '缺失' in line or '缺口' in line or '没有' in line:
            eng_gaps.append(line)
        elif '？' in line or '?' in line:
            eng_questions.append(line)
    
    # Parse product section
    for line in prod_text.split('\n'):
        line = line.strip()
        if '理解' in line or '任务' in line or '真正' in line:
            prod_understanding += line
        elif '缺失' in line or '缺口' in line or '没有' in line or '需要' in line:
            prod_gaps.append(line)
        elif '？' in line or '?' in line:
            prod_questions.append(line)
    
    # If parsing failed, use raw text as understanding
    if not eng_understanding:
        eng_understanding = eng_text[:200] if eng_text else "LLM分析完成"
    if not prod_understanding:
        prod_understanding = prod_text[:200] if prod_text else "LLM分析完成"
    
    # Use gaps from the gaps section if perspective-specific parsing failed
    if not eng_gaps and gaps:
        eng_gaps = gaps[:2]
    if not prod_gaps and gaps:
        prod_gaps = gaps[2:] if len(gaps) > 2 else gaps[1:]
    
    engineer = PerspectiveResult(
        viewpoint="工程师视角",
        understanding=eng_understanding,
        gaps=[g for g in eng_gaps if g][:5],
        confidence=confidence,
        questions=[q for q in eng_questions if q][:5]
    )
    
    product = PerspectiveResult(
        viewpoint="产品视角",
        understanding=prod_understanding,
        gaps=[g for g in prod_gaps if g][:5],
        confidence=confidence,
        questions=[q for q in prod_questions if q][:5]
    )
    
    # Build conflicts from gaps
    conflicts = []
    all_gaps = list(set(eng_gaps + prod_gaps))
    for gap in all_gaps[:3]:
        if gap in eng_gaps and gap in prod_gaps:
            pass  # common gap
        elif gap in eng_gaps:
            conflicts.append(ConflictResult(
                engineer_gap=gap,
                product_gap="",
                resolution_needed=True,
                question_to_user=f"【技术细节】{gap}，这个重要吗？"
            ))
        else:
            conflicts.append(ConflictResult(
                engineer_gap="",
                product_gap=gap,
                resolution_needed=True,
                question_to_user=f"【需求确认】{gap}，需要考虑吗？"
            ))
    
    # Determine auto_proceed based on confidence
    auto_proceed = confidence >= 0.6 and len(conflicts) <= 2
    
    analysis = DualAnalysis(
        original=instruction,
        engineer=engineer,
        product=product,
        conflicts=conflicts,
        common_gaps=list(set(eng_gaps) & set(prod_gaps)),
        recommended_confidence=confidence,
        auto_proceed=auto_proceed,
        analysis_text=""
    )
    
    analysis.analysis_text = format_dual_analysis(analysis)
    return analysis


def dual_perspective_analysis_llm(instruction: str, lang: str = "auto") -> Optional[DualAnalysis]:
    """
    Run LLM-enhanced dual-perspective analysis on an instruction.
    Returns None if no API key is configured.
    """
    cfg = load_config()
    api_key = cfg.get("llm_api_key")
    
    if not api_key:
        return None
    
    prompt = DUAL_ANALYSIS_PROMPT.format(instruction=instruction)
    system_role = "你是一个批判性思维专家，擅长从工程师和产品两个视角深度分析需求。"
    
    llm_output = _llm_call(prompt, system_role)
    if not llm_output:
        return None
    
    return _parse_llm_dual_analysis(instruction, llm_output)

# =============================================================================
# Fallback: Rule-based analysis (when no LLM API key)
# =============================================================================

def analyze_engineer(instruction: str, lang: str = "zh") -> PerspectiveResult:
    """
    Engineer perspective: Focus on technical completeness (rule-based fallback).
    """
    instruction_lower = instruction.lower()
    gaps = []
    questions = []
    understanding = ""
    confidence = 0.5
    
    if any(w in instruction_lower for w in ["代码", "code", "函数", "function", "算法", "实现", "implement"]):
        understanding = "代码/算法实现任务"
        if not any(w in instruction_lower for w in ["python", "javascript", "java", "go", "rust", "sql"]):
            gaps.append("编程语言/框架未指定")
            questions.append("用什么语言实现？")
        if not any(w in instruction_lower for w in ["输入", "input", "参数", "返回", "return"]):
            gaps.append("输入输出未明确")
            questions.append("函数的输入输出是什么？")
        if not any(w in instruction_lower for w in ["错误", "error", "异常", "验证"]):
            gaps.append("错误处理未考虑")
            questions.append("需要处理哪些异常情况？")
        if len(gaps) == 0:
            confidence = 0.8
    elif any(w in instruction_lower for w in ["登录", "注册", "auth", "login", "register", "用户"]):
        understanding = "用户认证系统"
        if not any(w in instruction_lower for w in ["jwt", "session", "oauth", "密码", "hash"]):
            gaps.append("认证方式未指定")
            questions.append("用JWT、Session还是其他方式？")
        if not any(w in instruction_lower for w in ["数据库", "database", "mysql", "postgresql", "mongodb"]):
            gaps.append("数据存储未指定")
            questions.append("用户数据存在哪里？")
        if len(gaps) <= 1:
            confidence = 0.7
    elif any(w in instruction_lower for w in ["网站", "web", "app", "前端", "frontend", "页面"]):
        understanding = "网页/应用开发"
        if not any(w in instruction_lower for w in ["react", "vue", "angular", "html", "css"]):
            gaps.append("前端框架未指定")
            questions.append("用什么前端技术？")
        if not any(w in instruction_lower for w in ["后端", "backend", "api", "服务器"]):
            gaps.append("后端实现未指定")
            questions.append("有后端吗？还是纯前端？")
        confidence = 0.4 if gaps else 0.6
    elif any(w in instruction_lower for w in ["分析", "analyze", "处理", "process", "数据", "data"]):
        understanding = "数据处理任务"
        if not any(w in instruction_lower for w in ["格式", "format", "csv", "json", "excel"]):
            gaps.append("数据格式未指定")
            questions.append("输入数据是什么格式？")
        if not any(w in instruction_lower for w in ["输出", "output", "结果"]):
            gaps.append("输出格式未指定")
            questions.append("输出要什么格式？")
        confidence = 0.7 if len(gaps) == 0 else 0.4
    else:
        understanding = "通用任务"
        gaps.append("任务边界不清晰")
        questions.append("具体要实现什么？达到什么效果？")
        confidence = 0.3
    
    return PerspectiveResult(
        viewpoint="工程师视角",
        understanding=understanding,
        gaps=gaps,
        confidence=confidence,
        questions=questions
    )

def analyze_product(instruction: str, lang: str = "zh") -> PerspectiveResult:
    """
    Product perspective: Focus on real user needs (rule-based fallback).
    """
    instruction_lower = instruction.lower()
    gaps = []
    questions = []
    understanding = ""
    confidence = 0.5
    
    if any(w in instruction_lower for w in ["登录", "login", "登陆"]):
        understanding = "用户需要登录能力"
        if "注册" not in instruction_lower and "register" not in instruction_lower:
            gaps.append("可能需要注册功能（用户不只是登录）")
            questions.append("用户从哪里来？需要先注册吗？")
        if "找回密码" not in instruction_lower and "reset" not in instruction_lower:
            gaps.append("可能需要密码找回功能")
        if "第三方" not in instruction_lower and "oauth" not in instruction_lower:
            gaps.append("可能需要微信/Google等第三方登录")
        confidence = 0.6
    elif instruction_lower.startswith("做") or instruction_lower.startswith("做个"):
        understanding = "用户想做某个功能/产品"
        gaps.append("功能范围不明确")
        gaps.append("用户可能自己也不确定具体要什么")
        questions.append("这个功能给谁用？")
        questions.append("主要解决什么问题？")
        confidence = 0.3
    elif any(w in instruction_lower for w in ["写代码", "写程序", "写个", "写一个"]):
        understanding = "用户需要代码"
        gaps.append("代码用途不明确")
        questions.append("这段代码用在什么项目里？")
        confidence = 0.5
    elif any(w in instruction_lower for w in ["文章", "博客", "blog", "post", "写文章"]):
        understanding = "用户需要文章/内容"
        gaps.append("受众不明确")
        questions.append("这篇文章给谁看？")
        questions.append("需要多长？什么风格？")
        confidence = 0.5
    elif any(w in instruction_lower for w in ["解释", "explain", "什么是", "是什么", "介绍"]):
        understanding = "用户需要理解某个概念"
        if "给" not in instruction_lower and "to" not in instruction_lower:
            gaps.append("受众不明确")
            questions.append("这个解释给谁看？")
        if len(instruction.split()) < 10:
            gaps.append("问题可能太简单或太宽泛")
            questions.append("想深入了解还是只需概述？")
        confidence = 0.6
    elif any(w in instruction_lower for w in ["api", "接口", "interface", "服务"]):
        understanding = "用户需要API/接口"
        gaps.append("接口规范可能不完整")
        questions.append("REST还是GraphQL？")
        questions.append("需要文档吗？")
        confidence = 0.5
    else:
        understanding = "用户有某种需求"
        gaps.append("需求边界不清晰")
        questions.append("具体要解决什么问题？")
        confidence = 0.3
    
    return PerspectiveResult(
        viewpoint="产品视角",
        understanding=understanding,
        gaps=gaps,
        confidence=confidence,
        questions=questions
    )

# =============================================================================
# Conflict Detection & Resolution (kept from original)
# =============================================================================

def find_conflicts(engineer: PerspectiveResult, product: PerspectiveResult) -> list[ConflictResult]:
    common_gaps = {g for g in find_common_gaps(engineer, product)}
    conflicts = []
    for gap in engineer.gaps:
        if gap not in common_gaps:
            conflicts.append(ConflictResult(
                engineer_gap=gap,
                product_gap="",
                resolution_needed=True,
                question_to_user=f"【技术细节】{gap}，这个重要吗？"
            ))
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
    common = []
    for eg in engineer.gaps:
        for pg in product.gaps:
            if eg == pg:
                common.append(eg)
                break
            eg_kw = set(eg.replace('未指定', '').replace('缺失', '').replace('可能', '').replace('需要', ''))
            pg_kw = set(pg.replace('未指定', '').replace('缺失', '').replace('可能', '').replace('需要', ''))
            if eg_kw & pg_kw and len(eg_kw & pg_kw) >= 2:
                common.append(eg)
                break
    return common

def calculate_confidence(engineer: PerspectiveResult, product: PerspectiveResult) -> tuple[float, bool]:
    avg_confidence = (engineer.confidence + product.confidence) / 2
    conflicts = find_conflicts(engineer, product)
    confidence_penalty = len(conflicts) * 0.05
    final_confidence = max(0.15, avg_confidence - confidence_penalty)
    auto_proceed = (
        final_confidence > 0.6 and
        len(conflicts) <= 1 and
        len(engineer.gaps) + len(product.gaps) <= 3
    )
    return final_confidence, auto_proceed

# =============================================================================
# Formatting (kept from original)
# =============================================================================

def format_dual_analysis(analysis: DualAnalysis) -> str:
    """Format the dual analysis for display."""
    sep = '━' * 49
    lines = []
    task_name = analysis.original.strip()
    if len(task_name) > 20:
        task_name = task_name[:18] + "…"

    lines.append(sep)
    lines.append(f"🧠 双视角分析 · {task_name}")
    lines.append(sep)
    lines.append("")

    lines.append(f"📝 原始指令")
    quoted = analysis.original.strip()
    if len(quoted) > 50:
        quoted = quoted[:48] + "…"
    lines.append(f'"{quoted}"')
    lines.append("")

    lines.append(f"⚡ 置信度评估")
    lines.append(sep[:24])

    conf_pct = int(analysis.recommended_confidence * 100)
    eng_conf = int(analysis.engineer.confidence * 100)
    prod_conf = int(analysis.product.confidence * 100)

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

    lines.append(f"🔧 工程师视角发现")
    lines.append(sep[:24])
    lines.append(f"✅ 理解：{analysis.engineer.understanding}")
    if analysis.engineer.gaps:
        for gap in analysis.engineer.gaps:
            lines.append(f"❌ 缺失：{gap}")
    else:
        lines.append("✅ 未发现明显技术缺口")
    if analysis.engineer.questions:
        lines.append("")
        for q in analysis.engineer.questions:
            lines.append(f"❓ {q}")
    lines.append("")

    lines.append(f"🎯 产品视角发现")
    lines.append(sep[:24])
    lines.append(f"✅ 理解：{analysis.product.understanding}")
    if analysis.product.gaps:
        for gap in analysis.product.gaps:
            lines.append(f"❌ 缺失：{gap}")
    else:
        lines.append("✅ 未发现明显需求缺口")
    if analysis.product.questions:
        lines.append("")
        for q in analysis.product.questions:
            lines.append(f"❓ {q}")
    lines.append("")

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
        instr_lower = analysis.original.lower()
        if '登录' in analysis.original or 'login' in instr_lower or 'auth' in instr_lower:
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

def dual_perspective_analysis(instruction: str, lang: str = "auto", use_llm: bool = True) -> DualAnalysis:
    """
    Run dual-perspective analysis on an instruction.
    
    Uses LLM deep reasoning by default when API key is available.
    Falls back to rule-based analysis if no API key or LLM fails.
    """
    if lang == "auto":
        chinese_chars = sum(1 for c in instruction if '\u4e00' <= c <= '\u9fff')
        english_words = len([w for w in instruction.split() if w.isascii()])
        lang = "zh" if chinese_chars > english_words else "en"
    
    # Try LLM first if enabled
    if use_llm:
        llm_result = dual_perspective_analysis_llm(instruction, lang)
        if llm_result:
            return llm_result
    
    # Fallback: rule-based analysis
    engineer = analyze_engineer(instruction, lang)
    product = analyze_product(instruction, lang)
    conflicts = find_conflicts(engineer, product)
    common_gaps = find_common_gaps(engineer, product)
    confidence, auto_proceed = calculate_confidence(engineer, product)
    
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
