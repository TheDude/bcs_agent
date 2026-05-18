"""Construction of the Pydantic AI :class:`~pydantic_ai.Agent`.

This is deliberately the only place that knows how to turn a :class:`Config`
into an ``Agent``. Future integrations (tools, capabilities) should be wired in
here so the rest of the harness stays unchanged.
"""

from __future__ import annotations

from pydantic_ai import Agent

from bcs_agent.config import Config


def build_agent(config: Config | None = None) -> Agent[None, str]:
    """Build a conversational agent from ``config``.

    Args:
        config: Harness configuration. Defaults to :class:`Config` defaults.

    Returns:
        A Pydantic AI ``Agent`` that returns plain text.
    """
    config = config or Config()
    return Agent(
        config.model,
        instructions=config.instructions,
        # Integrations land here later, e.g.:
        #   tools=[...], capabilities=[...]
    )
