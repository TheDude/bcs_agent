"""Example bcs-agent plugin: a clock.

This module is the code half of an installable plugin *package*. The
``pyproject.toml`` next to it declares the ``bcs_agent.plugins`` entry point
that makes ``get_toolset`` discoverable once the package is installed.

It is the minimal plugin: one no-argument tool.
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
