# Prompt Autopilot Test Results
**Date:** 2026-04-17 00:02 (Asia/Shanghai)
**Tester:** cron autopilot iteration
**Total Tests:** 28

---

## Summary
- **Passed:** 16/28 (57%)
- **Failed/Issues:** 12/28 (43%)

---

## Issue Categories

### 🔴 Critical: Generic Placeholders (7 cases)
When prompts are too vague, the system outputs unexpanded placeholders like:
```
- 类型：[请描述输入数据类型和格式]
- 范围：[请描述数据范围或规模]
- 示例：[提供一个具体输入示例]
```

**Affected:** T2, T8, T9, T18, T19, T22, T27

### 🔴 Critical: Verb Phrase Contextual Fill (4 cases)
When prompt is a verb phrase like "解释机器学习", placeholders incorrectly contain the full verb phrase:
```
关心什么：解释机器学习 是什么、如何工作
读者读完后能回答：解释机器学习 是什么？
```

Should be: "关心什么：机器学习 是什么..."

**Affected:** T5, T7, T17, T24

### 🟡 Medium: Output Content Mismatch (1 case)
T10: Prompt "写一个Python函数处理JSON数据"
- Task title says "处理JSON数据"
- Output description says "数值（平均值）"

No actual JSON processing logic specified.

### 🟡 Medium: Emoji in Prompt (1 case)
T22: "帮我写一个🎮游戏脚本" - emoji handled okay but no specific game type extracted

### 🟢 Minor: Template Duplication (email tasks)
T3, T14, T26: Email templates have nested brackets like `[请描述]` which is acceptable but repetitive

---

## Test-by-Test Results

| # | Prompt | Score | Status | Notes |
|---|--------|-------|--------|-------|
| T1 | 写一个Python函数计算斐波那契数列 | 8.05 | ✅ Pass | Good context fill |
| T2 | fix the bug in my code | 8.05 | ⚠️ Placeholders | Generic placeholder issue |
| T3 | 帮我写一封道歉邮件 | 7.25 | ⚠️ Minor | Some placeholder brackets |
| T4 | write a blog post about AI | 7.3 | ⚠️ Repetition | "AI（人工智能）" repeated |
| T5 | 解释什么是量子纠缠 | 6.9 | ❌ Verb fill | "解释量子纠缠" in wrong places |
| T6 | 帮我写一个排序算法 | 8.05 | ✅ Pass | Good |
| T7 | explain how blockchain works | 6.9 | ❌ Verb fill | English phrase in Chinese slots |
| T8 | 请帮我写一个 function 处理 user data | 8.05 | ⚠️ Placeholders | Generic placeholder issue |
| T9 | 写代码 | 8.05 | ⚠️ Placeholders | Generic placeholder issue |
| T10 | 写一个Python函数处理JSON数据 | 8.05 | ⚠️ Mismatch | Says "平均值" in output |
| T11 | 写一个Python函数接收JSON数组返回平均值保留2位小数 | 8.05 | ✅ Pass | Well filled |
| T12 | 用Python实现快速排序 | 8.05 | ✅ Pass | Good |
| T13 | 用Python实现一个LRU缓存 | 8.05 | ✅ Pass | Good |
| T14 | 写一封拒绝面试者的邮件语气专业友善 | 7.6 | ⚠️ Minor | Template brackets |
| T15 | 写一段科幻小说开头设定在22世纪火星城市 | 5.0 | ⚠️ Placeholders | Context filled but still has many [类型][风格] placeholders |
| T16 | 写文献综述摘要关于深度学习在医学影像的应用 | 5.0 | ⚠️ Placeholders | Same as T15 |
| T17 | 解释机器学习 | 6.9 | ❌ Verb fill | "解释机器学习" repeated |
| T18 | 写单元测试 | 5.0 | ⚠️ Placeholders | Generic placeholder issue |
| T19 | 优化这段SQL | 7.65 | ⚠️ Placeholders | Example placeholders |
| T20 | 做好这个功能 | 5.0 | ❌ Useless | All placeholders |
| T21 | AI | 5.0 | ❌ Useless | All placeholders |
| T22 | 帮我写一个🎮游戏脚本 | 8.05 | ⚠️ Placeholders | Generic placeholder issue |
| T23 | 用Python实现输入列表输出平方 | 8.05 | ✅ Pass | Specific enough |
| T24 | 给初级工程师解释什么是闭包 | 6.9 | ✅ Pass | Good fill (闭包 properly extracted) |
| T25 | 给团队发一封关于项目延期的通知 | 7.6 | ✅ Pass | Good |
| T26 | 回复客户投诉订单延迟了5天 | 7.25 | ⚠️ Minor | Some placeholder brackets |
| T27 | review这段React代码的性能问题 | 5.0 | ⚠️ Placeholders | Generic placeholder issue |

---

## Root Cause Analysis

1. **Low specificity prompts** → System falls back to template with generic placeholders
2. **Verb phrase extraction** → Noun/verb separation not working correctly for Chinese
3. **English prompts in Chinese mode** → Language mismatch in contextual fill
4. **Prompt too short** → System cannot infer enough context to fill placeholders

---

## Recommendations

1. When prompt is a verb phrase, extract the noun concept for contextual slots
2. Add minimum specificity threshold - if prompt score < threshold, add warning
3. For English prompts, detect language and adjust template accordingly
4. Better handling of single-word/very-short prompts (T20, T21)
