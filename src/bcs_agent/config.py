"""Configuration for the agent harness.

The harness is model- and provider-agnostic: the model is just a Pydantic AI
model string of the form ``"provider:model-name"``. Anything Pydantic AI can
resolve (``openai:``, ``anthropic:``, ``xai:``, ``google-gla:`` ...) works
without code changes -- only the string and the relevant API key change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

#: Default model. ``xai:grok-4-1-fast-reasoning`` requires ``XAI_API_KEY``.
DEFAULT_MODEL = "xai:grok-4-1-fast-reasoning"

#: Default agent instructions. Re-sent on every run (not stored in history),
#: so they keep applying for the whole conversation.
DEFAULT_INSTRUCTIONS = (
    "You are a helpful, conversational assistant. "
    "Use the running conversation as context and answer clearly and concisely."
)

#: Default directory scanned for tool plugins, relative to the working dir.
DEFAULT_TOOLS_DIR = "tools"

#: Environment variables that override the defaults.
MODEL_ENV_VAR = "BCS_AGENT_MODEL"
INSTRUCTIONS_ENV_VAR = "BCS_AGENT_INSTRUCTIONS"
TOOLS_DIR_ENV_VAR = "BCS_AGENT_TOOLS_DIR"


@dataclass(slots=True)
class Config:
    """Harness configuration.

    Attributes:
        model: A Pydantic AI ``"provider:model-name"`` string.
        instructions: System-level guidance applied to every turn.
        tools_dir: Directory scanned for tool plugins (see :mod:`bcs_agent.plugins`).
    """

    model: str = DEFAULT_MODEL
    instructions: str = DEFAULT_INSTRUCTIONS
    tools_dir: str = DEFAULT_TOOLS_DIR

    @classmethod
    def from_env(cls) -> "Config":
        """Build a :class:`Config`, letting environment variables override defaults."""
        return cls(
            model=os.getenv(MODEL_ENV_VAR, DEFAULT_MODEL),
            instructions=os.getenv(INSTRUCTIONS_ENV_VAR, DEFAULT_INSTRUCTIONS),
            tools_dir=os.getenv(TOOLS_DIR_ENV_VAR, DEFAULT_TOOLS_DIR),
        )
