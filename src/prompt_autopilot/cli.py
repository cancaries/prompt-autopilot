"""
Command-line interface for prompt-autopilot.
"""

import sys
import argparse
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from prompt_autopilot import (
    optimize,
    analyze_instruction,
    generate_optimized_versions,
    evaluate_version,
    record_feedback,
    load_preferences,
    save_template,
    list_templates,
    search_templates,
    display_result,
    DisplayStyle,
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
    
    # analyze command  
    anal_parser = subparsers.add_parser("analyze", aliases=["a"], help="Analyze an instruction")
    anal_parser.add_argument("instruction", nargs="*", help="Instruction to analyze")
    
    # feedback command
    fb_parser = subparsers.add_parser("feedback", aliases=["f"], help="Record feedback")
    fb_parser.add_argument("--instruction", "-i", required=True, help="Original instruction")
    fb_parser.add_argument("--choice", "-c", choices=["A", "B", "C"], required=True, help="Which version chosen")
    fb_parser.add_argument("--feedback", help="Feedback text")
    fb_parser.add_argument("--improve", help="What could be improved")
    
    # templates command
    tpl_parser = subparsers.add_parser("templates", aliases=["t"], help="Manage templates")
    tpl_parser.add_argument("--search", "-s", help="Search templates")
    
    # prefs command
    prefs_parser = subparsers.add_parser("prefs", help="Show preferences")
    
    args = parser.parse_args()
    
    # Handle empty args - run interactive mode
    if len(sys.argv) == 1:
        interactive()
        return
    
    # Execute command
    if args.command in ("optimize", "o") or (args.command is None and args.instruction):
        instruction = " ".join(args.instruction) if args.instruction else ""
        if not instruction:
            print("Error: instruction required", file=sys.stderr)
            sys.exit(1)
        
        result = optimize(instruction)
        style = DisplayStyle(args.style) if args.style else DisplayStyle.RICH
        output = display_result(result, style=style, show_all=args.all)
        print(output)
        
        # Ask for feedback
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
        
    elif args.command == "prefs":
        prefs = load_preferences()
        print("\n⚙️  Preferences:\n")
        for k, v in prefs.items():
            if k != "feedback_history":
                print(f"  {k}: {v}")
        print(f"\n  Total feedback entries: {len(prefs.get('feedback_history', []))}")

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
    print("Commands: /optimize, /analyze, /templates, /prefs, /quit")
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
                    print("Usage: /optimize <instruction>")
                    continue
                result = optimize(rest)
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
