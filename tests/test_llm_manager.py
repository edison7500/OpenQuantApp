from engine.llm_manager import LLMManager


def test_analysis_prompt_is_balanced_and_evidence_driven():
    prompt = LLMManager.build_analysis_prompt(
        "TEST", "### Analysis Context for TEST\n- Sharpe Ratio: 1.2"
    )

    assert "证据驱动的资深投资研究员" in prompt
    assert "多空证据对称" in prompt
    assert "不得臆造" in prompt
    assert "数据局限" in prompt
    assert "偏积极 / 中性 / 偏谨慎" in prompt
    assert "首席风险官" not in prompt
    assert "立即撤离" not in prompt
    assert "存活概率" not in prompt


def test_analysis_prompt_includes_symbol_and_context():
    context = "unique-context-value"

    prompt = LLMManager.build_analysis_prompt("AAPL", context)

    assert "AAPL" in prompt
    assert context in prompt
