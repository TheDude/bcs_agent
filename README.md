# bcs-agent

A simple, model- and provider-agnostic **conversational AI agent harness**, built
on [Pydantic AI](https://ai.pydantic.dev/).

Chat with an LLM from your terminal. Each message builds on the conversation so
far, so the agent keeps context as you talk.

## Design

Four small pieces, one job each:

| Module | Responsibility |
|--------|----------------|
| `config.py`  | What model, instructions, and tools directory to use (`Config`, env overrides). |
| `plugins.py` | Discover tool plugins from the `tools/` directory (`discover_toolsets`). |
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
| `BCS_AGENT_MODEL`        | Model string `provider:model-name`.   | `xai:grok-4-1-fast-reasoning` |
| `BCS_AGENT_INSTRUCTIONS` | System instructions for the agent.    | a concise-assistant prompt |
| `BCS_AGENT_TOOLS_DIR`    | Directory scanned for tool plugins.   | `tools` |

```bash
BCS_AGENT_MODEL=anthropic:claude-sonnet-4-6 uv run bcs-agent
```

## Plugins

Tools are added as **plugins** — files or directories dropped into the `tools/`
folder. Every plugin present is discovered and wired into the agent at startup;
**presence is the entitlement**, so a deployment exposes exactly the
integrations that are there.

A plugin is either `tools/<name>.py` or a package `tools/<name>/` (the latter is
what a git submodule looks like). It defines a `get_toolset` factory returning a
Pydantic AI [toolset](https://ai.pydantic.dev/toolsets/):

```python
from pydantic_ai import FunctionToolset

toolset = FunctionToolset()

@toolset.tool_plain
def current_time() -> str:
    """Return the current UTC time in ISO-8601 format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

def get_toolset() -> FunctionToolset:   # add a `config` parameter to receive Config
    return toolset
```

Two reference plugins live in [`examples/tools/`](examples/tools/):

- [`clock.py`](examples/tools/clock.py) — the minimal plugin (one no-arg tool).
- [`world_clock.py`](examples/tools/world_clock.py) — a tool that takes a
  location argument and uses `ModelRetry` to have the model correct a bad one.

```bash
BCS_AGENT_TOOLS_DIR=examples/tools uv run bcs-agent
```

Key properties:

- **Tool names are namespaced** by plugin (`current_time` in plugin `clock` is
  exposed to the model as `clock_current_time`), so plugins never collide.
- **Dependencies partition per plugin.** Because `get_toolset()` is a factory, a
  plugin lazy-imports its own SDK *inside* the function — the harness core never
  depends on any integration's packages, only the plugins present do.
- **Fail fast.** A plugin that is present but cannot load (bad import, missing
  SDK, no `get_toolset`) raises `PluginError` at startup — a paid-for
  integration is never silently missing.

### External tool sources

Any Pydantic AI `AbstractToolset` works as a plugin's return value, including
external sources — a plugin can `return` an `ACIToolset` (`pydantic_ai.ext.aci`)
or `LangChainToolset` (`pydantic_ai.ext.langchain`), or an MCP server. For
example, a future Google Workspace plugin:

```python
# tools/google_workspace/__init__.py  (a git submodule)
def get_toolset(config):
    from pydantic_ai.ext.aci import ACIToolset   # lazy: only this plugin needs aci-sdk
    import os
    return ACIToolset(
        ["GOOGLE__GMAIL_SEND", "GOOGLE__CALENDAR_LIST_EVENTS"],
        linked_account_owner_id=os.environ["ACI_LINKED_ACCOUNT_OWNER_ID"],
    )
```

### DevOps: per-customer products

This harness is deployed per customer, with customers paying per integration.
Model each plugin as its own git repository and add it as a **submodule** under
`tools/`, on a branch per customer. Checking out a customer's branch yields
exactly their entitled plugin set — no separate allowlist to keep in sync.

## Tests

```bash
uv run pytest
```

Tests use Pydantic AI's `TestModel` / `FunctionModel`, so they are deterministic
and never hit the network. Coverage is reported to the terminal.
