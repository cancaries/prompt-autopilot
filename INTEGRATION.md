# Integration with AI Tools

This document explains how to integrate `prompt-autopilot` with various AI coding tools.

## OpenClaw

### Method 1: Skill File

Copy the skill file to your OpenClaw skills directory:

```bash
mkdir -p ~/.openclaw/skills/prompt-autopilot
cp INTEGRATION.md ~/.openclaw/skills/prompt-autopilot/SKILL.md
```

### Method 2: Automatic Invocation

Add to your `BOOTSTRAP.md` or `MEMORY.md`:

```
For any user instruction, run through prompt-autopilot first:
1. Analyze the instruction
2. Generate optimized versions  
3. Evaluate and recommend
4. Apply the recommended version
```

### Method 3: OpenClaw Skill

The skill file at `~/.openclaw/skills/prompt-autopilot/SKILL.md` provides
the complete prompt injection for OpenClaw to automatically optimize any instruction.

## Cursor

### Using .cursorrules

Add to your project's `.cursorrules` file:

```json
{
  "rules": [
    {
      "match": "**/*",
      "skill": {
        "name": "prompt-autopilot",
        "mode": "before"
      }
    }
  ]
}
```

Or as a prompt instruction:

```markdown
## Prompt Optimization

Before responding to any user instruction:

1. Run the instruction through prompt-autopilot
2. Use the recommended version
3. Learn from feedback

Use: `python -m prompt_autopilot optimize "<instruction>"`
```

### Cursor Rules (Cursor App)

In Cursor Settings → Rules, add:

```
You must optimize every instruction before execution:

1. Analyze the instruction for missing information
2. Generate 3 versions (Concise, Detailed, Structured)
3. Evaluate and pick the best
4. Apply it

Run: ~/.prompt-autopilot/run.sh "<instruction>"
```

## Claude Code

### System Prompt Injection

Add to your Claude Code config or use the `--system-prompt` flag:

```bash
claude code --system-prompt "$(cat ~/.openclaw/skills/prompt-autopilot/SKILL.md)"
```

### Alias

Add to your `.zshrc` or `.bashrc`:

```bash
alias claude-a='claude code --system-prompt "Always use prompt-autopilot before responding"'
```

## Codex

### MCP Server Integration

If using Codex with MCP, add to your MCP config:

```json
{
  "mcpServers": {
    "prompt-autopilot": {
      "command": "python",
      "args": ["-m", "prompt_autopilot", "optimize"]
    }
  }
}
```

### In-Project Instruction

Add to your project's `INSTRUCTIONS.md`:

```markdown
# Prompt Optimization

All instructions must be optimized using prompt-autopilot before execution.

Before responding to any request:
1. Analyze: Check for missing context, constraints, format
2. Optimize: Generate improved versions
3. Evaluate: Score each version
4. Apply: Use the best version

Command: `python -m prompt_autopilot optimize "<instruction>"`
```

## VS Code Copilot

### Custom Instruction

In VS Code settings for Copilot:

```json
{
  "copilot.instruction.custom": "Always optimize instructions with prompt-autopilot before execution"
}
```

## Generic Integration

For any AI tool that supports custom instructions or system prompts:

```markdown
## Prompt Optimization Rule

When given an instruction:

1. **Analyze** - Identify what's missing:
   - Context or background?
   - Output format?
   - Constraints or limitations?
   - Target audience?

2. **Optimize** - Generate 3 versions:
   - Version A: Concise (direct, minimal)
   - Version B: Detailed (full context + examples)
   - Version C: Structured (step-by-step)

3. **Evaluate** - Score each (1-10):
   - Clarity: Is the goal clear?
   - Specificity: Are requirements concrete?
   - Completeness: Is everything needed included?

4. **Apply** - Use the highest scoring version

5. **Learn** - Remember preferences for next time
```

## Installation for All Tools

Once installed via pip:

```bash
pip install prompt-autopilot
```

All tools can then use:

```bash
python -m prompt_autopilot optimize "<instruction>"
```

Or for development:

```bash
git clone https://github.com/yourname/prompt-autopilot.git
cd prompt-autopilot
pip install -e .
```
