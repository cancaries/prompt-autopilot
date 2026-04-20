# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-04-21

### Fixed
- **T11 (P0) few-shot mismatch**: Input `写一个Python函数接收JSON数组返回平均值保留2位小数` now shows averaging-specific few-shot examples (`[1, 2, 3, 4, 5] → 3.00`) instead of unrelated JSON field extraction. Root cause: static shared template not differentiated by task.
- **T10/T11 (P1) shared few-shot**: T10 and T11 now have distinct few-shot examples. T10 → JSON field extraction/validation. T11 → numeric array statistics (average, sum, min/max).
- **T27 (P2) mixed language**: `review这段React代码的性能问题` now normalizes to consistent Chinese `审查这段React代码的性能问题` instead of embedding English `review` in Chinese sentence.
- **T10 Few-shot mismatch**: Fixed JSON/数组 few-shot examples that incorrectly showed averaging (e.g. `[1, 2, 3, 4] → 2.5（平均值）`) — same as T11. Now shows generic JSON-processing examples: field extraction and JSON validation.
- **Bullet spacing**: Fixed missing space after dash in "-具体的输入/输出规格" → "- 具体的输入/输出规格" (affects all "指令信息不足" templates)
- **T13 creative_writing**: Filled unfilled placeholder `视角：[第一人称/第三人称/上帝视角]` → `视角：第三人称`
- **T14 academic_writing**: Filled unfilled placeholders `类型：[文献综述/研究摘要/...]` → `类型：文献综述` and `学术领域：[如 计算机科学/医学/...]` → `学术领域：计算机科学`
- **Few-shot examples**: Replaced placeholder `# 正常用例 → 期望输出` with concrete examples `输入：列表 [5, 2, 8, 1, 9] → 输出：[1, 2, 5, 8, 9]` for generic code tasks
- **P1-A (Few-shot generic placeholders)**: Replaced generic `"输入：给定任务需求 → 输出：完整实现代码"` with concrete examples per keyword type (SQL/function/user data). Affects T2, T8, T18, T19, T20.
- **P1-B (Language confusion)**: Fixed `_extract_info()` to use `detect_language()` instead of hardcoded `"中文"`. English instructions (e.g. `write a blog post about AI`) now correctly output `"语言：英文"`. Affects T4, T7.
- **P2 (Audience field)**: Fixed `_extract_info()` to infer audience from genre keywords (e.g. `"科幻"` → `"科幻小说读者"`) and `_extract_core_concept()` instead of embedding full instruction. Affects T15, T16, T27.
- **P3 (Boundary description)**: Fixed `"空数组返回 0 或空列表"` → `"空数组应返回 None（因为平均值对空集无定义），调用方需自行处理空数组输入"`. Affects T10.

## [1.0.2] - 2026-04-16

### Fixed
- **P1**: Enable LLM inference fallback when rule-based template matching fails; add `_CODE_DEFAULTS` entries for JSON array (平均值) and square/power tasks
- **P2**: Add `code_review` task type with keywords (review/代码审查/cr/代码分析/性能review/review这段) — fixes misclassification of code review prompts as Python code
- **P3**: Add `test_generation` task type with keywords (单元测试/pytest/jest/test case/写测试) and proper template — fixes misclassification of unit test prompts as writing tasks
- **P4**: Fix `_extract_tone()` to combine tone keywords instead of early-return — "语气专业友善" now correctly fills as "专业友善"

## [1.0.1] - 2026-04-16

### Fixed
- Removed orphaned module-level code in core.py causing SyntaxError that blocked all CLI usage

## [1.0.0] - 2026-04-15

### Added
- Initial release
- Context-aware template generation based on instruction type
- Support for Chinese, English, and mixed-language instructions
- Instruction type detection: code, writing, explanation, question, data
- Language detection: zh, en, mixed
- Smart version recommendations based on instruction type
- Bilingual documentation (English + Chinese)

### Features
- **Analyze**: Detect missing information, ambiguous terms, unstated assumptions
- **Optimize**: Generate 3 versions - Concise, Detailed, Structured
- **Evaluate**: Score each on Clarity, Specificity, Completeness (1-10)
- **Recommend**: Pick the best version with explanation
- **Learn**: Remember preferences for future use

### Integration
- Works with: OpenClaw, Cursor, Claude Code, Codex, any AI tool
- CLI: `prompt-autopilot` and `pma` commands
- Skill file for OpenClaw integration
