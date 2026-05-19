"""Tests for :mod:`bcs_agent.plugins` -- filesystem plugin discovery."""

import textwrap
from pathlib import Path

import pytest
from pydantic_ai import FunctionToolset
from pydantic_ai.messages import (
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from bcs_agent.agent import build_agent
from bcs_agent.config import Config
from bcs_agent.plugins import PluginError, discover_toolsets

#: A minimal, well-formed plugin: one tool, a no-arg ``get_toolset``.
_GREET_PLUGIN = """
    from pydantic_ai import FunctionToolset

    toolset = FunctionToolset()

    @toolset.tool_plain
    def greet(name: str) -> str:
        return f"hello {name}"

    def get_toolset():
        return toolset
"""


def _make_plugin(tools_dir: Path, name: str, body: str, *, package: bool = False) -> None:
    """Write a plugin named ``name`` into ``tools_dir`` (as a file or package)."""
    if package:
        target = tools_dir / name / "__init__.py"
    else:
        target = tools_dir / f"{name}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(body))


def _config(tools_dir: Path) -> Config:
    return Config(tools_dir=str(tools_dir))


def test_discovers_a_single_file_plugin(tmp_path):
    tools = tmp_path / "tools"
    _make_plugin(tools, "greet", _GREET_PLUGIN)
    toolsets = discover_toolsets(_config(tools))
    assert len(toolsets) == 1


def test_discovers_a_package_plugin(tmp_path):
    # A package plugin is what a git submodule looks like on disk.
    tools = tmp_path / "tools"
    _make_plugin(tools, "greet", _GREET_PLUGIN, package=True)
    toolsets = discover_toolsets(_config(tools))
    assert len(toolsets) == 1


def test_get_toolset_receives_config_when_declared(tmp_path):
    # A factory that declares a parameter must be handed the Config; if it were
    # called with no args this plugin would raise TypeError -> PluginError.
    tools = tmp_path / "tools"
    _make_plugin(
        tools,
        "needs_config",
        """
        from pydantic_ai import FunctionToolset
        from bcs_agent.config import Config

        def get_toolset(config):
            assert isinstance(config, Config)
            return FunctionToolset()
        """,
    )
    assert len(discover_toolsets(_config(tools))) == 1


def test_missing_tools_dir_yields_no_toolsets(tmp_path):
    toolsets = discover_toolsets(_config(tmp_path / "does-not-exist"))
    assert toolsets == []


def test_underscore_and_non_python_entries_are_skipped(tmp_path):
    tools = tmp_path / "tools"
    _make_plugin(tools, "greet", _GREET_PLUGIN)
    _make_plugin(tools, "_private", _GREET_PLUGIN)  # leading underscore -> skip
    (tools / "notes.txt").write_text("not a plugin")  # non-.py -> skip
    (tools / "emptydir").mkdir()  # no __init__.py -> skip
    toolsets = discover_toolsets(_config(tools))
    assert len(toolsets) == 1


def test_missing_get_toolset_raises_plugin_error(tmp_path):
    tools = tmp_path / "tools"
    _make_plugin(tools, "broken", "x = 1\n")
    with pytest.raises(PluginError, match="broken"):
        discover_toolsets(_config(tools))


def test_import_failure_raises_plugin_error(tmp_path):
    tools = tmp_path / "tools"
    _make_plugin(tools, "broken", "raise RuntimeError('boom on import')\n")
    with pytest.raises(PluginError, match="failed to import"):
        discover_toolsets(_config(tools))


def test_factory_failure_raises_plugin_error(tmp_path):
    tools = tmp_path / "tools"
    _make_plugin(
        tools,
        "broken",
        """
        def get_toolset():
            raise RuntimeError('boom in factory')
        """,
    )
    with pytest.raises(PluginError, match="raised"):
        discover_toolsets(_config(tools))


def test_wrong_return_type_raises_plugin_error(tmp_path):
    tools = tmp_path / "tools"
    _make_plugin(
        tools,
        "broken",
        """
        def get_toolset():
            return "not a toolset"
        """,
    )
    with pytest.raises(PluginError, match="AbstractToolset"):
        discover_toolsets(_config(tools))


def test_discover_with_default_config_finds_no_plugins():
    # The repo's own tools/ holds only a README -- a bare agent has no tools.
    assert discover_toolsets() == []


def test_plugin_names_are_namespaced_to_prevent_collisions(tmp_path):
    tools = tmp_path / "tools"
    search_plugin = """
        from pydantic_ai import FunctionToolset
        toolset = FunctionToolset()

        @toolset.tool_plain
        def search(query: str) -> str:
            return "ok"

        def get_toolset():
            return toolset
    """
    _make_plugin(tools, "alpha", search_plugin)
    _make_plugin(tools, "beta", search_plugin)

    model = TestModel()
    agent = build_agent(_config(tools))
    with agent.override(model=model):
        agent.run_sync("hi")

    names = {t.name for t in model.last_model_request_parameters.function_tools}
    # Both plugins define a tool called ``search``; prefixing keeps them distinct.
    assert {"alpha_search", "beta_search"} <= names


def test_build_agent_attaches_discovered_plugin(tmp_path):
    tools = tmp_path / "tools"
    _make_plugin(tools, "greet", _GREET_PLUGIN)

    agent = build_agent(_config(tools))
    with agent.override(model=TestModel()):
        result = agent.run_sync("hi")

    # TestModel exercises every tool; the discovered tool was actually invoked.
    assert any(
        isinstance(part, ToolReturnPart) and "greet" in part.tool_name
        for message in result.all_messages()
        for part in message.parts
    )


def test_build_agent_honors_extra_toolsets(tmp_path):
    # extra_toolsets lets library users inject tools without plugin files.
    extra = FunctionToolset()

    @extra.tool_plain
    def ping() -> str:
        return "pong"

    agent = build_agent(_config(tmp_path / "empty"), extra_toolsets=[extra])
    model = TestModel()
    with agent.override(model=model):
        agent.run_sync("hi")

    assert "ping" in {t.name for t in model.last_model_request_parameters.function_tools}


#: examples/tools/ -- the directory holding the reference example plugins.
_EXAMPLE_TOOLS = Path(__file__).parents[1] / "examples" / "tools"


def test_example_clock_plugin_is_discoverable_and_runs():
    # Lock the minimal reference plugin in examples/tools/clock.py.
    agent = build_agent(Config(tools_dir=str(_EXAMPLE_TOOLS)))
    with agent.override(model=TestModel(call_tools=["clock_current_time"])):
        result = agent.run_sync("what time is it?")

    assert any(
        isinstance(part, ToolReturnPart) and "current_time" in part.tool_name
        for message in result.all_messages()
        for part in message.parts
    )


def test_example_world_clock_plugin_reports_a_location_time():
    # Lock the parameterized reference plugin in examples/tools/world_clock.py.
    def model(messages, info):
        parts = [p for m in messages for p in m.parts]
        if any(isinstance(p, ToolReturnPart) for p in parts):
            return ModelResponse(parts=[TextPart("reported")])
        return ModelResponse(
            parts=[
                ToolCallPart("world_clock_current_datetime", {"location": "Asia/Tokyo"})
            ]
        )

    agent = build_agent(Config(tools_dir=str(_EXAMPLE_TOOLS)))
    with agent.override(model=FunctionModel(model)):
        result = agent.run_sync("what time is it in Tokyo?")

    returns = [
        part
        for message in result.all_messages()
        for part in message.parts
        if isinstance(part, ToolReturnPart) and "current_datetime" in part.tool_name
    ]
    assert returns and "Asia/Tokyo" in str(returns[0].content)


def test_example_world_clock_plugin_retries_on_a_bad_location():
    # An unknown identifier raises ModelRetry; the model corrects and succeeds.
    def model(messages, info):
        parts = [p for m in messages for p in m.parts]
        if any(isinstance(p, ToolReturnPart) for p in parts):
            return ModelResponse(parts=[TextPart("reported")])
        corrected = any(isinstance(p, RetryPromptPart) for p in parts)
        location = "Asia/Tokyo" if corrected else "Nowhere/Fake"
        return ModelResponse(
            parts=[ToolCallPart("world_clock_current_datetime", {"location": location})]
        )

    agent = build_agent(Config(tools_dir=str(_EXAMPLE_TOOLS)))
    with agent.override(model=FunctionModel(model)):
        result = agent.run_sync("what time is it in Atlantis?")

    messages = result.all_messages()
    assert any(
        isinstance(part, RetryPromptPart)
        for message in messages
        for part in message.parts
    )
    assert result.output == "reported"
