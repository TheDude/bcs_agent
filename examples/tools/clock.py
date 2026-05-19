"""Example tool plugin: a clock.

This is a reference for the plugin convention. A plugin is a ``.py`` file (or a
package directory) dropped into the harness's ``tools/`` folder. It defines a
``get_toolset()`` factory returning a Pydantic AI toolset.

Try it::

    BCS_AGENT_TOOLS_DIR=examples/tools uv run bcs-agent

then ask the agent for the current time.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic_ai import FunctionToolset

#: A bundle of related tools. The harness namespaces these under the plugin
#: name, so ``current_time`` is exposed to the model as ``clock_current_time``.
toolset = FunctionToolset()


@toolset.tool_plain
def current_time() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def get_toolset() -> FunctionToolset:
    """Plugin entry point: hand the harness this plugin's toolset."""
    return toolset
