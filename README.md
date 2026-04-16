# 🚀 prompt-autopilot

**Turn AI tool output from "templates" to "professional tools"**

> All steps are LLM-powered · No API Key required · Chinese & English

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

## 🧠 LLM Tier System

**All steps are LLM-powered.** The difference is only in model selection:

| Tier | Model | Response Time | Use Case |
|------|-------|--------------|----------|
| ⚡ **fast** | gpt-3.5-turbo | 1-2s | Simple instructions (< 10 words) |
| ⚡ **medium** | gpt-3.5-turbo + detailed prompt | 2-3s | Medium instructions |
| 🧠 **deep** | gpt-4 | 5-10s | Complex instructions (>= 30 words) |

### CLI Usage

```bash
# Auto-select tier based on instruction complexity (default)
pma optimize "做个登录"

# Force fast LLM (gpt-3.5-turbo, ~1-2s)
pma optimize "做个登录" --fast

# Force deep LLM (gpt-4, ~5-10s)
pma optimize "做个登录" --deep

# Explicit tier selection
pma optimize "做个登录" --tier auto|fast|medium|deep
```

---

## 🔐 API Key Configuration (Optional)

For LLM-powered optimization, configure your API key securely:

```bash
# Method 1: Environment variables (recommended)
export PROMPT_AUTOPILOT_API_KEY="sk-..."
export PROMPT_AUTOPILOT_FAST_MODEL="gpt-3.5-turbo"
export PROMPT_AUTOPILOT_DEEP_MODEL="gpt-4"
export PROMPT_AUTOPILOT_ENDPOINT="https://api.openai.com/v1/chat/completions"
```

```bash
# Method 2: Local config file (not committed to git)
# File: ~/.prompt-autopilot/config.json
{
  "llm_api_key": "sk-...",
  "fast_model": "gpt-3.5-turbo",
  "deep_model": "gpt-4",
  "llm_endpoint": "https://api.openai.com/v1/chat/completions"
}
```

**Without API key**: Falls back to built-in smart templates.
**With API key**: All steps use LLM with auto tier selection.

> ⚠️ **Security**: API keys are never committed to git. The `config.json` file and `.env` are in `.gitignore`.

---

## ⭐ Features

- 🧠 **think** — Dual perspective analysis (engineer + product)
- ⚡ **optimize** — LLM-powered with tier selection (fast/medium/deep)
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
