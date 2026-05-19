"""bcs_agent: a simple, model-agnostic conversational AI agent harness.

The public surface is intentionally small:

- ``Config``            -- how the harness is configured (model, instructions).
- ``build_agent``       -- construct a Pydantic AI ``Agent`` from a ``Config``.
- ``Session``           -- a multi-turn conversation that accumulates context.
- ``run_repl``          -- an interactive terminal chat loop.
- ``discover_toolsets`` -- discover tool plugins from installed packages.
- ``PluginError``       -- raised when a plugin is installed but cannot be loaded.
"""

from bcs_agent.agent import build_agent
from bcs_agent.cli import run_repl
from bcs_agent.config import Config
from bcs_agent.plugins import PluginError, discover_toolsets
from bcs_agent.session import Session

__all__ = [
    "Config",
    "PluginError",
    "Session",
    "build_agent",
    "discover_toolsets",
    "run_repl",
]
