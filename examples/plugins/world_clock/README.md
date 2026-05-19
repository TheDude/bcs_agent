# bcs-plugin-world-clock

An example [bcs-agent](../../../README.md) plugin: a tool that reports the
current date and time at a location.

A richer template than `bcs-plugin-clock` — it shows a tool that takes a
**parameter** and uses `ModelRetry` to have the model correct a bad argument.

## Try it

From the repo root:

```bash
uv pip install -e examples/plugins/world_clock
uv run bcs-agent                             # ask "what time is it in Tokyo?"
uv pip uninstall bcs-plugin-world-clock      # remove it again
```

## Dependencies

This plugin uses only the standard library. A plugin that needs a third-party
SDK (e.g. an ACI.dev or LangChain integration) declares it in the
`dependencies` list of this package's `pyproject.toml`, and the installer pulls
it in automatically — the harness core stays dependency-free.
