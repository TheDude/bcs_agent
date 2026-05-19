# bcs-agent

A simple, model- and provider-agnostic **conversational AI agent harness**, built
on [Pydantic AI](https://ai.pydantic.dev/).

Chat with an LLM from your terminal. Each message builds on the conversation so
far, so the agent keeps context as you talk.

## Design

Four small pieces, one job each:

| Module | Responsibility |
|--------|----------------|
| `config.py`  | What model and instructions to use (`Config`, env overrides). |
| `plugins.py` | Discover installed tool plugins (`discover_toolsets`). |
| `agent.py`   | Turn a `Config` into a Pydantic AI `Agent` with its plugins attached (`build_agent`). |
| `session.py` | A multi-turn `Session` that accumulates message history. |
| `cli.py`     | The interactive `run_repl` chat loop. |

The harness is **provider-agnostic**: the model is just a Pydantic AI
`"provider:model-name"` string. Switching from xAI to OpenAI, Anthropic, Google,
etc. is a config change, not a code change. The default is
`xai:grok-4-1-fast-reasoning`.

## Setup

This project uses [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync
```

Set the API key for whichever provider you use. For the default model:

```bash
export XAI_API_KEY=...
```

## Usage

Run the chat loop:

```bash
uv run bcs-agent
# or:  uv run python -m bcs_agent
```

REPL commands: `/help`, `/reset` (clear context), `/exit` (or Ctrl-D).

### As a library

```python
from bcs_agent import Session

session = Session()
print(session.send("Hi, my name is Sam."))
print(session.send("What's my name?"))   # remembers "Sam" from the prior turn
```

### Configuration

| Variable | Effect | Default |
|----------|--------|---------|
| `BCS_AGENT_MODEL`        | Model string `provider:model-name`. | `xai:grok-4-1-fast-reasoning` |
| `BCS_AGENT_INSTRUCTIONS` | System instructions for the agent.  | a concise-assistant prompt |

```bash
BCS_AGENT_MODEL=anthropic:claude-sonnet-4-6 uv run bcs-agent
```

## Plugins

Tools are added as **plugins**: each plugin is an installable Python package
that declares an entry point in the `bcs_agent.plugins` group. The harness
discovers every installed plugin from package metadata at startup — there is no
directory to scan and nothing to configure. A deployment exposes exactly the
plugin packages installed in its environment.

### Writing a plugin

A minimal plugin package is two files. The code module defines a `get_toolset`
factory returning a Pydantic AI [toolset](https://ai.pydantic.dev/toolsets/):

```python
# bcs_plugin_clock.py
from datetime import datetime, timezone

from pydantic_ai import FunctionToolset

toolset = FunctionToolset()

@toolset.tool_plain
def current_time() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()

def get_toolset() -> FunctionToolset:   # add a `config` parameter to receive Config
    return toolset
```

and the `pyproject.toml` declares the package plus the entry point that makes it
discoverable:

```toml
[project]
name = "bcs-plugin-clock"
version = "0.1.0"
dependencies = ["pydantic-ai-slim"]

[project.entry-points."bcs_agent.plugins"]
clock = "bcs_plugin_clock:get_toolset"   # name = clock; value = module:callable

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Install it into the harness environment — from a path, or straight from Git:

```bash
uv pip install -e ./bcs-plugin-clock
uv pip install "git+https://github.com/your-org/bcs-plugin-clock@v0.1.0"
```

Two complete reference packages live in [`examples/plugins/`](examples/plugins/):
[`clock`](examples/plugins/clock/) (the minimal plugin) and
[`world_clock`](examples/plugins/world_clock/) (a tool that takes a parameter
and uses `ModelRetry` to have the model correct a bad argument). Each has a
README with install-and-try instructions.

### Key properties

- **Tool names are namespaced** by plugin (the entry-point name): `current_time`
  in plugin `clock` is exposed to the model as `clock_current_time`, so plugins
  never collide.
- **Dependencies partition per plugin.** Each plugin package declares its own
  `dependencies`; the installer resolves them automatically and a lockfile pins
  the whole tree. The harness core depends on no integration's SDK.
- **Fail fast.** A plugin that is installed but cannot load (bad import, missing
  dependency, a `get_toolset` that errors) raises `PluginError` at startup — a
  paid-for integration is never silently missing.

### External tool sources

A plugin's `get_toolset()` can return *any* Pydantic AI `AbstractToolset`,
including external sources — an `ACIToolset` (`pydantic_ai.ext.aci`), a
`LangChainToolset` (`pydantic_ai.ext.langchain`), or an MCP server. A Google
Workspace plugin, for example:

```python
# bcs_plugin_google_workspace.py
import os

def get_toolset():
    from pydantic_ai.ext.aci import ACIToolset
    return ACIToolset(
        ["GOOGLE__GMAIL_SEND", "GOOGLE__CALENDAR_LIST_EVENTS"],
        linked_account_owner_id=os.environ["ACI_LINKED_ACCOUNT_OWNER_ID"],
    )
```

with `aci-sdk` in that package's `dependencies` — pulled in only for deployments
that install this plugin.

### DevOps: per-customer products

The harness is deployed per customer, and customers pay per integration. Each
plugin is its own package/repository. A customer's product is a committed,
reviewable lock/requirements file listing the plugin packages they bought;
`uv sync` reproduces that exact environment — plugin versions plus their full
resolved dependency trees, pinned with hashes.

## Tests

```bash
uv run pytest
```

Tests use Pydantic AI's `TestModel` / `FunctionModel`, so they are deterministic
and never hit the network. Coverage is reported to the terminal.
