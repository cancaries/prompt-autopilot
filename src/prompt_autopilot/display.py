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

def format_markdown(result: OptimizationResult, show_all: bool = True) -> str:
    """Format as markdown (for AI tool output) — stunning version."""
    rv = result["recommended_version"]
    re = result["recommended_evaluation"]
    e = re
    scores = e['scores']

    # Parse sections from the recommended template to extract emojis
    template = rv['template']
    sections = []
    if '## ' in template:
        for line in template.split('\n'):
            if line.startswith('## '):
                sections.append(line.replace('## ', '').strip())

    # Detect emoji from task type
    task_type = result['analysis'].get('instruction_type', 'general')
    emoji_map = {'code': '🧠', 'writing': '✍️', 'explanation': '💡', 'general': '🎯'}
    title_emoji = emoji_map.get(task_type, '🎯')

    sep = '━' * 49
    lines = []

    # Header
    lines.append(f"{sep}")
    lines.append(f"✨ 优化后的编程指令")
    lines.append(f"{sep}")
    lines.append("")

    # Score line
    lines.append(
        f"综合 {e['overall']}/10 · 清晰度 {scores['clarity']} · 具体性 {scores['specificity']} · 完整性 {scores['completeness']}"
    )
    lines.append("")

    # Emit sections from the template with emoji
    section_emoji = {'任务': '🎯', '输入': '📥', '输出': '📤', '性能': '⚡',
                     '边界': '🛡️', '约束': '⚠️', '可选': '🔮', '背景': '📋',
                     '受眾': '👥', '受众': '👥', '写作目的': '🎯', '核心信息': '💬',
                     '风格': '🎨', '结构': '🏗️', '内容框架': '🗂️', '解释主题': '💡',
                     '受众画像': '👤', '解释深度': '🔬', '解释策略': '🧩', '检验理解': '✅'}

    in_section = False
    current_section = ""
    for line in template.split('\n'):
        if line.startswith('## '):
            # Close previous section
            if in_section:
                lines.append("")
            # Start new section
            section_name = line.replace('## ', '').strip().rstrip('】').lstrip('【')
            emoji = section_emoji.get(section_name, '📌')
            lines.append(f"## {emoji} {section_name}")
            in_section = True
            current_section = section_name
        elif line.startswith('【') and '】' in line:
            # Section label line like 【任务】
            section_name = line.strip().lstrip('【').rstrip('】')
            emoji = section_emoji.get(section_name, '📌')
            lines.append(f"{emoji} **{section_name}**")
        elif line.startswith('- ') or line.startswith('• '):
            lines.append(line)
        elif line.strip() and in_section:
            lines.append(line)
        elif line.strip() and not in_section:
            lines.append(line)
        else:
            if line.strip() == '' and in_section:
                pass  # skip blank within section
            else:
                lines.append(line)

    lines.append("")
    lines.append(sep)

    return "\n".join(lines)

def format_rich(result: OptimizationResult, show_all: bool = True) -> str:
    """Format with rich (for terminal) — stunning version."""
    if not HAS_RICH:
        return format_markdown(result, show_all)

    from io import StringIO
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=100)

    rv = result["recommended_version"]
    re = result["recommended_evaluation"]
    e = re
    scores = e['scores']

    sep = '━' * 49

    # Title block
    console.print(f"[bold cyan]{sep}[/]")
    console.print(f"[bold cyan]✨ 优化后的编程指令[/]")
    console.print(f"[bold cyan]{sep}[/]")
    console.print()

    # Score line
    score_line = (f"综合 {e['overall']}/10 · 清晰度 {scores['clarity']} · "
                  f"具体性 {scores['specificity']} · 完整性 {scores['completeness']}")
    console.print(f"[yellow]{score_line}[/yellow]")
    console.print()

    # Parse template into structured sections
    template = rv['template']
    section_emoji = {
        '任务': '🎯', '输入': '📥', '输出': '📤', '性能': '⚡',
        '边界': '🛡️', '约束': '⚠️', '可选': '🔮', '背景': '📋',
        '受眾': '👥', '受众': '👥', '写作目的': '🎯', '核心信息': '💬',
        '风格': '🎨', '结构': '🏗️', '内容框架': '🗂️', '解释主题': '💡',
        '受众画像': '👤', '解释深度': '🔬', '解释策略': '🧩', '检验理解': '✅',
    }

    # Split into sections
    section_lines = []
    current = []
    for line in template.split('\n'):
        if line.startswith('## ') or (line.startswith('【') and '】' in line):
            if current:
                section_lines.append(('block', current))
            current = [line]
        else:
            current.append(line)
    if current:
        section_lines.append(('block', current))

    for _tag, lines_block in section_lines:
        first = lines_block[0]
        if first.startswith('## '):
            section_name = first.replace('## ', '').strip()
            emoji = section_emoji.get(section_name, '📌')
            console.print(f"[bold]{emoji} {section_name}[/bold]")
            for ln in lines_block[1:]:
                if ln.strip():
                    console.print(f"  {ln}")
        elif first.startswith('【'):
            section_name = first.strip().lstrip('【').rstrip('】')
            emoji = section_emoji.get(section_name, '📌')
            console.print(f"[bold]{emoji} {section_name}[/bold]")
            for ln in lines_block[1:]:
                if ln.strip():
                    console.print(f"  {ln}")
        else:
            for ln in lines_block:
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
