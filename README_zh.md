# prompt-autopilot

**个人测试项目 | 欢迎 Clone/Star/Fork 来评价**

---

## 什么是 prompt-autopilot？

**prompt-autopilot** 是一个与工具无关的提示词优化系统。它能够分析你原始的指令，生成多个优化版本，用质量分数进行评估，并随着时间推移学习你的偏好。

> 🔗 英文说明：[English README](README_en.md)

---

## 功能特点

- 🔍 **分析** — 检测缺失信息、歧义表述、未说明的假设
- ✨ **优化** — 生成 3 个版本：简洁版、详细版、结构化版
- 📊 **评估** — 从清晰度、具体性、完整性三个维度评分（1-10）
- ✅ **推荐** — 选择最佳版本并解释原因
- 🧠 **学习** — 记住你的偏好，下次优化更精准

---

## 快速开始

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

---

## 示例输出

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

## 工作流程

| 步骤 | 描述 |
|------|------|
| **1. 分析** | 检查缺失的上下文、格式、约束条件 |
| **2. 优化** | 生成 3 个版本（简洁/详细/结构化） |
| **3. 评估** | 从清晰度、具体性、完整性评分 |
| **4. 推荐** | 选择最佳版本并说明原因 |
| **5. 学习** | 记住偏好，下次优化更准确 |

---

## 集成方式

可与任何 AI 工具配合使用：

| 工具 | 集成方式 |
|------|---------|
| **OpenClaw** | 放入 `~/.openclaw/skills/prompt-autopilot/` |
| **Cursor** | 添加到 `.cursorrules` |
| **Claude Code** | `--system-prompt` 注入 |
| **Codex** | MCP 服务器集成 |
| **通用 LLM** | 作为独立 CLI 或系统提示词使用 |

详细设置说明请参阅 [INTEGRATION.md](INTEGRATION.md)。

---

## 反馈与贡献

🎯 **欢迎反馈！** 这是一个测试项目，所有建议、问题报告和复刻都非常欢迎。

- ⭐ 觉得有用的话请 Star
- 🍴 欢迎 Fork 创建你自己的版本
- 🐛 通过 GitHub Issues 报告问题
- 💡 分享你的使用场景和改进建议

---

## 许可证

MIT 许可证 — 详见 [LICENSE](LICENSE)。

---

<p align="center">
  <b>⭐ 如果这个项目对你有帮助，请给我一个 Star！⭐</b>
</p>
