"""
Display formatting for prompt-autopilot using rich.
"""

from enum import Enum
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from .core import OptimizationResult

class DisplayStyle(Enum):
    """Output display style."""
    MARKDOWN = "markdown"      # Plain markdown for AI tool output
    RICH = "rich"              # Rich formatted terminal output
    MINIMAL = "minimal"       # Just the recommended version

def display_result(
    result: OptimizationResult,
    style: DisplayStyle = DisplayStyle.MARKDOWN,
    show_all: bool = True,
) -> str:
    """
    Format optimization result for display.
    
    Args:
        result: Result from optimize()
        style: Display style to use
        show_all: Whether to show all versions or just recommended
    
    Returns:
        Formatted string
    """
    if style == DisplayStyle.MINIMAL:
        return format_minimal(result)
    elif style == DisplayStyle.RICH and HAS_RICH:
        return format_rich(result, show_all)
    else:
        return format_markdown(result, show_all)

def format_minimal(result: OptimizationResult) -> str:
    """Just show the recommended version."""
    rv = result["recommended_version"]
    return f"""{rv['template']}

---
Score: {result['recommended_evaluation']['overall']}/10 ({result['recommended_evaluation']['grade']})
"""

def _format_version_block(version: dict, evaluation: dict) -> list[str]:
    """Format a single version (A/B/C) with its score."""
    lines = []
    vtype = version.get('type', '')
    vdesc = version.get('description', '')
    template = version.get('template', '')
    scores = evaluation.get('scores', {})
    overall = evaluation.get('overall', 0)
    grade = evaluation.get('grade', '')

    lines.append(f"\n{'=' * 52}")
    lines.append(f"📋 {vtype}  {vdesc}")
    lines.append(f"   评分：{overall}/10 ({grade}) · 清晰度 {scores.get('clarity', 0)} · 具体性 {scores.get('specificity', 0)} · 完整性 {scores.get('completeness', 0)}")
    lines.append('=' * 52)

    section_emoji = {
        '任务': '🎯', '输入': '📥', '输出': '📤', '性能': '⚡',
        '边界': '🛡️', '约束': '⚠️', '可选': '🔮', '背景': '📋',
        '受眾': '👥', '受众': '👥', '写作目的': '🎯', '核心信息': '💬',
        '风格': '🎨', '结构': '🏗️', '内容框架': '🗂️', '解释主题': '💡',
        '受众画像': '👤', '解释深度': '🔬', '解释策略': '🧩', '检验理解': '✅',
        '邮件结构': '📧', '语气要求': '✍️', '参考模板': '✅',
    }

    for line in template.split('\n'):
        if line.startswith('## '):
            section_name = line.replace('## ', '').strip()
            emoji = section_emoji.get(section_name, '📌')
            lines.append(f"\n{emoji} {section_name}")
        elif line.startswith('【') and '】' in line:
            section_name = line.strip().lstrip('【').rstrip('】')
            emoji = section_emoji.get(section_name, '📌')
            lines.append(f"{emoji} **{section_name}**")
        elif line.strip():
            lines.append(line)

    return lines


def format_markdown(result: OptimizationResult, show_all: bool = True) -> str:
    """Format as markdown (for AI tool output) — stunning version."""
    versions = result.get('versions', [])
    evaluations = result.get('evaluations', [])
    recommended_idx = result.get('recommended_idx', 0)

    sep = '━' * 49
    lines = []

    # Header
    lines.append(f"{sep}")
    lines.append(f"✨ 优化后的编程指令")
    lines.append(f"{sep}")
    lines.append("")

    if show_all and len(versions) > 1:
        # Show all versions
        for i, (version, evaluation) in enumerate(zip(versions, evaluations)):
            marker = " ✅ 推荐" if i == recommended_idx else ""
            block_lines = _format_version_block(version, evaluation)
            # Add recommendation marker to type line
            block_lines[0] = block_lines[0].replace(
                f"📋 {version.get('type', '')}",
                f"📋 {version.get('type', '')}{marker}"
            )
            lines.extend(block_lines)
        lines.append("")
        lines.append(sep)
    else:
        # Show only recommended version
        rv = result["recommended_version"]
        re_ = result["recommended_evaluation"]
        scores = re_['scores']
        lines.append(
            f"综合 {re_['overall']}/10 · 清晰度 {scores['clarity']} · 具体性 {scores['specificity']} · 完整性 {scores['completeness']}  ✅ 推荐"
        )
        lines.append("")

        template = rv['template']
        section_emoji = {
            '任务': '🎯', '输入': '📥', '输出': '📤', '性能': '⚡',
            '边界': '🛡️', '约束': '⚠️', '可选': '🔮', '背景': '📋',
            '受眾': '👥', '受众': '👥', '写作目的': '🎯', '核心信息': '💬',
            '风格': '🎨', '结构': '🏗️', '内容框架': '🗂️', '解释主题': '💡',
            '受众画像': '👤', '解释深度': '🔬', '解释策略': '🧩', '检验理解': '✅',
            '邮件结构': '📧', '语气要求': '✍️', '参考模板': '✅',
        }

        for line in template.split('\n'):
            if line.startswith('## '):
                section_name = line.replace('## ', '').strip()
                emoji = section_emoji.get(section_name, '📌')
                lines.append(f"\n{emoji} {section_name}")
            elif line.startswith('【') and '】' in line:
                section_name = line.strip().lstrip('【').rstrip('】')
                emoji = section_emoji.get(section_name, '📌')
                lines.append(f"{emoji} **{section_name}**")
            elif line.strip():
                lines.append(line)

        lines.append("")
        lines.append(sep)

    return "\n".join(lines)

def _console_version_block(console, version: dict, evaluation: dict, recommended: bool):
    """Print a single version block to rich console."""
    vtype = version.get('type', '')
    vdesc = version.get('description', '')
    template = version.get('template', '')
    scores = evaluation.get('scores', {})
    overall = evaluation.get('overall', 0)
    grade = evaluation.get('grade', '')
    marker = " ✅ 推荐" if recommended else ""

    sep = '═' * 50
    console.print(f"[bold cyan]{sep}[/]")
    vtype_line = f"[bold]📋 {vtype}{marker}[/bold]  [dim]{vdesc}[/dim]"
    console.print(vtype_line)
    score_line = (f"   评分：{overall}/10 ({grade}) · "
                  f"清晰度 {scores.get('clarity', 0)} · "
                  f"具体性 {scores.get('specificity', 0)} · "
                  f"完整性 {scores.get('completeness', 0)}")
    console.print(f"[yellow]{score_line}[/yellow]")

    section_emoji = {
        '任务': '🎯', '输入': '📥', '输出': '📤', '性能': '⚡',
        '边界': '🛡️', '约束': '⚠️', '可选': '🔮', '背景': '📋',
        '受眾': '👥', '受众': '👥', '写作目的': '🎯', '核心信息': '💬',
        '风格': '🎨', '结构': '🏗️', '内容框架': '🗂️', '解释主题': '💡',
        '受众画像': '👤', '解释深度': '🔬', '解释策略': '🧩', '检验理解': '✅',
        '邮件结构': '📧', '语气要求': '✍️', '参考模板': '✅',
        '进阶要点': '🔍', '高级技巧': '💡',
    }

    current = []
    for line in template.split('\n'):
        if line.startswith('## ') or (line.startswith('【') and '】' in line):
            if current:
                for ln in current:
                    if ln.strip():
                        console.print(f"  {ln}")
                console.print()
            section_name = line.replace('## ', '').replace('【', '').replace('】', '').strip()
            emoji = section_emoji.get(section_name, '📌')
            console.print(f"[bold]{emoji} {section_name}[/bold]")
            current = []
        else:
            current.append(line)
    for ln in current:
        if ln.strip():
            console.print(f"  {ln}")
    console.print()


def format_rich(result: OptimizationResult, show_all: bool = True) -> str:
    """Format with rich (for terminal) — stunning version with A/B/C support."""
    if not HAS_RICH:
        return format_markdown(result, show_all)

    from io import StringIO
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=100)

    versions = result.get('versions', [])
    evaluations = result.get('evaluations', [])
    recommended_idx = result.get('recommended_idx', 0)

    sep = '━' * 49
    console.print(f"[bold cyan]{sep}[/]")
    console.print(f"[bold cyan]✨ 优化后的编程指令[/]")
    console.print(f"[bold cyan]{sep}[/]")
    console.print()

    if show_all and len(versions) > 1:
        for i, (version, evaluation) in enumerate(zip(versions, evaluations)):
            _console_version_block(
                console, version, evaluation,
                recommended=(i == recommended_idx)
            )
        console.print(f"[bold cyan]{sep}[/]")
    else:
        rv = result["recommended_version"]
        re_ = result["recommended_evaluation"]
        scores = re_['scores']
        score_line = (f"综合 {re_['overall']}/10 · 清晰度 {scores['clarity']} · "
                      f"具体性 {scores['specificity']} · 完整性 {scores['completeness']}  ✅ 推荐")
        console.print(f"[yellow]{score_line}[/yellow]")
        console.print()

        section_emoji = {
            '任务': '🎯', '输入': '📥', '输出': '📤', '性能': '⚡',
            '边界': '🛡️', '约束': '⚠️', '可选': '🔮', '背景': '📋',
            '受眾': '👥', '受众': '👥', '写作目的': '🎯', '核心信息': '💬',
            '风格': '🎨', '结构': '🏗️', '内容框架': '🗂️', '解释主题': '💡',
            '受众画像': '👤', '解释深度': '🔬', '解释策略': '🧩', '检验理解': '✅',
            '邮件结构': '📧', '语气要求': '✍️', '参考模板': '✅',
        }

        template = rv['template']
        current = []
        for line in template.split('\n'):
            if line.startswith('## ') or (line.startswith('【') and '】' in line):
                if current:
                    for ln in current:
                        if ln.strip():
                            console.print(f"  {ln}")
                    console.print()
                section_name = line.replace('## ', '').replace('【', '').replace('】', '').strip()
                emoji = section_emoji.get(section_name, '📌')
                console.print(f"[bold]{emoji} {section_name}[/bold]")
                current = []
            else:
                current.append(line)
        for ln in current:
            if ln.strip():
                console.print(f"  {ln}")

        console.print()
        console.print(f"[bold cyan]{sep}[/]")

    return buffer.getvalue()

def format_for_ai_tools(result: OptimizationResult) -> str:
    """
    Format output specifically for AI coding tools (Cursor, Claude Code, etc).
    This format is optimized for readability and immediate use.
    """
    rv = result["recommended_version"]
    re = result["recommended_evaluation"]
    
    lines = []
    lines.append("=" * 60)
    lines.append("PROMPT-AUTOPILOT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"📝 {result['original']}")
    lines.append("")
    
    # Show analysis briefly
    missing = result["analysis"].get("missing", [])
    if missing:
        lines.append("⚠️ Missing: " + " | ".join(missing[:2]))
        lines.append("")
    
    # Show recommended
    lines.append(f"✅ RECOMMENDED (Score: {re['overall']}/10)")
    lines.append("-" * 40)
    lines.append(rv["template"])
    lines.append("-" * 40)
    
    return "\n".join(lines)
