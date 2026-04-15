# prompt-autopilot

**Auto-optimize prompts, evaluate quality, learn preferences.**

A tool-agnostic system that analyzes your instructions, generates optimized versions, evaluates them, and learns your preferences over time.

Works with any AI coding tool: Cursor, Claude Code, Codex, OpenClaw, GitHub Copilot, or any LLM interface.

---

## Features

- 🔍 **Analyze** — Find missing information, assumptions, and risks in instructions
- ✨ **Optimize** — Generate 3 versions: Concise, Detailed, Structured
- 📊 **Evaluate** — Score each on Clarity, Specificity, Completeness
- ✅ **Recommend** — Pick the best version with explanation
- 🧠 **Learn** — Remember your preferences for future use

---

## Quick Start

```bash
# Install
pip install prompt-autopilot

# Use (CLI)
prompt-autopilot "帮我写一封道歉邮件"

# Or use the shorter alias
pma "fix the bug"
```

---

## Examples

```
$ pma "fix the bug"

============================================================
📝 Original: fix the bug

⚠️ Missing:
  - Very brief - may lack necessary context
  - No output format specified
  - No constraints or limitations stated

✅ Recommended: Version B (Detailed)
   Score: 8.3/10

Write a Python function that:
- Input: JSON array of user objects [{"id": int, "name": str}]
- Processing: Filter users where age >= 18
- Output: List of strings ["name1", "name2"]
- Requirements: Type hints, handle empty list
```

---

## How It Works

| Step | What Happens |
|------|-------------|
| **Analyze** | Check for missing context, format, constraints |
| **Optimize** | Generate 3 versions (Concise/Detailed/Structured) |
| **Evaluate** | Score on Clarity, Specificity, Completeness |
| **Recommend** | Pick the best version with explanation |
| **Learn** | Remember your preferences for next time |

---

## Integration

Works with any AI tool. See [INTEGRATION.md](INTEGRATION.md) for:

- **OpenClaw** — Skill file auto-loaded
- **Cursor** — Add to .cursorrules
- **Claude Code** — System prompt injection
- **Codex** — MCP server integration
- **Generic** — Works as system prompt

---

## Development

```bash
git clone https://github.com/yourname/prompt-autopilot.git
cd prompt-autopilot
pip install -e .
pip install -e ".[dev]"
pytest
```

---

## License

MIT
