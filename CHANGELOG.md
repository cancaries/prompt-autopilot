# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-04-16

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
