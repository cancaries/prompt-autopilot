# 🚀 prompt-autopilot

**Turn AI tool output from "templates" to "professional tools"**

> No API Key required · Ready to use · Chinese & English

[中文说明](README_zh.md) · [English](README_en.md) · [Integration Guide](INTEGRATION.md) · [License](LICENSE)

---

## ⚡ See It In Action

```
$ pma "帮我写排序算法"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ 优化后的编程指令
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 任务
用 Python 实现快速排序算法

## 📥 输入
类型：整数数组，范围：1-100000，示例：[3, 6, 8, 10, 1, 2, 1]

## 📤 输出
类型：整数数组（升序），示例：[1, 1, 2, 3, 6, 8, 10]

## ⚡ 性能
时间：O(n log n) | 空间：O(log n)

## 🛡️ 边界
空数组 → [] | 单元素 → [x] | 重复 → 保持相对顺序

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Score: 9.0/10
```

---

## 📦 Quick Start

```bash
pip install prompt-autopilot

# Core commands
pma think "做个登录功能"    # Dual-perspective analysis
pma optimize "写排序算法"   # Smart optimization
```

---

## 🔐 API Key Configuration (Optional)

For enhanced LLM-powered optimization, configure your API key securely:

```bash
# Method 1: Environment variables (recommended)
export PROMPT_AUTOPILOT_API_KEY="sk-..."
export PROMPT_AUTOPILOT_MODEL="gpt-4"
export PROMPT_AUTOPILOT_ENDPOINT="https://api.openai.com/v1/chat/completions"

# Then use --use-llm flag
prompt-autopilot optimize "做个登录功能" --use-llm
prompt-autopilot think "帮我写排序算法" --use-llm
```

```bash
# Method 2: Local config file (not committed to git)
# File: ~/.prompt-autopilot/config.json
{
  "llm_api_key": "sk-...",
  "llm_model": "gpt-4",
  "llm_endpoint": "https://api.openai.com/v1/chat/completions"
}

# Then use --use-llm flag
prompt-autopilot optimize "做个登录功能" --use-llm
```

**Priority**: Environment variables > Config file > Defaults

> ⚠️ **Security**: API keys are never committed to git. The `config.json` file and `.env` are in `.gitignore`.

---

## ⭐ Features

- 🧠 **think** — Dual perspective analysis (engineer + product)
- ✨ **optimize** — Intelligent inference with professional output
- 📊 **analyze** — Quick gap detection
- 🎯 **No API Key needed** — Built-in smart inference engine
- 🔧 **Category-aware** — Code, writing, explanation, Q&A
- 🔐 **Secure** — API key via env vars or local config, never in git

---

## 🔗 Links

- [📖 Chinese README](README_zh.md)
- [📖 Integration Guide](INTEGRATION.md)
- [📖 License](LICENSE)
- [🐛 Issues](https://github.com/cancaries/prompt-autopilot/issues)

---

<p align="center"><b>⭐ Star if useful!</b></p>
