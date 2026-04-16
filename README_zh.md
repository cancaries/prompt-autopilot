# 🚀 prompt-autopilot

**让 AI 工具的输出从"模板"变成"专业工具"**

> 所有环节都是 LLM 驱动 · 无需 API Key 也能用 · 中英双语

[![GitHub stars](https://img.shields.io/github/stars/cancaries/prompt-autopilot?style=flat-square)](https://github.com/cancaries/prompt-autopilot)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## ⚡ 先看效果

```
$ pma "帮我写排序算法"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ 优化后的编程指令
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 任务
用 Python 实现快速排序算法

## 📥 输入
类型：整数数组
范围：长度 1-100000，元素 0-10^9
示例：[3, 6, 8, 10, 1, 2, 1]

## 📤 输出
类型：整数数组（升序）
示例：[1, 1, 2, 3, 6, 8, 10]

## ⚡ 性能
时间：O(n log n) 平均 | 空间：O(log n)

## 🛡️ 边界
- 空数组 → []
- 单元素 → [x]
- 重复元素 → 保持相对顺序

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
综合 9.0/10 · 清晰度 9 · 具体性 9 · 完整性 9
```

---

## 📦 安装（30 秒上手）

```bash
# 方式一：pip 安装（推荐）
pip install prompt-autopilot

# 方式二：源码安装
git clone https://github.com/cancaries/prompt-autopilot.git
cd prompt-autopilot
pip install -e .
```

**无需配置 API Key**，开箱即用！

---

## 🧠 LLM 分层系统

**所有环节都是 LLM 驱动。** 区别只是模型选择：

| 层级 | 模型 | 响应时间 | 适用场景 |
|------|------|---------|---------|
| ⚡ **fast** | gpt-3.5-turbo | 1-2秒 | 简单指令（< 10 词） |
| ⚡ **medium** | gpt-3.5 + 详细prompt | 2-3秒 | 中等指令 |
| 🧠 **deep** | gpt-4 | 5-10秒 | 复杂指令（>= 30 词） |

### CLI 用法

```bash
# 自动选择层级（默认）
pma optimize "做个登录"

# 强制快速 LLM（gpt-3.5，~1-2秒）
pma optimize "做个登录" --fast

# 强制深度 LLM（gpt-4，~5-10秒）
pma optimize "做个登录" --deep

# 显式指定层级
pma optimize "做个登录" --tier auto|fast|medium|deep
```

### 自动选择规则

```python
# < 10 词 → fast
# < 30 词 → medium
# >= 30 词 → deep
```

---

## 🎯 核心功能

### 1. `think` — 双视角深度分析

```bash
pma think "做个登录功能"
```

从**工程师视角**和**产品视角**同时分析同一个指令，找出双方都忽略的问题。

| 视角 | 关注点 |
|------|--------|
| 🔧 工程师视角 | 技术完整性、语言/框架/数据库/错误处理 |
| 🎯 产品视角 | 用户真正需要什么、可能遗漏的需求 |

### 2. `optimize` — LLM 优化 + 专业输出

```bash
pma optimize "帮我写排序算法"
pma optimize "写一封给投资人的邮件"
```

**所有环节都是 LLM 驱动**，结合智能推断引擎，常见任务自动补充默认值，不再输出空白占位符。

### 3. `analyze` — 快速分析

```bash
pma analyze "解释一下区块链"
```

快速检测缺失的要素。

---

## 💡 对比：Before / After

| 场景 | Before（模板） | After（专业） |
|------|---------------|--------------|
| 排序 | `【约束】输入：整数数组` | `【输入】类型：整数数组，范围：长度 1-100000，示例：[3,1,2]` |
| 登录 | `【约束】[请补充认证方式]` | `【认证】JWT，bcrypt 哈希，24h 有效期，密码重置` |
| 写邮件 | `【受众】[描述目标读者]` | `【受众】30-40岁投资人，关注ROI，数据驱动` |
| 解释概念 | `【受众】[受众背景]` | `【受众】非技术背景的职场人士，用银行转账做类比` |

---

## 🎨 支持的任务类型

| 类型 | 示例输入 | 推断内容 |
|------|---------|---------|
| **排序算法** | `帮我写排序` | Python, O(n log n), 边界情况 |
| **登录/认证** | `做个登录功能` | JWT + bcrypt + PostgreSQL |
| **API 接口** | `写个API` | RESTful, JSON, 参数校验, JWT 认证 |
| **LRU 缓存** | `实现缓存` | O(1), get/put, 容量限制 |
| **数据库操作** | `增删改查` | SQL, 防注入, 事务处理 |
| **写作任务** | `写一封邮件` | 受众 + 目的 + 语气 + 核心要点 |
| **概念解释** | `解释区块链` | 受众背景 + 类比场景 + 核心概念 |

---

## 🔧 高级用法

### 配置 API Key（可选，启用 LLM 生成）

```bash
# 设置 OpenAI API Key
pma config --api-key sk-xxx --model gpt-4

# 强制使用深度 LLM（gpt-4）
pma optimize "帮我写个功能" --deep

# 自动选择（默认）
pma optimize "帮我写个功能"
```

**不配置 API Key**：使用内置智能模板
**配置 API Key**：所有环节使用 LLM，自动选择层级

### 配置文件

```json
// ~/.prompt-autopilot/config.json
{
  "llm_api_key": "sk-...",
  "fast_model": "gpt-3.5-turbo",
  "deep_model": "gpt-4",
  "llm_endpoint": "https://api.openai.com/v1/chat/completions"
}
```

### 交互模式

```bash
pma
# 进入交互模式，输入任意指令
```

### 记录反馈（学习你的偏好）

```bash
pma feedback -i "帮我写排序" -c B --feedback "A太简单，C太复杂"
```

---

## 🏗️ 与其他工具集成

| 工具 | 集成方式 |
|------|---------|
| **Cursor** | 添加到 `.cursorrules` |
| **Claude Code** | `--system-prompt` 注入 |
| **VS Code Copilot** | 作为 Snippet 使用 |
| **OpenClaw** | 放入 `~/.openclaw/skills/prompt-autopilot/` |

详见 [INTEGRATION.md](INTEGRATION.md)。

---

## 🆚 为什么不直接让 AI 写代码？

| | 直接问 AI | prompt-autopilot |
|---|---|---|
| 登录功能 | `帮我做个登录功能` | 得到模糊答案 |
| **prompt-autopilot** | 先问清楚：用什么认证？数据库？注册功能要不要？ | 得到完整专业答案 |
| 排序算法 | `写个排序` | 得到缺边界的代码 |
| **prompt-autopilot** | 自动推断：O(n log n)、空数组/重复元素的处理 | 得到可直接提交的代码 |

---

## 📂 项目结构

```
prompt-autopilot/
├── src/prompt_autopilot/
│   ├── core.py              # 核心逻辑 + LLM 分层系统
│   ├── display.py           # 格式化输出
│   ├── dual_perspective.py   # 双视角分析系统
│   └── cli.py               # 命令行入口
├── README_zh.md             # 本文档
├── INTEGRATION.md           # 集成指南
└── LICENSE                  # MIT
```

---

## 🤝 贡献

欢迎 Star、Fork、提 Issue！

```bash
git clone https://github.com/cancaries/prompt-autopilot.git
cd prompt-autopilot
pip install -e .[dev]
pytest
```

---

## 📜 许可证

MIT License · 详见 [LICENSE](LICENSE)

---

<p align="center">
  <b>⭐ 如果对你有帮助，请给一个 Star！⭐</b>
</p>
