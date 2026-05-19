# bcs-plugin-clock

An example [bcs-agent](../../../README.md) plugin: a one-tool clock. Use it as a
template for your own plugins.

A plugin is an **installable package** that declares a `bcs_agent.plugins` entry
point pointing at a `get_toolset()` factory. The minimal package is two files:

- `pyproject.toml` — declares the package and the entry point.
- `bcs_plugin_clock.py` — the code, defining `get_toolset()`.

## Try it

From the repo root:

```bash
uv pip install -e examples/plugins/clock
uv run bcs-agent                       # ask "what time is it?"
uv pip uninstall bcs-plugin-clock      # remove it again
```

The harness discovers the plugin from package metadata once it is installed —
there is no directory to scan and nothing else to configure.
