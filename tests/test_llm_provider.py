from unittest.mock import patch

import pytest

from engine.llm_provider import (
    LLMConfig,
    LLMConfigurationError,
    create_llm,
)


def test_reads_legacy_gemini_config():
    config = LLMConfig.from_secrets(
        {"gemini": {"api_key": "legacy-key", "model": "gemini-test"}}
    )

    assert config.provider == "gemini"
    assert config.model == "gemini-test"
    assert config.api_key == "legacy-key"


def test_reads_common_openai_config():
    config = LLMConfig.from_secrets(
        {
            "llm": {
                "provider": "openai",
                "api_key": "openai-key",
                "model": "gpt-test",
                "temperature": 0.1,
                "max_tokens": 2000,
            }
        }
    )

    assert config.provider == "openai"
    assert config.temperature == 0.1
    assert config.max_tokens == 2000


def test_openai_compatible_accepts_base_url_alias():
    config = LLMConfig.from_secrets(
        {
            "llm": {
                "provider": "openai-like",
                "api_key": "compatible-key",
                "model": "custom-model",
                "base_url": "https://llm.example/v1",
                "context_window": 64_000,
            }
        }
    )

    assert config.provider == "openai_compatible"
    assert config.api_base == "https://llm.example/v1"
    assert config.context_window == 64_000


def test_ollama_does_not_require_api_key():
    config = LLMConfig.from_secrets(
        {"llm": {"provider": "ollama", "model": "qwen3:8b"}}
    )

    assert config.provider == "ollama"
    assert config.api_key is None
    assert config.api_base == "http://localhost:11434"


@pytest.mark.parametrize(
    ("secrets", "message"),
    [
        (
            {"llm": {"provider": "unknown", "model": "x", "api_key": "k"}},
            "provider",
        ),
        ({"llm": {"provider": "openai", "api_key": "k"}}, "model"),
        ({"llm": {"provider": "openai", "model": "x"}}, "API key"),
        (
            {
                "llm": {
                    "provider": "openai_compatible",
                    "model": "x",
                    "api_key": "k",
                }
            },
            "api_base",
        ),
    ],
)
def test_rejects_invalid_config(secrets, message):
    with pytest.raises(LLMConfigurationError, match=message):
        LLMConfig.from_secrets(secrets)


def test_factory_constructs_gemini():
    config = LLMConfig("gemini", "gemini-test", "key")

    with patch("llama_index.llms.google_genai.GoogleGenAI") as google_genai:
        create_llm(config)

    google_genai.assert_called_once_with(
        model="gemini-test",
        api_key="key",
        temperature=0.2,
    )


def test_factory_constructs_openai_compatible():
    config = LLMConfig(
        "openai_compatible",
        "custom-model",
        "key",
        api_base="https://llm.example/v1",
    )

    with patch("llama_index.llms.openai_like.OpenAILike") as openai_like:
        create_llm(config)

    openai_like.assert_called_once_with(
        model="custom-model",
        api_key="key",
        temperature=0.2,
        api_base="https://llm.example/v1",
        timeout=60.0,
        context_window=128_000,
        is_chat_model=True,
    )


def test_factory_constructs_ollama():
    config = LLMConfig(
        "ollama",
        "qwen3:8b",
        "ollama-cloud-key",
        temperature=0.1,
        api_base="http://ollama:11434",
        max_tokens=4096,
        timeout=180.0,
        context_window=32_000,
    )

    with patch("llama_index.llms.ollama.Ollama") as ollama:
        create_llm(config)

    ollama.assert_called_once_with(
        model="qwen3:8b",
        base_url="http://ollama:11434",
        temperature=0.1,
        request_timeout=180.0,
        context_window=32_000,
        additional_kwargs={"num_predict": 4096},
        headers={"Authorization": "Bearer ollama-cloud-key"},
    )
