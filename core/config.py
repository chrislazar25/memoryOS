"""
config.py — Central environment loader for MemoryOS.

Call load_env() once at startup (before any provider is instantiated).
It loads .env, validates required keys for the active provider, and
sets model defaults so downstream code can always read them from os.environ.
"""

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-6"
_OPENAI_DEFAULT_MODEL = "gpt-4o"


def load_env() -> None:
    """Load .env and validate environment for the configured LLM provider."""
    load_dotenv()

    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower().strip()

    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise EnvironmentError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or export it in your shell."
            )
        model = os.environ.setdefault("ANTHROPIC_MODEL", _ANTHROPIC_DEFAULT_MODEL)
        logger.info("Provider: anthropic  |  model: %s", model)

    elif provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise EnvironmentError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
                "Add it to your .env file or export it in your shell."
            )
        model = os.environ.setdefault("OPENAI_MODEL", _OPENAI_DEFAULT_MODEL)
        logger.info("Provider: openai  |  model: %s", model)

    else:
        raise EnvironmentError(
            f"LLM_PROVIDER={provider!r} is not supported. "
            "Valid values: 'anthropic' (default), 'openai'."
        )
