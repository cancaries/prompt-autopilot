# prompt-autopilot

**Personal Testing Project | Welcome to Clone/Star/Fork**

---

## What is prompt-autopilot?

**prompt-autopilot** is a tool-agnostic prompt optimization system. It analyzes your raw instructions, generates multiple optimized versions, evaluates them with quality scores, and learns your preferences over time.

> 🔗 Also available in: [中文说明](README_zh.md)

---

## Features

- 🔍 **Analyze** — Detect missing information, ambiguous terms, unstated assumptions
- ✨ **Optimize** — Generate 3 versions: Concise, Detailed, Structured
- 📊 **Evaluate** — Score each on Clarity, Specificity, Completeness (1-10)
- ✅ **Recommend** — Pick the best version with explanation
- 🧠 **Learn** — Remember your preferences for future use

---

## Quick Start

```bash
# Install via pip
pip install prompt-autopilot

# Or install from source
git clone https://github.com/cancaries/prompt-autopilot.git
cd prompt-autopilot
pip install -e .

# Use
prompt-autopilot optimize "帮我写一封道歉邮件"
pma "fix the bug"  # shorter alias

# Interactive mode
prompt-autopilot
```

---

## Example Output

```
$ pma "fix the bug"

============================================================
📝 Original: fix the bug

⚠️ Missing:
  - Very brief - may lack necessary context
  - No output format specified
  - No constraints or limitations stated

✅ Recommended: Version C (Structured)
   Score: 8.0/10 (B)

## Task
fix the bug

## Input
[What I will provide]

## Constraints
- [Limitation 1]
- [Limitation 2]

## Output Format
[Describe expected format]

## Success Criteria
- [Criterion 1]
- [Criterion 2]
```

---

## How It Works

| Step | Description |
|------|-------------|
| **1. Analyze** | Check for missing context, format, constraints |
| **2. Optimize** | Generate 3 versions (Concise/Detailed/Structured) |
| **3. Evaluate** | Score on Clarity, Specificity, Completeness |
| **4. Recommend** | Pick the best version with explanation |
| **5. Learn** | Remember preferences for next time |

---

## Integration

Works with any AI tool:

| Tool | Integration Method |
|------|-------------------|
| **OpenClaw** | Skill file in `~/.openclaw/skills/prompt-autopilot/` |
| **Cursor** | Add to `.cursorrules` |
| **Claude Code** | `--system-prompt` injection |
| **Codex** | MCP server integration |
| **Any LLM** | Works as standalone CLI or system prompt |

See [INTEGRATION.md](INTEGRATION.md) for detailed setup instructions.

---

## Feedback & Contribution

🎯 **Welcome feedback!** This is a testing project, so all suggestions, issues, and forks are welcome.

- ⭐ Star if you find it useful
- 🍴 Fork to create your own version
- 🐛 Report bugs via GitHub Issues
- 💡 Share your use cases and improvement ideas

---

## License

MIT License - See [LICENSE](LICENSE) for details.
