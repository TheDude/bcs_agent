"""Tests for :mod:`bcs_agent.config`."""

from bcs_agent.config import DEFAULT_INSTRUCTIONS, DEFAULT_MODEL, Config


def test_defaults_match_required_model():
    config = Config()
    assert config.model == DEFAULT_MODEL == "xai:grok-4-1-fast-reasoning"
    assert config.instructions == DEFAULT_INSTRUCTIONS


def test_explicit_construction_is_provider_agnostic():
    config = Config(model="anthropic:claude-sonnet-4-6", instructions="Be terse.")
    assert config.model == "anthropic:claude-sonnet-4-6"
    assert config.instructions == "Be terse."


def test_from_env_falls_back_to_defaults(monkeypatch):
    monkeypatch.delenv("BCS_AGENT_MODEL", raising=False)
    monkeypatch.delenv("BCS_AGENT_INSTRUCTIONS", raising=False)
    config = Config.from_env()
    assert config.model == DEFAULT_MODEL
    assert config.instructions == DEFAULT_INSTRUCTIONS


def test_from_env_overrides_model_and_instructions(monkeypatch):
    monkeypatch.setenv("BCS_AGENT_MODEL", "openai:gpt-5.2")
    monkeypatch.setenv("BCS_AGENT_INSTRUCTIONS", "Speak like a pirate.")
    config = Config.from_env()
    assert config.model == "openai:gpt-5.2"
    assert config.instructions == "Speak like a pirate."
