import os
import logging
from typing import Literal, Any
from pydantic import SecretStr

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)


def get_chat_client(
    provider: Literal["openai", "anthropic", "openrouter"],
    model: str,
    temperature: float,
    timeout: int,
) -> Any:
    """
    Create and return a chat client for the given provider.

    Args:
        provider: One of "openai", "anthropic", "openrouter".
        model: Model identifier string.
        temperature: Sampling temperature.
        timeout: Request timeout in seconds.

    Returns:
        An instance of the provider-specific chat client.

    Raises:
        ValueError: If provider is unknown or OPENROUTER_API_KEY is missing when provider is "openrouter".
    """
    logger.info(
        "Creating chat client provider=%s model=%s temperature=%s timeout=%s",
        provider,
        model,
        temperature,
        timeout,
    )

    if provider == "openai":
        return ChatOpenAI(model=model, temperature=temperature, timeout=timeout)
    elif provider == "anthropic":
        return ChatAnthropic(model_name=model, temperature=temperature, timeout=timeout, stop=None)
    elif provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY is required when provider='openrouter'")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            timeout=timeout,
            base_url="https://openrouter.ai/api/v1",
            api_key=SecretStr(key),
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
