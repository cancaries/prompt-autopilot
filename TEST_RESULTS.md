# Test Results - 2026-04-16 00:07 (Asia/Shanghai)

## Syntax Fix Applied
- Removed orphaned module-level code at lines 315-351 in `src/prompt_autopilot/core.py`
- Committed: `37e3b46 Fix: Remove orphaned module-level code causing SyntaxError`
- CHANGELOG updated

---

## Test Summary (28 cases)

### ✅ WORKING (2 cases)
| # | Prompt | Status | Notes |
|---|--------|--------|-------|
| T6 | 帮我写一个排序算法 | ✅ Pass | Returns actual working code |
| T12 | 用Python实现快速排序 | ✅ Pass | Returns actual working quicksort |

### ⚠️ MAJOR QUALITY ISSUES (26 cases)

#### Category 1: Placeholder Output (Garbage Function Names)
These return `def <garbage_name>(): pass` instead of actual code:
- T1: 写一个Python函数计算斐波那契数列 → function name is "Python函数计算斐波那契数列"
- T8: 请帮我写一个 function 处理 user data → function name is "请function处理userdata"
- T10: 写一个Python函数处理JSON数据 → function name is "Python函数处理JSON数据"
- T11: 写一个Python函数接收JSON数组返回平均值保留2位小数 → function name is "Python函数接收JSON数组返回平均值保留2位小数"
- T13: 用Python实现一个LRU缓存 → placeholder
- T19: 优化这段SQL → function name is "优化这段SQL"
- T23: 用Python实现输入列表输出平方 → function name is "用Python实现输入列表输出平方"
- T27: review这段React代码的性能问题 → function name is "review这段React代码的性能问题"

#### Category 2: Wrong Template Type (Content Mismatch)
- T3: 帮我写一封道歉邮件 → Returns "道歉邮件模板" ✅ Actually works for apology email
- T14: 写一封拒绝面试者的邮件语气专业友善 → Returns "道歉邮件模板" ❌ Should be rejection letter, not apology
- T17: 解释机器学习 → Returns content about "AI是什么" ❌ Topic mismatch

#### Category 3: Template with Placeholders Instead of Real Content
- T4: write a blog post about AI → Returns outline template with [Opening], [Content] placeholders
- T7: explain how blockchain works → Returns outline with [Your definition] placeholders
- T15: 写一段科幻小说开头设定在22世纪火星城市 → Returns outline template, not actual fiction
- T16: 写文献综述摘要关于深度学习在医学影像的应用 → Returns outline template, not actual content
- T18: 写单元测试 → Returns outline template with placeholders
- T22: 帮我写一个🎮游戏脚本 → Returns outline template

#### Category 4: Broken Context Filling
- T24: 给初级工程师解释什么是闭包 → Output contains "给初级工程师闭包是一种[你的理解/定义]" ❌ The prompt is incorrectly inserted into the template

#### Category 5: Garbage/Vague Output
- T2: fix the bug in my code → Returns placeholder
- T9: 写代码 → Returns placeholder
- T20: 做好这个功能 → Returns "**直接回答**：做好这个功能\n\n[基于指令生成的具体内容]"
- T21: AI → Returns garbage
- T25: 给团队发一封关于项目延期的通知 → Returns garbage
- T26: 回复客户投诉订单延迟了5天 → Returns garbage

### Scoring Issues
- All cases show Score: 9.0/10 (A) even when output is garbage - scoring is not discriminative
- The system consistently recommends Version A (Direct) regardless of quality

---

## Root Cause Analysis

The `generate_direct_code` function has specific handlers for:
- Sorting (快排, 排序, quicksort, mergesort) ✅ Works
- Login (登录, login) ✅ Works  
- API (api, 接口) ✅ Works

But it falls through to "Generic" for everything else, which just returns:
```python
def {func_name}():
    pass
```
Where `func_name` is derived from the prompt by removing common words, leaving garbage.

The system needs:
1. More specific handlers (fibonacci, LRU, JSON processing, etc.)
2. OR actual prompt completion using AI (not template-based)
3. Better scoring that penalizes placeholder output

---

## Status: 🔴 26/28 tests FAIL (quality)

The CLI works after syntax fix, but output quality is severely degraded.
