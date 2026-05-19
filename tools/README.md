# `tools/` — plugin directory

Every plugin in this directory is discovered and wired into the agent at
startup. **Presence is the entitlement:** a deployment exposes exactly the
integrations that are present here — nothing more.

## Writing a plugin

A plugin is either:

- a single file — `tools/<name>.py`, or
- a package — `tools/<name>/` containing `__init__.py` (this is what a git
  submodule looks like).

The module must define a `get_toolset` factory returning a Pydantic AI
[`AbstractToolset`](https://ai.pydantic.dev/toolsets/):

```python
def get_toolset() -> AbstractToolset: ...
# or, if the plugin needs harness configuration:
def get_toolset(config: Config) -> AbstractToolset: ...
```

The harness passes the `Config` only when the factory declares a parameter.

A factory (not a module-level toolset) is required so a plugin can **lazy-import
its own SDK inside `get_toolset()`**. The harness core never imports an
integration's packages — only the plugin that needs them does, only when that
plugin is present. Each plugin/submodule therefore owns its own dependencies.

Tool names are automatically namespaced by plugin name (a tool `search` in a
plugin `web` is exposed to the model as `web_search`), so plugins cannot collide.

A plugin that is present but fails to load (bad import, missing SDK, no
`get_toolset`) raises a `PluginError` at startup — **fail fast**, so a paid-for
integration is never silently missing.

See [`examples/tools/`](../examples/tools/) for reference plugins:
[`clock.py`](../examples/tools/clock.py) (minimal) and
[`world_clock.py`](../examples/tools/world_clock.py) (a tool with a parameter
that uses `ModelRetry`).

## DevOps: per-customer products via git submodules

This harness is deployed per customer, and customers pay per integration. Model
each plugin as its own git repository and add it as a **submodule** under
`tools/`. Maintain a branch per customer whose set of submodules defines the
product that customer bought:

```
git submodule add <repo> tools/google_workspace   # on the customer's branch
```

Checking out a customer's branch yields exactly their entitled plugin set — no
separate allowlist to keep in sync.
