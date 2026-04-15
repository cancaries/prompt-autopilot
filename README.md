# prompt-autopilot

[English](#english) | [中文](#中文)

---

## English

### What is prompt-autopilot?

**prompt-autopilot** is a tool-agnostic prompt optimization system. It analyzes your raw instructions, generates multiple optimized versions, evaluates them with quality scores, and learns your preferences over time.

**Personal Testing Project | Welcome to Clone/Star/Fork**

This is my personal project for testing and improving LLM instruction quality. I'm sharing it openly for the community to evaluate, fork, and provide feedback.

### Features

- 🔍 **Analyze** — Detect missing information, ambiguous terms, unstated assumptions
- ✨ **Optimize** — Generate 3 versions: Concise, Detailed, Structured
- 📊 **Evaluate** — Score each on Clarity, Specificity, Completeness (1-10)
- ✅ **Recommend** — Pick the best version with explanation
- 🧠 **Learn** — Remember your preferences for future use

### Quick Start

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

### Example Output

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

### How It Works

| Step | Description |
|------|-------------|
| **1. Analyze** | Check for missing context, format, constraints |
| **2. Optimize** | Generate 3 versions (Concise/Detailed/Structured) |
| **3. Evaluate** | Score on Clarity, Specificity, Completeness |
| **4. Recommend** | Pick the best version with explanation |
| **5. Learn** | Remember preferences for next time |

### Integration

Works with any AI tool:

| Tool | Integration Method |
|------|-------------------|
| **OpenClaw** | Skill file in `~/.openclaw/skills/prompt-autopilot/` |
| **Cursor** | Add to `.cursorrules` |
| **Claude Code** | `--system-prompt` injection |
| **Codex** | MCP server integration |
| **Any LLM** | Works as standalone CLI or system prompt |

See [INTEGRATION.md](INTEGRATION.md) for detailed setup instructions.

### Feedback & Contribution

🎯 **Welcome feedback!** This is a testing project, so all suggestions, issues, and forks are welcome.

- ⭐ Star if you find it useful
- 🍴 Fork to create your own version
- 🐛 Report bugs via GitHub Issues
- 💡 Share your use cases and improvement ideas

### License

MIT License - See [LICENSE](LICENSE) for details.

---

## 中文

### 什么是 prompt-autopilot？

**prompt-autopilot** 是一个与工具无关的提示词优化系统。它能够分析你原始的指令，生成多个优化版本，用质量分数进行评估，并随着时间推移学习你的偏好。

**个人测试项目 | 欢迎 Clone/Star/Fork**

这是我个人的测试项目，用于提升 LLM 指令质量。我公开分享这个项目，欢迎社区来评价、复刻和反馈。

### 功能特点

- 🔍 **分析** — 检测缺失信息、歧义表述、未说明的假设
- ✨ **优化** — 生成 3 个版本：简洁版、详细版、结构化版
- 📊 **评估** — 从清晰度、具体性、完整性三个维度评分（1-10）
- ✅ **推荐** — 选择最佳版本并解释原因
- 🧠 **学习** — 记住你的偏好，下次优化更精准

### 快速开始

```bash
# pip 安装
pip install prompt-autopilot

# 或从源码安装
git clone https://github.com/cancaries/prompt-autopilot.git
cd prompt-autopilot
pip install -e .

# 使用
prompt-autopilot optimize "帮我写一封道歉邮件"
pma "fix the bug"  # 短命令别名

# 交互模式
prompt-autopilot
```

### 示例输出

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

### 工作流程

| 步骤 | 描述 |
|------|------|
| **1. 分析** | 检查缺失的上下文、格式、约束条件 |
| **2. 优化** | 生成 3 个版本（简洁/详细/结构化） |
| **3. 评估** | 从清晰度、具体性、完整性评分 |
| **4. 推荐** | 选择最佳版本并说明原因 |
| **5. 学习** | 记住偏好，下次优化更准确 |

### 集成方式

可与任何 AI 工具配合使用：

| 工具 | 集成方式 |
|------|---------|
| **OpenClaw** | 放入 `~/.openclaw/skills/prompt-autopilot/` |
| **Cursor** | 添加到 `.cursorrules` |
| **Claude Code** | `--system-prompt` 注入 |
| **Codex** | MCP 服务器集成 |
| **通用 LLM** | 作为独立 CLI 或系统提示词使用 |

详细设置说明请参阅 [INTEGRATION.md](INTEGRATION.md)。

### 反馈与贡献

🎯 **欢迎反馈！** 这是一个测试项目，所有建议、问题报告和复刻都非常欢迎。

- ⭐ 觉得有用的话请 Star
- 🍴 欢迎 Fork 创建你自己的版本
- 🐛 通过 GitHub Issues 报告问题
- 💡 分享你的使用场景和改进建议

### 许可证

MIT 许可证 — 详见 [LICENSE](LICENSE)。

---

<p align="center">
  <b>⭐ 如果这个项目对你有帮助，请给我一个 Star！⭐</b><br>
  <b>If this project is helpful to you, please give it a Star!</b>
</p>
