# Prompt Autopilot Test Plan

## Overview

This document defines the comprehensive test suite for prompt-autopilot.
The supervisor runs these tests periodically and iterates based on results.

---

## Test Categories

### Category 1: Instruction Type (5 tests)

| ID | Test Case | Instruction | Expected Type |
|----|-----------|-------------|---------------|
| T1 | Code - Function | `写一个Python函数计算斐波那契数列` | code |
| T2 | Code - Debug | `fix the bug in my code` | code |
| T3 | Writing - Email | `帮我写一封道歉邮件` | writing |
| T4 | Writing - Article | `write a blog post about AI` | writing |
| T5 | Explanation | `解释什么是量子纠缠` | explanation |

### Category 2: Language (3 tests)

| ID | Test Case | Instruction | Expected Lang |
|----|-----------|-------------|---------------|
| T6 | Chinese | `帮我写一个排序算法` | zh |
| T7 | English | `explain how blockchain works` | en |
| T8 | Mixed | `请帮我写一个 function 处理 user data` | mixed |

### Category 3: Complexity (4 tests)

| ID | Test Case | Instruction | Complexity |
|----|-----------|-------------|------------|
| T9 | Very Brief | `写代码` | minimal |
| T10 | Medium | `写一个Python函数处理JSON数据` | medium |
| T11 | Detailed | `写一个Python函数，接收一个JSON数组，每个元素有name和age字段，返回age>18的所有name，用列表推导式实现` | high |
| T12 | With Constraints | `写一个函数，接收数字列表返回平均值，要求：1.处理空列表 2.保留2位小数 3.用类型注解` | with-constraints |

### Category 4: Domain (4 tests)

| ID | Test Case | Instruction | Domain |
|----|-----------|-------------|--------|
| T13 | Technical | `用Python实现一个LRU缓存` | technical |
| T14 | Business | `写一封拒绝面试者的邮件，语气专业友善` | business |
| T15 | Creative | `写一段科幻小说开头，200字，设定在22世纪火星城市` | creative |
| T16 | Academic | `写文献综述的摘要部分，关于深度学习在医学影像的应用，300词` | academic |

### Category 5: Common Failure Modes (4 tests)

| ID | Test Case | Instruction | Missing Element |
|----|-----------|-------------|----------------|
| T17 | No Format | `解释机器学习` | output format |
| T18 | No Audience | `写单元测试` | audience |
| T19 | No Constraints | `优化这段SQL` | constraints |
| T20 | Vague | `做好这个功能` | everything vague |

### Category 6: Edge Cases (4 tests)

| ID | Test Case | Instruction | Edge Type |
|----|-----------|-------------|-----------|
| T21 | Very Short | `AI` | minimal (<5 chars) |
| T22 | With Emoji | `帮我写一个🎮游戏脚本` | special chars |
| T23 | With Code Block | `用Python实现：输入列表[1,2,3]，输出[1,4,9]` | inline code |
| T24 | Multi-line | `第一行写函数\n第二行写文档字符串\n第三行写测试` | multi-line |

### Category 7: Real-World Scenarios (4 tests)

| ID | Test Case | Instruction | Scenario |
|----|-----------|-------------|--------|
| T25 | Senior Dev to Junior | `给初级工程师解释什么是闭包` | teaching |
| T26 | Manager to Team | `给团队发一封关于项目延期的通知` | workplace |
| T27 | Customer Service | `回复客户投诉：订单延迟了5天` | service |
| T28 | Code Review | `review这段React代码的性能问题` | review |

---

## Expected Output Quality

### For Each Test

1. **Analysis** should identify:
   - Missing elements (context, format, constraints, audience)
   - Assumptions being made
   - Potential failure modes

2. **Versions** should:
   - Be contextually appropriate for instruction type
   - Have smart fill-in-the-blank placeholders (not generic)
   - Match the detected language (zh/en/mixed)

3. **Recommendation** should:
   - Choose appropriate version for instruction type
   - Score consistently (no huge variance)
   - Explain why this version was chosen

---

## Scoring Rubric

### Analysis Quality (1-10)
- Correctly identifies missing elements: +2 per element
- Doesn't falsely flag complete instructions: +5
- Language detection correct: +3

### Template Quality (1-10)
- Uses context-appropriate fillers: +3
- No duplicate prefixes: +3
- Language matches instruction: +2
- Completeness of placeholders: +2

### Recommendation Quality (1-10)
- Correct version for instruction type: +5
- Score within reasonable range of other versions: +3
- Explains reasoning: +2

---

## Test Execution

### Full Test (28 cases)
```bash
cd ~/programs/prompt-autopilot

# Run all tests and save output
for i in {1..28}; do
  echo "=== T$i ===" >> test_results.md
  prompt-autopilot optimize "$(get_test_instruction T$i)" --style markdown >> test_results.md 2>&1
done
```

### Quick Test (8 core cases)
```bash
prompt-autopilot optimize "写一个Python函数" --style markdown
prompt-autopilot optimize "帮我写道歉邮件" --style markdown
prompt-autopilot optimize "explain quantum entanglement" --style markdown
prompt-autopilot optimize "fix the bug" --style markdown
prompt-autopilot optimize "写代码" --style markdown
prompt-autopilot optimize "用Python实现快速排序" --style markdown
prompt-autopilot optimize "给团队写项目延期通知" --style markdown
prompt-autopilot optimize "AI是什么" --style markdown
```

---

## Iteration Triggers

Run full test when:
- Adding new instruction type support
- Modifying template generation
- Adding new language support
- Before major releases

Run quick test when:
- Periodic maintenance (every 6 hours)
- After bug fixes
- Before pushing to GitHub

---

## Success Criteria

| Metric | Target | Acceptable |
|--------|--------|------------|
| Error-free execution | 100% | 90% |
| Correct type detection | 90% | 80% |
| Correct language detection | 95% | 85% |
| No duplicate prefixes | 100% | 95% |
| Context-appropriate templates | 85% | 75% |

---

## Known Limitations

- Very short instructions (<3 words) may have poor analysis
- Mixed language with mostly code may misdetect language
- Creative writing prompts may need more diverse templates
- Multi-line instructions need better parsing

---

*Last Updated: 2026-04-15*
