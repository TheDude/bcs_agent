"""Plugin discovery via Python entry points.

A *plugin* is an installable distribution package that declares an entry point
in the ``bcs_agent.plugins`` group::

    [project.entry-points."bcs_agent.plugins"]
    clock = "bcs_plugin_clock:get_toolset"

The entry-point key (``clock``) is the plugin name; the value points at a
``get_toolset`` factory returning a Pydantic AI
:class:`~pydantic_ai.toolsets.AbstractToolset`. The harness discovers every
installed plugin from package metadata -- no filesystem scanning -- so a
deployment exposes exactly the plugin packages installed in its environment.

The factory may optionally accept the harness :class:`Config`; it is passed
only when the factory declares a parameter.
"""

from __future__ import annotations

import importlib.metadata
import inspect
from collections.abc import Iterable

from pydantic_ai.toolsets import AbstractToolset, PrefixedToolset

from bcs_agent.config import Config

#: The entry-point group plugins declare themselves under.
PLUGIN_GROUP = "bcs_agent.plugins"


class PluginError(Exception):
    """A plugin is installed but could not be loaded.

    Raised eagerly (fail-fast): an integration a customer paid for must never
    silently disappear because of a broken or misconfigured plugin.
    """


def discover_toolsets(
    config: Config | None = None,
    *,
    entry_points: Iterable[importlib.metadata.EntryPoint] | None = None,
) -> list[AbstractToolset]:
    """Discover and build a toolset for every installed plugin.

    Args:
        config: Harness configuration, forwarded to plugin factories that
            declare a parameter. Defaults to :class:`Config` defaults.
        entry_points: Entry points to load. Defaults to every entry point in
            the ``bcs_agent.plugins`` group. An injection seam for tests; any
            object with a ``name`` attribute and a ``load()`` method works.

    Returns:
        One :class:`PrefixedToolset` per plugin -- prefixed with the plugin name
        so tools from different plugins cannot collide.

    Raises:
        PluginError: If a plugin is installed but cannot be loaded.
    """
    config = config or Config()
    if entry_points is None:
        entry_points = importlib.metadata.entry_points(group=PLUGIN_GROUP)
    return [
        PrefixedToolset(_load_plugin(ep, config), ep.name)
        for ep in sorted(entry_points, key=lambda ep: ep.name)
    ]


def _load_plugin(ep: importlib.metadata.EntryPoint, config: Config) -> AbstractToolset:
    """Resolve a single entry point to its toolset, failing loudly on any problem."""
    try:
        factory = ep.load()
    except Exception as exc:
        raise PluginError(f"plugin {ep.name!r}: failed to load ({exc})") from exc

    if not callable(factory):
        raise PluginError(
            f"plugin {ep.name!r}: entry point must point to a callable"
        )

    try:
        toolset = factory(config) if _wants_config(factory) else factory()
    except Exception as exc:
        raise PluginError(
            f"plugin {ep.name!r}: get_toolset() raised ({exc})"
        ) from exc

    if not isinstance(toolset, AbstractToolset):
        raise PluginError(
            f"plugin {ep.name!r}: get_toolset() must return an AbstractToolset, "
            f"got {type(toolset).__name__}"
        )
    return toolset


def _wants_config(factory: object) -> bool:
    """True if ``factory`` declares a parameter -- it should receive the Config."""
    try:
        return len(inspect.signature(factory).parameters) > 0
    except (TypeError, ValueError):  # pragma: no cover - uninspectable callable
        return False
