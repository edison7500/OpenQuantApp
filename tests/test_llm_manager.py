from unittest.mock import patch

from engine.llm_manager import LLMManager
from engine.macro_manager import MacroMetric
from engine.llm_provider import LLMConfig


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


def test_refreshes_llm_after_secrets_change():
    manager = object.__new__(LLMManager)
    manager.config = LLMConfig("gemini", "old-model", "old-key")
    manager.llm = object()
    new_config = LLMConfig(
        "ollama",
        "gemma4:31b-cloud",
        "new-key",
        api_base="https://ollama.com",
    )
    new_llm = object()

    with (
        patch(
            "engine.llm_manager.LLMConfig.from_secrets",
            return_value=new_config,
        ),
        patch("engine.llm_manager.create_llm", return_value=new_llm),
        patch("engine.llm_manager.Settings") as settings,
    ):
        manager._refresh_llm_if_needed()

    assert manager.config == new_config
    assert manager.llm is new_llm
    assert settings.llm is new_llm


def test_macro_context_preserves_value_date_and_source():
    manager = object.__new__(LLMManager)
    metrics = [
        MacroMetric(
            label="失业率",
            value=4.2,
            unit="%",
            icon="👷",
            observation_date="2026-06-01",
            source="FRED",
            series_id="UNRATE",
        )
    ]

    context = manager.build_ai_context("TEST", macro_data=metrics)

    assert "- 失业率: 4.20%" in context
    assert "as of 2026-06-01" in context
    assert "source: FRED" in context
