"""Tests for :mod:`bcs_agent.plugins` -- entry-point plugin discovery."""

import importlib.metadata
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
from bcs_agent.plugins import PLUGIN_GROUP, PluginError, discover_toolsets

#: examples/plugins/ -- the directory holding the reference example packages.
_EXAMPLE_PLUGINS = Path(__file__).parents[1] / "examples" / "plugins"


class _FakeEntryPoint:
    """Minimal stand-in for importlib.metadata.EntryPoint (``.name`` + ``.load()``).

    ``target`` is what ``load()`` returns; if it is an exception instance,
    ``load()`` raises it instead -- to simulate a plugin that fails to import.
    """

    def __init__(self, name: str, target: object) -> None:
        self.name = name
        self._target = target

    def load(self) -> object:
        if isinstance(self._target, BaseException):
            raise self._target
        return self._target


# --- factory functions an entry point might point at -------------------------

def _greet_toolset() -> FunctionToolset:
    toolset = FunctionToolset()

    @toolset.tool_plain
    def greet(name: str) -> str:
        return f"hello {name}"

    return toolset


def _search_toolset() -> FunctionToolset:
    toolset = FunctionToolset()

    @toolset.tool_plain
    def search(query: str) -> str:
        return "ok"

    return toolset


def _config_toolset(config: Config) -> FunctionToolset:
    # If discovery called this with no args, it would raise TypeError.
    assert isinstance(config, Config)
    return FunctionToolset()


def _raising_factory() -> FunctionToolset:
    raise RuntimeError("boom in factory")


def _wrong_type_factory() -> str:
    return "not a toolset"


# --- discovery ---------------------------------------------------------------

def test_no_entry_points_yields_no_toolsets():
    assert discover_toolsets(entry_points=[]) == []


def test_default_discovery_reads_installed_packages():
    # No plugin packages are installed in the test environment.
    assert discover_toolsets() == []


def test_discovers_a_plugin():
    toolsets = discover_toolsets(
        entry_points=[_FakeEntryPoint("greet", _greet_toolset)]
    )
    assert len(toolsets) == 1


def test_config_is_forwarded_to_factories_that_declare_it():
    toolsets = discover_toolsets(
        entry_points=[_FakeEntryPoint("cfg", _config_toolset)]
    )
    assert len(toolsets) == 1


def test_entry_point_load_failure_raises_plugin_error():
    ep = _FakeEntryPoint("broken", ImportError("no such module"))
    with pytest.raises(PluginError, match="failed to load"):
        discover_toolsets(entry_points=[ep])


def test_non_callable_entry_point_raises_plugin_error():
    ep = _FakeEntryPoint("broken", 42)
    with pytest.raises(PluginError, match="callable"):
        discover_toolsets(entry_points=[ep])


def test_factory_failure_raises_plugin_error():
    ep = _FakeEntryPoint("broken", _raising_factory)
    with pytest.raises(PluginError, match="raised"):
        discover_toolsets(entry_points=[ep])


def test_wrong_return_type_raises_plugin_error():
    ep = _FakeEntryPoint("broken", _wrong_type_factory)
    with pytest.raises(PluginError, match="AbstractToolset"):
        discover_toolsets(entry_points=[ep])


def test_plugin_names_are_namespaced_to_prevent_collisions():
    toolsets = discover_toolsets(
        entry_points=[
            _FakeEntryPoint("alpha", _search_toolset),
            _FakeEntryPoint("beta", _search_toolset),
        ]
    )
    model = TestModel()
    agent = build_agent(extra_toolsets=toolsets)
    with agent.override(model=model):
        agent.run_sync("hi")

    names = {t.name for t in model.last_model_request_parameters.function_tools}
    # Both plugins expose a tool called ``search``; prefixing keeps them distinct.
    assert {"alpha_search", "beta_search"} <= names


def test_build_agent_honors_extra_toolsets():
    extra = FunctionToolset()

    @extra.tool_plain
    def ping() -> str:
        return "pong"

    model = TestModel()
    agent = build_agent(extra_toolsets=[extra])
    with agent.override(model=model):
        agent.run_sync("hi")

    assert "ping" in {t.name for t in model.last_model_request_parameters.function_tools}


# --- example plugin packages -------------------------------------------------

def _example_entry_point(name, module, monkeypatch):
    """Make an example package importable and return a real EntryPoint for it."""
    monkeypatch.syspath_prepend(str(_EXAMPLE_PLUGINS / name))
    return importlib.metadata.EntryPoint(
        name=name, value=f"{module}:get_toolset", group=PLUGIN_GROUP
    )


def test_example_clock_plugin_loads_via_a_real_entry_point(monkeypatch):
    ep = _example_entry_point("clock", "bcs_plugin_clock", monkeypatch)
    toolsets = discover_toolsets(entry_points=[ep])
    assert len(toolsets) == 1

    agent = build_agent(extra_toolsets=toolsets)
    with agent.override(model=TestModel()):
        result = agent.run_sync("what time is it?")

    assert any(
        isinstance(part, ToolReturnPart) and "current_time" in part.tool_name
        for message in result.all_messages()
        for part in message.parts
    )


def test_example_world_clock_plugin_reports_a_location_time(monkeypatch):
    ep = _example_entry_point("world_clock", "bcs_plugin_world_clock", monkeypatch)
    toolsets = discover_toolsets(entry_points=[ep])

    def model(messages, info):
        parts = [p for m in messages for p in m.parts]
        if any(isinstance(p, ToolReturnPart) for p in parts):
            return ModelResponse(parts=[TextPart("reported")])
        return ModelResponse(
            parts=[
                ToolCallPart("world_clock_current_datetime", {"location": "Asia/Tokyo"})
            ]
        )

    agent = build_agent(extra_toolsets=toolsets)
    with agent.override(model=FunctionModel(model)):
        result = agent.run_sync("what time is it in Tokyo?")

    returns = [
        part
        for message in result.all_messages()
        for part in message.parts
        if isinstance(part, ToolReturnPart) and "current_datetime" in part.tool_name
    ]
    assert returns and "Asia/Tokyo" in str(returns[0].content)


def test_example_world_clock_plugin_retries_on_a_bad_location(monkeypatch):
    ep = _example_entry_point("world_clock", "bcs_plugin_world_clock", monkeypatch)
    toolsets = discover_toolsets(entry_points=[ep])

    def model(messages, info):
        parts = [p for m in messages for p in m.parts]
        if any(isinstance(p, ToolReturnPart) for p in parts):
            return ModelResponse(parts=[TextPart("reported")])
        corrected = any(isinstance(p, RetryPromptPart) for p in parts)
        location = "Asia/Tokyo" if corrected else "Nowhere/Fake"
        return ModelResponse(
            parts=[ToolCallPart("world_clock_current_datetime", {"location": location})]
        )

    agent = build_agent(extra_toolsets=toolsets)
    with agent.override(model=FunctionModel(model)):
        result = agent.run_sync("what time is it in Atlantis?")

    messages = result.all_messages()
    assert any(
        isinstance(part, RetryPromptPart)
        for message in messages
        for part in message.parts
    )
    assert result.output == "reported"
