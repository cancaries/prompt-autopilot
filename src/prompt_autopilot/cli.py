"""
Command-line interface for prompt-autopilot.
"""

import sys
import argparse
import os
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from prompt_autopilot import (
    optimize,
    optimize_with_llm,
    analyze_instruction,
    generate_optimized_versions,
    evaluate_version,
    record_feedback,
    load_preferences,
    load_config,
    save_config,
    save_template,
    list_templates,
    search_templates,
    display_result,
    DisplayStyle,
)
from prompt_autopilot.dual_perspective import (
    dual_perspective_analysis,
)
from prompt_autopilot.library import (
    save_prompt,
    load_prompt,
    list_prompts,
    search_prompts,
    delete_prompt,
    use_prompt,
    find_similar,
    update_prompt,
)


def main():
    parser = argparse.ArgumentParser(
        description="prompt-autopilot: Auto-optimize prompts, evaluate quality, learn preferences"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # optimize command
    opt_parser = subparsers.add_parser("optimize", aliases=["o"], help="Optimize a prompt")
    opt_parser.add_argument("instruction", nargs="*", help="Instruction to optimize")
    opt_parser.add_argument("--style", choices=["markdown", "rich", "minimal"], default="rich", help="Output style")
    opt_parser.add_argument("--all", action="store_true", help="Show all versions (not just recommended)")
    opt_parser.add_argument("--use-llm", action="store_true", help="Use LLM to generate optimized prompt (requires API key) [deprecated, use --deep]")
    opt_parser.add_argument("--tier", choices=["auto", "fast", "medium", "deep"], default="auto", help="LLM tier selection: auto (default), fast (gpt-3.5), medium (fast model + detailed prompt), deep (gpt-4)")
    opt_parser.add_argument("--fast", action="store_true", help="Force fast LLM (gpt-3.5-turbo)")
    opt_parser.add_argument("--deep", action="store_true", help="Force deep LLM (gpt-4)")
    opt_parser.add_argument("--save", metavar="NAME", help="Save the optimized result to library with given name")

    # analyze command
    anal_parser = subparsers.add_parser("analyze", aliases=["a"], help="Analyze an instruction")
    anal_parser.add_argument("instruction", nargs="*", help="Instruction to analyze")

    # think command - dual perspective analysis
    think_parser = subparsers.add_parser("think", aliases=["th"], help="Deep dual-perspective analysis")
    think_parser.add_argument("instruction", nargs="*", help="Instruction to analyze deeply")
    think_parser.add_argument("--auto", action="store_true", help="Auto-proceed if confident, skip confirmation")

    # feedback command
    fb_parser = subparsers.add_parser("feedback", aliases=["f"], help="Record feedback")
    fb_parser.add_argument("--instruction", "-i", required=True, help="Original instruction")
    fb_parser.add_argument("--choice", "-c", choices=["A", "B", "C"], required=True, help="Which version chosen")
    fb_parser.add_argument("--feedback", help="Feedback text")
    fb_parser.add_argument("--improve", help="What could be improved")

    # templates command (old JSON-based system)
    tpl_parser = subparsers.add_parser("templates", aliases=["t"], help="Manage templates (old system)")
    tpl_parser.add_argument("--search", "-s", help="Search templates")

    # ---- Library commands (new markdown-based system) ----

    # library list
    lib_list_parser = subparsers.add_parser("list", help="List all prompts in library")
    lib_list_parser.add_argument("--tag", "-t", help="Filter by tag")

    # library save
    lib_save_parser = subparsers.add_parser("save", help="Save a prompt to library")
    lib_save_parser.add_argument("name", help="Prompt name (unique identifier)")
    lib_save_parser.add_argument("prompt", nargs="*", help="Prompt content (or use --file)")
    lib_save_parser.add_argument("--tags", "-T", nargs="*", help="Tags for the prompt")
    lib_save_parser.add_argument("--description", "-d", help="Short description")
    lib_save_parser.add_argument("--file", "-f", help="Read prompt from file")

    # library search
    lib_search_parser = subparsers.add_parser("search", help="Search prompts in library")
    lib_search_parser.add_argument("query", nargs="*", help="Search query")
    lib_search_parser.add_argument("--tag", "-t", help="Search within specific tag")

    # library show
    lib_show_parser = subparsers.add_parser("show", help="Show prompt details")
    lib_show_parser.add_argument("name", help="Prompt name")
    lib_show_parser.add_argument("--raw", action="store_true", help="Show raw markdown content")

    # library edit
    lib_edit_parser = subparsers.add_parser("edit", help="Edit a prompt in library")
    lib_edit_parser.add_argument("name", help="Prompt name")
    lib_edit_parser.add_argument("--prompt", "-p", help="New prompt content")
    lib_edit_parser.add_argument("--tags", "-T", nargs="*", help="New tags")
    lib_edit_parser.add_argument("--description", "-d", help="New description")

    # library delete
    lib_delete_parser = subparsers.add_parser("delete", help="Delete a prompt from library")
    lib_delete_parser.add_argument("name", help="Prompt name")
    lib_delete_parser.add_argument("--force", action="store_true", help="Skip confirmation")

    # library use
    lib_use_parser = subparsers.add_parser("use", help="Use a template with new instruction")
    lib_use_parser.add_argument("name", help="Template name")
    lib_use_parser.add_argument("instruction", nargs="*", help="Instruction override")
    lib_use_parser.add_argument("--print", action="store_true", help="Print result instead of passing to stdin")

    # prefs command
    cfg_parser = subparsers.add_parser("config", help="Show/set LLM configuration")
    cfg_parser.add_argument("--api-key", metavar="KEY", help="Set LLM API key")
    cfg_parser.add_argument("--model", metavar="MODEL", help="Set LLM model (e.g., gpt-4)")
    cfg_parser.add_argument("--endpoint", metavar="URL", help="Set LLM endpoint URL")

    prefs_parser = subparsers.add_parser("prefs", help="Show preferences")

    args = parser.parse_args()

    # Handle --set-api-key at top level (before subcommand)
    if "--set-api-key" in sys.argv:
        idx = sys.argv.index("--set-api-key")
        if idx + 1 < len(sys.argv):
            key = sys.argv[idx + 1]
            cfg = load_config()
            cfg["llm_api_key"] = key
            save_config(cfg)
            print(f"✅ API key set: {key[:8]}...{key[-4:]}")
            sys.argv = sys.argv[:idx] + sys.argv[idx + 2:]
        else:
            print("Error: --set-api-key requires a KEY argument", file=sys.stderr)
            sys.exit(1)

    # Handle empty args - run interactive mode
    if len(sys.argv) == 1:
        interactive()
        return

    # ---- Library command handlers ----

    if args.command == "list":
        _cmd_list(args)
        return

    if args.command == "save":
        _cmd_save(args)
        return

    if args.command == "search":
        _cmd_search(args)
        return

    if args.command == "show":
        _cmd_show(args)
        return

    if args.command == "edit":
        _cmd_edit(args)
        return

    if args.command == "delete":
        _cmd_delete(args)
        return

    if args.command == "use":
        _cmd_use(args)
        return

    # ---- Original command handlers ----

    if args.command in ("optimize", "o") or (args.command is None and args.instruction):
        instruction = " ".join(args.instruction) if args.instruction else ""
        if not instruction:
            print("Error: instruction required", file=sys.stderr)
            sys.exit(1)

        # Smart recommendation before optimizing
        similar = find_similar(instruction, top_k=3)
        if similar:
            print(f"\n💡 发现相似模板：{similar[0][0].get('name')} (相似度 {similar[0][1]:.0f}%)")
            for i, (p, score) in enumerate(similar[1:], 2):
                print(f"   {p.get('name')} (相似度 {score:.0f}%)")
            print("   是否基于它修改？ [y/N] ", end="", flush=True)
            try:
                choice = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                choice = "n"
            if choice == "y" and similar:
                template_name = similar[0][0].get("name")
                print(f"\n使用模板: {template_name}")
                result = use_prompt(template_name, instruction)
                if result:
                    print("\n" + "=" * 50)
                    print("📝 基于模板生成的 Prompt:")
                    print("=" * 50)
                    print(result.get("content", ""))
                    ask_feedback(instruction, result)
                    return

        # Determine tier from flags
        tier = "auto"
        if args.fast:
            tier = "fast"
        elif args.deep:
            tier = "deep"
        elif args.use_llm:  # Legacy --use-llm maps to deep
            tier = "deep"
        elif getattr(args, 'tier', None) and args.tier != "auto":
            tier = args.tier

        # Run optimization with tier selection
        result = optimize(instruction, tier=tier)
        style = DisplayStyle(args.style) if args.style else DisplayStyle.RICH
        output = display_result(result, style=style, show_all=args.all)

        # Show tier info
        llm_tier = result.get("llm_tier", "auto")
        tier_info = {"none": "(无 API key，使用模板)", "fast": "(⚡ fast LLM)", "medium": "(⚡ medium LLM)", "deep": "(🧠 deep LLM)", "auto": "(auto)"}
        print(f"\n{tier_info.get(llm_tier, '')}")
        print(output)

        # --save flag
        if getattr(args, "save", None):
            save_name = args.save
            recommended = result.get("recommended_version", {})
            prompt_content = recommended.get("template", "")
            if prompt_content:
                try:
                    tags = _extract_tags(instruction)
                    meta = save_prompt(save_name, prompt_content, tags=tags)
                    print(f"\n✅ 已保存到库: {meta['name']}")
                    print(f"   标签: {', '.join(meta.get('tags', []))}")
                except FileExistsError as e:
                    print(f"\n⚠️  {e}")
                    print("   使用 --force 强制覆盖")
            else:
                print("\n⚠️  没有可保存的内容")

        ask_feedback(instruction, result)

    elif args.command in ("analyze", "a"):
        instruction = " ".join(args.instruction) if args.instruction else ""
        if not instruction:
            print("Error: instruction required", file=sys.stderr)
            sys.exit(1)

        analysis = analyze_instruction(instruction)
        print(f"\n📝 Instruction: {instruction}\n")
        print(f"Word count: {analysis['word_count']}\n")

        if analysis["missing"]:
            print("⚠️  Missing:")
            for m in analysis["missing"]:
                print(f"  - {m}")

        if analysis["assumptions"]:
            print("\n💡 Assumptions:")
            for a in analysis["assumptions"]:
                print(f"  - {a}")

        if analysis["risks"]:
            print("\n⚠️  Risks:")
            for r in analysis["risks"]:
                print(f"  - {r}")

    elif args.command in ("think", "th"):
        instruction = " ".join(args.instruction) if args.instruction else ""
        if not instruction:
            print("Error: instruction required", file=sys.stderr)
            sys.exit(1)

        result = dual_perspective_analysis(instruction)
        print(result.analysis_text)

        if args.auto or result.auto_proceed:
            print("\n✅ 置信度高，直接生成结果...\n")
            opt_result = optimize(instruction)
            print(display_result(opt_result, DisplayStyle.MARKDOWN))
        else:
            print("\n💬 请确认或补充上述问题后，再运行 optimize")
            print("   或者加 --auto 参数强制自动生成")

    elif args.command in ("feedback", "f"):
        choice_map = {"A": 0, "B": 1, "C": 2}
        prefs = record_feedback(
            args.instruction,
            choice_map[args.choice],
            args.feedback,
            args.improve,
        )
        print("✅ Feedback recorded!")
        print(f"Format preference: {prefs['format_preference']}")

    elif args.command in ("templates", "t"):
        if args.search:
            templates = search_templates(args.search)
            print(f"\n🔍 Search results for '{args.search}':\n")
        else:
            templates = list_templates()
            print(f"\n📚 Saved templates ({len(templates)}):\n")

        for t in templates:
            print(f"  • {t['name']} (used {t.get('use_count', 0)}x)")
            if t.get("tags"):
                print(f"    Tags: {', '.join(t['tags'])}")
            print()

    elif args.command == "config":
        cfg = load_config()
        if args.api_key is not None:
            cfg["llm_api_key"] = args.api_key
        if args.model is not None:
            cfg["llm_model"] = args.model
        if args.endpoint is not None:
            cfg["llm_endpoint"] = args.endpoint
        save_config(cfg)
        print("\n⚙️  LLM Config:\n")
        for k, v in cfg.items():
            if k == "llm_api_key":
                display = v[:8] + "..." + v[-4:] if v and len(v) > 12 else "(not set)"
                print(f"  {k}: {display}")
            else:
                print(f"  {k}: {v}")

    elif args.command == "prefs":
        prefs = load_preferences()
        print("\n⚙️  Preferences:\n")
        for k, v in prefs.items():
            if k != "feedback_history":
                print(f"  {k}: {v}")
        print(f"\n  Total feedback entries: {len(prefs.get('feedback_history', []))}")


# =============================================================================
# Library command implementations
# =============================================================================

def _cmd_list(args):
    prompts = list_prompts()
    if args.tag:
        prompts = [p for p in prompts if args.tag in p.get("tags", [])]

    if not prompts:
        print("\n📚 Prompt Library (empty)\n")
        return

    print(f"\n📚 Prompt Library ({len(prompts)} prompts)\n")
    for p in prompts:
        name = p.get("name", "")
        tags = p.get("tags", [])
        usage = p.get("usage_count", 0)
        desc = p.get("description", "")
        print(f"  • {name} (used {usage}x)")
        if tags:
            print(f"    Tags: {', '.join(tags)}")
        if desc:
            print(f"    {desc}")
        print()


def _cmd_save(args):
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            prompt_content = f.read().strip()
    else:
        prompt_content = " ".join(args.prompt) if args.prompt else ""

    if not prompt_content:
        print("Error: prompt content required (positional arg or --file)", file=sys.stderr)
        sys.exit(1)

    tags = args.tags if args.tags else []
    try:
        meta = save_prompt(args.name, prompt_content, tags=tags, description=args.description)
        print(f"✅ Saved: {meta['name']}")
        print(f"   Created: {meta['created']}")
        if tags:
            print(f"   Tags: {', '.join(tags)}")
    except FileExistsError as e:
        print(f"⚠️  {e}", file=sys.stderr)
        print("   Use --force to overwrite", file=sys.stderr)


def _cmd_search(args):
    query = " ".join(args.query) if args.query else ""
    results = search_prompts(query) if query else list_prompts()

    if args.tag:
        results = [p for p in results if args.tag in p.get("tags", [])]

    if not results:
        print(f"\n🔍 No results for '{query}'\n")
        return

    print(f"\n🔍 Search results for '{query}' ({len(results)} found)\n")
    for p in results:
        name = p.get("name", "")
        tags = p.get("tags", [])
        usage = p.get("usage_count", 0)
        content_preview = p.get("content", "")[:80].replace("\n", " ")
        print(f"  • {name} (used {usage}x)")
        print(f"    {content_preview}...")
        if tags:
            print(f"    Tags: {', '.join(tags)}")
        print()


def _cmd_show(args):
    prompt = load_prompt(args.name)
    if not prompt:
        print(f"Prompt '{args.name}' not found in library", file=sys.stderr)
        sys.exit(1)

    if args.raw:
        print(f"# {prompt.get('name')}")
        if prompt.get("tags"):
            print(f"# Tags: {', '.join(prompt['tags'])}")
        print()
        print(prompt.get("content", ""))
        return

    print(f"\n📄 {prompt.get('name')}")
    print("=" * 50)
    if prompt.get("description"):
        print(f"Description: {prompt['description']}")
    if prompt.get("tags"):
        print(f"Tags: {', '.join(prompt['tags'])}")
    print(f"Created: {prompt.get('created', 'unknown')}")
    print(f"Updated: {prompt.get('updated', 'unknown')}")
    print(f"Usage: {prompt.get('usage_count', 0)} times")
    print()
    print("--- Prompt Content ---")
    print(prompt.get("content", ""))


def _cmd_edit(args):
    updated = update_prompt(
        args.name,
        prompt=args.prompt,
        tags=args.tags,
        description=args.description,
    )
    if not updated:
        print(f"Prompt '{args.name}' not found in library", file=sys.stderr)
        sys.exit(1)
    print(f"✅ Updated: {updated['name']}")
    if updated.get("tags"):
        print(f"   Tags: {', '.join(updated['tags'])}")


def _cmd_delete(args):
    if not args.force:
        print(f"Delete '{args.name}' from library? [y/N] ", end="", flush=True)
        try:
            choice = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "n"
        if choice != "y":
            print("Cancelled.")
            return

    deleted = delete_prompt(args.name)
    if deleted:
        print(f"✅ Deleted: {args.name}")
    else:
        print(f"Prompt '{args.name}' not found in library", file=sys.stderr)
        sys.exit(1)


def _cmd_use(args):
    prompt = use_prompt(args.name, " ".join(args.instruction) if args.instruction else "")
    if not prompt:
        print(f"Template '{args.name}' not found in library", file=sys.stderr)
        sys.exit(1)

    content = prompt.get("content", "")
    if args.print:
        print(content)
    else:
        # Pass to stdout for piping (PromptHive pattern)
        print(content)


def _extract_tags(instruction: str) -> list[str]:
    """Extract simple tags from instruction keywords."""
    tag_map = {
        "登录": "auth", "注册": "auth", "认证": "auth", "jwt": "auth",
        "排序": "algorithm", "排序算法": "algorithm",
        "api": "api", "接口": "api",
        "数据库": "database", "sql": "database", "增删改查": "database",
        "缓存": "cache", "lru": "cache",
        "链表": "data-structure", "树": "data-structure", "图": "data-structure",
        "邮件": "writing", "写信": "writing", "文章": "writing",
        "解释": "explanation", "说明": "explanation",
    }
    instruction_lower = instruction.lower()
    found = set()
    for kw, tag in tag_map.items():
        if kw in instruction_lower:
            found.add(tag)
    return sorted(found)


# =============================================================================
# Feedback & Interactive
# =============================================================================

def ask_feedback(instruction: str, result: dict):
    """Ask user for feedback on the optimization."""
    try:
        print("\n" + "=" * 40)
        print("Which version did you prefer? (A/B/C/skip) ", end="", flush=True)
        choice = input().strip().upper()

        if choice in ["A", "B", "C"]:
            print("Any feedback? (optional, press Enter to skip): ", end="", flush=True)
            feedback = input().strip()

            improvement = None
            if feedback:
                print("What could be improved? (optional): ", end="", flush=True)
                improvement = input().strip()

            record_feedback(instruction, ["A", "B", "C"].index(choice), feedback, improvement)
            print("✅ Feedback recorded!")
    except (EOFError, KeyboardInterrupt):
        print()


def interactive():
    """Interactive mode - analyze or optimize any instruction."""
    print("=" * 50)
    print("Prompt Autopilot - Interactive Mode")
    print("=" * 50)
    print("Commands: /optimize, /analyze, /templates, /library, /prefs, /quit")
    print()

    while True:
        try:
            line = input("> ").strip()

            if not line:
                continue

            if line in ["/quit", "/exit", "/q"]:
                break

            if line.startswith("/"):
                cmd = line[1:].split()[0]
                rest = " ".join(line.split()[1:])
            else:
                cmd = "optimize"
                rest = line

            if cmd == "optimize" or cmd == "o":
                if not rest:
                    print("Usage: /optimize <instruction> [--fast|--deep]")
                    continue
                tier = "auto"
                if "--fast" in rest:
                    tier = "fast"
                    rest = rest.replace("--fast", "").strip()
                elif "--deep" in rest:
                    tier = "deep"
                    rest = rest.replace("--deep", "").strip()
                result = optimize(rest, tier=tier)
                print(display_result(result, DisplayStyle.RICH))
                ask_feedback(rest, result)

            elif cmd == "analyze" or cmd == "a":
                if not rest:
                    print("Usage: /analyze <instruction>")
                    continue
                analysis = analyze_instruction(rest)
                print(f"\nWord count: {analysis['word_count']}")
                if analysis["missing"]:
                    print("\n⚠️  Missing:")
                    for m in analysis["missing"]:
                        print(f"  - {m}")

            elif cmd == "templates" or cmd == "t":
                templates = list_templates()
                print(f"\n📚 Templates ({len(templates)}):\n")
                for t in templates:
                    print(f"  • {t['name']} (used {t.get('use_count', 0)}x)")

            elif cmd == "library" or cmd == "lib" or cmd == "l":
                prompts = list_prompts()
                print(f"\n📚 Library ({len(prompts)} prompts):\n")
                for p in prompts:
                    print(f"  • {p.get('name')} (used {p.get('usage_count', 0)}x)")

            elif cmd == "prefs":
                prefs = load_preferences()
                print("\n⚙️  Preferences:\n")
                for k, v in prefs.items():
                    if k != "feedback_history":
                        print(f"  {k}: {v}")

            else:
                print(f"Unknown command: {cmd}")

        except KeyboardInterrupt:
            print("\nBye!")
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()
