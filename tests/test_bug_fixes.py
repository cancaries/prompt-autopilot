"""
Test suite for the 4 bug fixes in prompt-autopilot.

P1: "用Python实现输入列表输出平方" should produce meaningful output from _infer_code_defaults
P2: "review这段React代码" should be classified as "code_review" (not "code")
P3: "写单元测试" should be classified as "test_generation" (not "writing")
P4: "写一封拒绝面试者的邮件语气专业友善" should have tone filled as "专业友善"
"""
import sys
import os

sys.path.insert(0, "/home/junhaoge/programs/prompt-autopilot/src")

from prompt_autopilot.core import (
    detect_instruction_type,
    _infer_code_defaults,
    generate_fallback_prompt,
)


class TestP1_InferCodeDefaults:
    """P1: _infer_code_defaults should return meaningful spec, not None/placeholder."""

    def test_squares_instruction_returns_meaningful_spec(self):
        """'用Python实现输入列表输出平方' should match the '平方' default spec."""
        instruction = "用Python实现输入列表输出平方"
        result = _infer_code_defaults(instruction)
        assert result is not None, (
            f"P1 FAILED: _infer_code_defaults returned None for '{instruction}'. "
            f"Expected a meaningful spec from _CODE_DEFAULTS."
        )
        assert "output" in result, f"P1 FAILED: spec has no 'output' key: {result}"
        assert result["output"] != "[请补充]", (
            f"P1 FAILED: output is still a placeholder '[请补充]', got: {result['output']}"
        )
        # The '平方' entry has output "数值或列表（平方）"
        assert "平方" in result["output"] or "列表" in result["output"].lower(), (
            f"P1 FAILED: output doesn't mention '平方' or list: {result['output']}"
        )
        print(f"P1 PASSED: _infer_code_defaults returned meaningful spec: {result}")


class TestP2_CodeReviewClassification:
    """P2: 'review这段React代码' should be classified as 'code_review' not 'code'."""

    def test_review_this_code_is_code_review(self):
        instruction = "review这段React代码"
        result = detect_instruction_type(instruction)
        assert result == "code_review", (
            f"P2 FAILED: 'review这段React代码' was classified as '{result}', "
            f"expected 'code_review'. "
            f"Check that 'review这段' is in code_review_keywords BEFORE code_keywords."
        )
        print(f"P2 PASSED: detect_instruction_type('review这段React代码') = '{result}'")


class TestP3_TestGenerationClassification:
    """P3: '写单元测试' should be classified as 'test_generation' not 'writing'."""

    def test_write_unit_test_is_test_generation(self):
        instruction = "写单元测试"
        result = detect_instruction_type(instruction)
        assert result == "test_generation", (
            f"P3 FAILED: '写单元测试' was classified as '{result}', "
            f"expected 'test_generation'. "
            f"Check that test_generation_keywords check comes BEFORE writing_keywords check."
        )
        print(f"P3 PASSED: detect_instruction_type('写单元测试') = '{result}'")


class TestP4_ToneExtraction:
    """P4: '写一封拒绝面试者的邮件语气专业友善' should have tone '专业友善'."""

    def test_combined_tone_extraction(self):
        """
        The instruction contains both '专业' and '友善'.
        _extract_tone should combine them into '专业友善'.
        """
        instruction = "写一封拒绝面试者的邮件语气专业友善"
        
        # We test via generate_fallback_prompt for writing tasks
        prompt = generate_fallback_prompt(instruction, "writing")
        
        assert "语气：专业友善" in prompt or "语气：专业" in prompt, (
            f"P4 FAILED: Neither '语气：专业友善' nor '语气：专业' found in prompt. "
            f"Expected '专业友善' (combined). Got:\n{prompt}"
        )
        
        # More strict: should be "专业友善", not just "专业"
        assert "语气：专业友善" in prompt, (
            f"P4 FAILED: Tone is '专业' but should be '专业友善'. "
            f"The _extract_tone function must combine both '专业' and '友善' when present. "
            f"Got:\n{prompt}"
        )
        print(f"P4 PASSED: tone extracted correctly as '专业友善'")
