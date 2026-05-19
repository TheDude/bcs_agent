"""Example bcs-agent plugin: a world clock.

A richer companion to the ``clock`` plugin. Where ``clock`` is the minimal
plugin, this one shows a tool that:

- takes a **parameter** (a location), and
- uses ``ModelRetry`` -- the idiomatic Pydantic AI way to hand the model a
  correctable error -- when that parameter is not a valid time zone.

It uses only the standard library (``zoneinfo``); a plugin that needs a
third-party SDK would declare it in this package's ``pyproject.toml``.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic_ai import FunctionToolset, ModelRetry

toolset = FunctionToolset()

#: Identifiers to show the model when it passes something unrecognized.
_EXAMPLES = "Europe/Paris, America/New_York, Asia/Tokyo, Australia/Sydney"


@toolset.tool_plain
def current_datetime(location: str) -> str:
    """Return the current date and time at a location.

    Args:
        location: An IANA time-zone identifier for the place of interest, such
            as ``Europe/Paris`` or ``America/New_York``. Convert a plain place
            name (e.g. "Tokyo") to its identifier (``Asia/Tokyo``) before
            calling this tool.
    """
    try:
        zone = ZoneInfo(location)
    except (ZoneInfoNotFoundError, ValueError):
        # Don't fail the run -- ask the model to try a corrected identifier.
        raise ModelRetry(
            f"{location!r} is not a valid IANA time-zone identifier. "
            f"Pass one of the form Area/City, e.g. {_EXAMPLES}."
        )

    stamp = datetime.now(zone).strftime("%A, %d %B %Y, %H:%M:%S %Z (UTC%z)")
    return f"{stamp} -- {location}"


def get_toolset() -> FunctionToolset:
    """Plugin entry point: hand the harness this plugin's toolset."""
    return toolset
