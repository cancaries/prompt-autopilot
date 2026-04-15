# Test Results

## 2026-04-15 - Initial Testing

### Tests Run (17 cases)

| Test | Instruction | Type | Version | Score | Status |
|------|-------------|------|---------|-------|--------|
| T1 | 写一个Python函数计算斐波那契数列 | code | C | 5.7 | ✅ |
| T2 | fix the bug in my code | code | C | 9.7 | ⚠️ Score too high |
| T3 | write a blog post about AI | writing | B | 4.1 | ✅ |
| T4 | 帮我写一封道歉邮件 | writing | B | 4.9 | ✅ |
| T5 | 解释什么是量子纠缠 | explanation | B | 4.9 | ✅ |
| T6 | 帮我写一个排序算法 | code | C | 5.7 | ✅ |
| T7 | explain how blockchain works | explanation | B | 5.5 | ✅ |
| T8 | 请帮我写一个 function 处理 user data | code | C | 5.7 | ✅ |
| T9 | 写代码 | code | C | 5.7 | ✅ |
| T10 | 写一个Python函数处理JSON数据 | code | C | 5.7 | ✅ |
| T11 | 用Python实现快速排序 | code | C | 5.7 | ✅ |
| T12 | 用Python实现一个LRU缓存 | code | C | 5.7 | ✅ |
| T13 | 写一段科幻小说开头设定在22世纪火星城市 | writing | B | 4.9 | ✅ |
| T14 | 解释机器学习 | explanation | B | 4.9 | ✅ |
| T15 | 做好这个功能 | general | C | 3.7 | ✅ |
| T16 | AI | general | C | 6.5 | ✅ |
| T17 | 给初级工程师解释什么是闭包 | explanation | B | 4.9 | ✅ |
| T18 | review这段React代码的性能问题 | code | C | 5.7 | ✅ |

### Summary

- **Total**: 17 tests
- **Pass**: 16
- **Fail**: 0
- **Warnings**: 1 (score inflation for "fix the bug")

### Issues Found

1. **Score Inflation** (T2): "fix the bug in my code" scored 9.7/10 - too high for a brief instruction with placeholder templates. The scoring evaluates template structure, not instruction quality.

### Fixes Applied

- ✅ Fix duplicate prefixes in Chinese explanation templates
- ✅ Add more Chinese code keywords (排序, 算法, 缓存, etc.)
- ✅ Fix misdetection of "排序算法" as writing instead of code
- ✅ Fix recommendation logic: writing tasks now ALWAYS use Version B

### Known Limitations

- Scores can be inflated when templates are well-structured but still contain placeholders
- Very short instructions (<3 words) have poor analysis
- Some technical terms may not be detected correctly

---

## Iteration Log

### v1.0.0 → v1.0.1
- Fix duplicate prefixes
- Fix instruction type detection
- Fix recommendation logic
- Add 28-case test plan
