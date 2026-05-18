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
| `agent.py`   | Turn a `Config` into a Pydantic AI `Agent` (`build_agent`). |
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

## Tests

```bash
uv run pytest
```

Tests use Pydantic AI's `TestModel` / `FunctionModel`, so they are deterministic
and never hit the network. Coverage is reported to the terminal.
