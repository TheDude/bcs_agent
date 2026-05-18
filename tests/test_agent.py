"""Tests for :mod:`bcs_agent.agent`."""

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from bcs_agent.agent import build_agent
from bcs_agent.config import Config


def test_build_agent_returns_an_agent():
    assert isinstance(build_agent(), Agent)


def test_build_agent_uses_the_required_default_model():
    assert build_agent().model.model_name == "grok-4-1-fast-reasoning"


def test_build_agent_honors_the_configured_model():
    # The configured model string flows straight through -- choosing a model
    # is a config change, not a code change.
    agent = build_agent(Config(model="xai:grok-3"))
    assert agent.model.model_name == "grok-3"


def test_agent_produces_text_output():
    agent = build_agent()
    with agent.override(model=TestModel()):
        result = agent.run_sync("hello")
    assert isinstance(result.output, str)
    assert result.output
