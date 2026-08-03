from unittest.mock import patch

import pandas as pd

from api.fear_greed import FearGreedObservation
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


def test_analysis_prompt_defines_macro_dates_as_observations():
    prompt = LLMManager.build_analysis_prompt("AAPL", "context")

    assert "### 时间基准" in prompt
    assert "`as of`" in prompt
    assert "不是预测日期" in prompt
    assert "不得将其质疑" in prompt


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


def test_financial_context_converts_yfinance_ratios_to_percentages():
    manager = object.__new__(LLMManager)

    context = manager.build_ai_context(
        "AAPL",
        financial_data={"ROE": 1.49, "Profit Margin": 0.25},
    )

    assert "- ROE: 149.00%" in context
    assert "- Profit Margin: 25.00%" in context


def test_news_context_uses_actual_finnhub_columns():
    manager = object.__new__(LLMManager)
    news = pd.DataFrame(
        [
            {
                "headline": "Apple launches a product",
                "sentiment_label": "Positive",
                "sentiment_score": 0.42,
                "datetime": pd.Timestamp("2026-08-01"),
                "source": "Example News",
            }
        ]
    )

    context = manager.build_ai_context("AAPL", news_data=news)

    assert "Apple launches a product: Positive, score 0.42" in context
    assert "published 2026-08-01" in context
    assert "source Example News" in context
    assert "News: N/A" not in context


def test_crypto_context_identifies_asset_type_and_market_news_scope():
    manager = object.__new__(LLMManager)
    news = pd.DataFrame(
        [
            {
                "headline": "Digital asset market update",
                "sentiment_label": "Neutral",
                "sentiment_score": 0.0,
                "news_scope": "crypto-market",
            }
        ]
    )

    context = manager.build_ai_context(
        "BTC/USDT", asset_type="crypto", news_data=news
    )

    assert "- Asset Type: crypto" in context
    assert "scope crypto-market" in context


def test_crypto_context_includes_sourced_fear_greed_observation():
    manager = object.__new__(LLMManager)
    observation = FearGreedObservation(
        value=33,
        classification="Fear",
        observation_date="2026-08-02",
    )

    context = manager.build_ai_context(
        "BTC/USDT",
        asset_type="crypto",
        market_sentiment=observation,
    )

    assert "Fear & Greed Index: 33/100 (Fear" in context
    assert "as of 2026-08-02" in context
    assert "source: Alternative.me" in context
    assert "scope: Bitcoin market" in context
    assert "not a standalone signal" in context
