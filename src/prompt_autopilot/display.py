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
    """Format as markdown (for AI tool output)."""
    lines = []
    
    # Header
    lines.append("# 📝 Prompt Autopilot\n")
    
    # Original
    lines.append(f"**Original:** {result['original']}\n")
    
    # Analysis
    analysis = result["analysis"]
    if analysis["missing"]:
        lines.append("## 🔍 Analysis\n")
        for item in analysis["missing"]:
            lines.append(f"- ⚠️ {item}")
        lines.append("")
    
    # Versions
    if show_all:
        lines.append("## ✨ Optimized Versions\n")
        for i, (v, e) in enumerate(zip(result["versions"], result["evaluations"])):
            marker = "✅ " if i == result["recommended_idx"] else "   "
            lines.append(f"{marker}**Version {v['type']}** ({v['description']})")
            lines.append(f"   Score: {e['overall']}/10 ({e['grade']}) | ", ending="")
            lines.append(f"C={e['scores']['clarity']} S={e['scores']['specificity']} O={e['scores']['completeness']}\n")
        lines.append("")
    
    # Recommended
    rv = result["recommended_version"]
    re = result["recommended_evaluation"]
    lines.append(f"## ✅ Recommended: Version {rv['type']}\n")
    lines.append(f"**Score:** {re['overall']}/10 ({re['grade']})\n")
    lines.append(f"```\n{rv['template']}\n```\n")
    
    # Why recommended
    analysis = result["analysis"]
    missing = analysis.get("missing", [])
    if missing:
        lines.append(f"**Why this version:**\n")
        for m in missing[:2]:
            lines.append(f"- Addresses: {m}\n")
    
    return "".join(lines)

def format_rich(result: OptimizationResult, show_all: bool = True) -> str:
    """Format with rich (for terminal)."""
    if not HAS_RICH:
        return format_markdown(result, show_all)
    
    from io import StringIO
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True)
    
    # Title
    console.print(Panel.fit("[bold cyan]Prompt Autopilot[/]", border_style="cyan"))
    
    # Original instruction
    console.print(f"\n[dim]Original:[/dim] {result['original']}")
    
    # Analysis
    analysis = result["analysis"]
    if analysis["missing"]:
        console.print("\n[yellow]🔍 Analysis[/yellow]")
        for item in analysis["missing"]:
            console.print(f"  ⚠️  {item}")
    
    # Versions table
    if show_all:
        console.print("\n[cyan]✨ Optimized Versions[/cyan]")
        table = Table(show_header=True)
        table.add_column("", style="cyan")
        table.add_column("Version", style="white")
        table.add_column("Score", justify="right")
        table.add_column("C", justify="right")
        table.add_column("S", justify="right")
        table.add_column("O", justify="right")
        
        for i, (v, e) in enumerate(zip(result["versions"], result["evaluations"])):
            marker = "✅" if i == result["recommended_idx"] else "  "
            table.add_row(
                marker,
                v["type"],
                f"{e['overall']}/10 ({e['grade']})",
                str(e['scores']['clarity']),
                str(e['scores']['specificity']),
                str(e['scores']['completeness']),
            )
        
        console.print(table)
    
    # Recommended
    rv = result["recommended_version"]
    re = result["recommended_evaluation"]
    
    console.print(f"\n[bold green]✅ Recommended: {rv['type']}[/bold green]")
    console.print(f"[dim]Score:[/dim] {re['overall']}/10 ({re['grade']})")
    
    # Format the template nicely
    lines = rv["template"].split("\n")
    formatted = "\n".join(f"  {line}" for line in lines)
    console.print(f"\n[white]{formatted}[/white]\n")
    
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
