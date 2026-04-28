# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-04-29

### Fixed
- **T11/T23 (Duplicate title prefix)**: Fixed `generate_fallback_prompt()` for `code` type where task title was "用 Python 实现：用Python实现..." (duplicate prefix). Now strips the "用{Lang}实现" pattern from the instruction before prepending the prefix, so title correctly shows "用 Python 实现：输入列表输出平方".
- **T15/T16 (Hardcoded 7.0 score)**: Added bonuses in `evaluate_version()` for `creative_writing` and `academic_writing` instruction types. Previously these types had no bonus blocks, resulting in all scores at base 7.0. Now properly rewards well-structured templates with specificity/completeness bonuses (T15 sci-fi: 7.0→9.25, T16 academic: 7.0→9.25).
- **T4/T7 (Mixed language field)**: Changed `_extract_info()` to return `info["language"] = "English"` (not "英文") for English inputs, fixing "Language：英文" mixed-language output in English templates.
- **T19 (SQL optimization examples)**: Added SQL optimization-specific few-shot examples in `get_technique_recommendations()` when instruction contains SQL optimization keywords ("优化", "optimize", "优化这段sql"). Examples now show EXPLAIN analysis and index recommendations instead of generic SELECT/INSERT query examples.

## [Unreleased] - 2026-04-26

### Fixed
- **T2/T8 (English code examples)**: `get_technique_recommendations()` for `code` type now detects input language and returns English examples/techniques when input is English. Fixed examples from Chinese "输入/输出" to English "Input/Output".
- **T4 (English writing template)**: `generate_fallback_prompt()` for `writing` type now uses English labels (Writing Task, Target Audience, etc.) when input is English. Also added English topic keywords without Chinese parentheticals.
- **T7 (English explanation template)**: `generate_fallback_prompt()` for `explanation` type now uses English labels (Explanation Task, Target Audience, etc.) when input is English.
- **T8 (Mixed language code)**: `get_technique_recommendations()` now detects language for code type and uses consistent language in examples.
- **T15 (Sci-fi style)**: `generate_fallback_prompt()` for `creative_writing` type now detects sci-fi genre and uses appropriate style ("科幻小说风格：宏大叙事、探索未来、想象力丰富") instead of generic "通俗易懂，适合科普".
- **T16 (Academic writing techniques)**: Added explicit `academic_writing` handling in `get_technique_recommendations()` with language-aware recommendations and examples instead of falling through to generic Chinese recommendations.

### Fixed
- **问题1 (T16 content pollution)**: `academic_writing` in `generate_fallback_prompt()` had hardcoded Few-shot examples (machine learning in medical imaging + unrelated blockchain in supply chain). Now dynamically uses `info['topic']` for the first example and omits the second unrelated example.
- **问题2 (T24 closure examples)**: `explanation` in `get_technique_recommendations()` gave generic method descriptions for technical concepts. Added specific code examples for "闭包/closure" keywords: `def outer(x): def inner(y): return x + y; return inner` with demonstration.
- **问题3 (T7 language inconsistency)**: English explanation prompts like "explain how blockchain works" returned Chinese analogies. Added `detect_language()` check at the start of explanation block; now returns English analogies and recommendations when input is English.
- **T4/T7 (Language mismatch)**: `_extract_info()` now returns English field values (audience, depth, style, tone, analogy, format) when input language is English. Previously only `info["language"]` was set to "英文" while other template fields remained hardcoded in Chinese. Now English input like `write a blog post about AI` outputs English audience fields like `general readers with basic knowledge of AI` instead of `一般读者，对AI有基本了解`.
- **T16 (Few-shot missing)**: `academic_writing` branch in `generate_fallback_prompt` now includes a `📖 Few-shot 示例` section with two example abstracts (machine learning in medical imaging, blockchain in supply chain) to guide the output format.

### Fixed
- **T10 (P1) context pollution**: `_CODE_DEFAULTS` entry for `("json", "数组", "list")` had averaging-specific `output` and `boundary` ("数值（平均值）", "空数组应返回 None..."), which polluted T10 (generic JSON processing). Fixed by: (1) updating output to "处理后的 JSON 数据或验证结果" and boundary to "空数组返回空对象 {} 或空列表 []；空对象返回空对象 {}；非法 JSON 返回 None"; (2) adding dedicated `("平均", "average", "mean")` entry before generic JSON/array entry so T11 correctly gets averaging boundary. T10 and T11 boundaries now distinct.
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
- **T9/T18/T19/T21 (Insufficient info examples)**: Added `_get_insufficient_info_examples(instruction_type, lang)` to generate context-appropriate examples for the "指令信息不足" warning. Examples now adapt to task type: `code` → code examples, `test_generation` → pytest/unittest examples, `explanation` → explanation examples, `writing` → writing examples, `general` → diverse examples. Previously all cases showed the same generic examples regardless of detected task type.

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

## [Unreleased] - 2026-04-27

### Known Issue
- **T2 (low severity)**: English code tasks still show Chinese technique section titles (e.g. "Chain-of-Thought：先分析最优子结构再写") while few-shot examples are correctly in English. Not blocking; core functionality works. Consider applying the same language-detection fix used in explanation branch.

