"""Filesystem-based tool plugin discovery.

A *plugin* is a file or directory in the configured ``tools/`` folder. Its mere
presence is the entitlement: the set of plugins under ``tools/`` is exactly the
set of integrations a deployment exposes. This pairs with a git-submodule devops
model -- a customer branch includes only the submodules they paid for.

- ``tools/<name>.py``  -- a single-file plugin.
- ``tools/<name>/``    -- a package plugin (what a git submodule looks like).

Each plugin module defines a ``get_toolset`` factory returning a Pydantic AI
:class:`~pydantic_ai.toolsets.AbstractToolset`::

    def get_toolset() -> AbstractToolset: ...
    # or, if it needs harness context:
    def get_toolset(config: Config) -> AbstractToolset: ...

The factory form (rather than a module-level toolset) lets a plugin lazy-import
its own SDK *inside* the function -- so the harness core never depends on any
integration's packages, only the plugins actually present do.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

from pydantic_ai.toolsets import AbstractToolset, PrefixedToolset

from bcs_agent.config import Config

#: The factory function each plugin module must define.
PLUGIN_FACTORY = "get_toolset"


class PluginError(Exception):
    """A plugin file is present but could not be loaded.

    Raised eagerly (fail-fast): an integration a customer paid for must never
    silently disappear because of a broken or misconfigured plugin.
    """


def discover_toolsets(config: Config | None = None) -> list[AbstractToolset]:
    """Discover and build every plugin toolset under ``config.tools_dir``.

    Args:
        config: Harness configuration. Defaults to :class:`Config` defaults.

    Returns:
        One :class:`PrefixedToolset` per plugin -- prefixed with the plugin name
        so tools from different plugins cannot collide. Empty when the tools
        directory does not exist.

    Raises:
        PluginError: If a plugin is present but cannot be loaded.
    """
    config = config or Config()
    tools_dir = Path(config.tools_dir)
    if not tools_dir.is_dir():
        return []

    toolsets: list[AbstractToolset] = []
    for name, source in _plugin_sources(tools_dir):
        toolset = _load_plugin(name, source, config)
        toolsets.append(PrefixedToolset(toolset, name))
    return toolsets


def _plugin_sources(tools_dir: Path) -> list[tuple[str, Path]]:
    """Return ``(name, source_path)`` for each plugin, sorted by name.

    A plugin is ``<name>.py`` or a ``<name>/`` package. Entries whose name
    starts with ``_`` (e.g. ``__pycache__``, private helpers) are skipped.
    """
    sources: list[tuple[str, Path]] = []
    for entry in sorted(tools_dir.iterdir()):
        if entry.name.startswith("_"):
            continue
        if entry.is_file() and entry.suffix == ".py":
            sources.append((entry.stem, entry))
        elif entry.is_dir() and (entry / "__init__.py").is_file():
            sources.append((entry.name, entry / "__init__.py"))
    return sources


def _load_plugin(name: str, source: Path, config: Config) -> AbstractToolset:
    """Import the plugin at ``source`` and call its ``get_toolset`` factory."""
    module_name = f"_bcs_agent_plugin_{name}"
    # A package plugin needs its directory as a search location so intra-package
    # imports (``from . import ...``) resolve.
    is_package = source.name == "__init__.py"
    search_locations = [str(source.parent)] if is_package else None

    try:
        spec = importlib.util.spec_from_file_location(
            module_name, source, submodule_search_locations=search_locations
        )
        if spec is None or spec.loader is None:  # pragma: no cover - defensive
            raise ImportError(f"could not create an import spec for {source}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise PluginError(f"plugin {name!r}: failed to import ({exc})") from exc

    factory = getattr(module, PLUGIN_FACTORY, None)
    if not callable(factory):
        raise PluginError(
            f"plugin {name!r}: must define a callable {PLUGIN_FACTORY}()"
        )

    try:
        toolset = factory(config) if _wants_config(factory) else factory()
    except Exception as exc:
        raise PluginError(
            f"plugin {name!r}: {PLUGIN_FACTORY}() raised ({exc})"
        ) from exc

    if not isinstance(toolset, AbstractToolset):
        raise PluginError(
            f"plugin {name!r}: {PLUGIN_FACTORY}() must return an AbstractToolset, "
            f"got {type(toolset).__name__}"
        )
    return toolset


def _wants_config(factory: object) -> bool:
    """True if ``factory`` declares a parameter -- it should receive the Config."""
    try:
        return len(inspect.signature(factory).parameters) > 0
    except (TypeError, ValueError):  # pragma: no cover - uninspectable callable
        return False
