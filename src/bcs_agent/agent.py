"""Construction of the Pydantic AI :class:`~pydantic_ai.Agent`.

This is deliberately the only place that knows how to turn a :class:`Config`
into an ``Agent``. Tools reach the agent as plugins: :func:`build_agent`
discovers every installed plugin package (see :mod:`bcs_agent.plugins`) and
attaches them as Pydantic AI toolsets.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic_ai import Agent
from pydantic_ai.toolsets import AbstractToolset

from bcs_agent.config import Config
from bcs_agent.plugins import discover_toolsets


def build_agent(
    config: Config | None = None,
    *,
    extra_toolsets: Sequence[AbstractToolset] | None = None,
) -> Agent[None, str]:
    """Build a conversational agent from ``config``.

    Args:
        config: Harness configuration. Defaults to :class:`Config` defaults.
        extra_toolsets: Toolsets to attach in addition to the discovered
            plugins. Lets library users and tests inject tools directly.

    Returns:
        A Pydantic AI ``Agent`` that returns plain text, with every installed
        plugin's toolset attached.
    """
    config = config or Config()
    toolsets: list[AbstractToolset] = discover_toolsets(config)
    if extra_toolsets:
        toolsets.extend(extra_toolsets)
    return Agent(
        config.model,
        instructions=config.instructions,
        toolsets=toolsets,
    )
