# Changelog

All notable changes to this project will be documented in this file.

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
