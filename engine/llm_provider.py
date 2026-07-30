"""LLM provider configuration and construction.

The application uses LlamaIndex's common LLM interface, so callers do not need
to know which provider is selected.
"""

from dataclasses import dataclass
from typing import Any, Mapping


class LLMConfigurationError(ValueError):
    """Raised when the configured LLM provider cannot be constructed."""


_PROVIDER_ALIASES = {
    "gemini": "gemini",
    "google": "gemini",
    "google_genai": "gemini",
    "openai": "openai",
    "openai_compatible": "openai_compatible",
    "openai_like": "openai_compatible",
    "ollama": "ollama",
}


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    api_key: str | None = None
    temperature: float = 0.2
    api_base: str | None = None
    max_tokens: int | None = None
    timeout: float = 60.0
    context_window: int | None = None

    @classmethod
    def from_secrets(cls, secrets: Mapping[str, Any]) -> "LLMConfig":
        """Read the common ``[llm]`` config or the legacy ``[gemini]`` config."""
        raw_config = secrets.get("llm")
        if raw_config:
            config = dict(raw_config)
            provider_name = str(config.get("provider", "")).strip().lower()
            provider_name = provider_name.replace("-", "_")
            provider = _PROVIDER_ALIASES.get(provider_name)
            if not provider:
                supported = ", ".join(sorted(_PROVIDER_ALIASES))
                raise LLMConfigurationError(
                    f"Unsupported LLM provider {provider_name!r}. "
                    f"Supported values: {supported}."
                )
        else:
            # Backward compatibility for existing deployments.
            config = dict(secrets.get("gemini", {}))
            provider = "gemini"

        model = str(config.get("model", "")).strip()
        if not model:
            if provider == "gemini" and not raw_config:
                model = "gemma-4-26b-a4b-it"
            else:
                raise LLMConfigurationError("LLM model is missing in secrets.")

        api_key_value = config.get("api_key")
        api_key = str(api_key_value).strip() if api_key_value else None
        if provider != "ollama" and not api_key:
            raise LLMConfigurationError("LLM API key is missing in secrets.")

        api_base_value = config.get("api_base", config.get("base_url"))
        api_base = (
            str(api_base_value).strip() if api_base_value is not None else None
        )
        if provider == "ollama" and not api_base:
            api_base = "http://localhost:11434"
        if provider == "openai_compatible" and not api_base:
            raise LLMConfigurationError(
                "api_base is required for an OpenAI-compatible provider."
            )

        context_window = _optional_int(config.get("context_window"))
        if provider == "openai_compatible" and context_window is None:
            context_window = 128_000

        return cls(
            provider=provider,
            model=model,
            api_key=api_key,
            temperature=float(config.get("temperature", 0.2)),
            api_base=api_base,
            max_tokens=_optional_int(config.get("max_tokens")),
            timeout=float(config.get("timeout", 60.0)),
            context_window=context_window,
        )


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def create_llm(config: LLMConfig):
    """Construct a LlamaIndex LLM for the selected provider."""
    common_kwargs = {
        "model": config.model,
        "api_key": config.api_key,
        "temperature": config.temperature,
    }
    if config.max_tokens is not None:
        common_kwargs["max_tokens"] = config.max_tokens

    if config.provider == "gemini":
        from llama_index.llms.google_genai import GoogleGenAI

        return GoogleGenAI(**common_kwargs)

    if config.provider == "openai":
        from llama_index.llms.openai import OpenAI

        return OpenAI(
            **common_kwargs,
            api_base=config.api_base,
            timeout=config.timeout,
        )

    if config.provider == "openai_compatible":
        from llama_index.llms.openai_like import OpenAILike

        return OpenAILike(
            **common_kwargs,
            api_base=config.api_base,
            timeout=config.timeout,
            context_window=config.context_window or 128_000,
            is_chat_model=True,
        )

    if config.provider == "ollama":
        from llama_index.llms.ollama import Ollama

        ollama_kwargs = {
            "model": config.model,
            "base_url": config.api_base,
            "temperature": config.temperature,
            "request_timeout": config.timeout,
        }
        if config.context_window is not None:
            ollama_kwargs["context_window"] = config.context_window
        if config.max_tokens is not None:
            ollama_kwargs["additional_kwargs"] = {
                "num_predict": config.max_tokens
            }
        if config.api_key:
            ollama_kwargs["headers"] = {
                "Authorization": f"Bearer {config.api_key}"
            }
        return Ollama(**ollama_kwargs)

    # LLMConfig normalizes providers, so this is a defensive guard for callers
    # that construct it directly.
    raise LLMConfigurationError(
        f"Unsupported normalized LLM provider: {config.provider!r}."
    )
