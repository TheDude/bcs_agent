"""Tests for :mod:`bcs_agent.session` -- the conversational core."""

from pydantic_ai import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from bcs_agent.agent import build_agent
from bcs_agent.session import Session


def _history_size_model(messages, info):
    """A model whose reply reports how many messages it was given as context."""
    return ModelResponse(parts=[TextPart(content=f"history={len(messages)}")])


def test_send_returns_text():
    session = Session()
    with session.agent.override(model=TestModel()):
        reply = session.send("hi")
    assert isinstance(reply, str)
    assert reply


def test_context_accumulates_across_turns():
    """Each turn must see more context than the one before it."""
    session = Session()
    with session.agent.override(model=FunctionModel(_history_size_model)):
        first = session.send("turn one")
        second = session.send("turn two")

    seen_first = int(first.split("=")[1])
    seen_second = int(second.split("=")[1])
    assert seen_second > seen_first  # second turn carries the first turn's history

    assert session.turn_count == 2
    # 2 user requests + 2 model responses retained for the next turn.
    assert len(session.messages) == 4


async def test_send_async_also_accumulates_context():
    session = Session()
    with session.agent.override(model=TestModel()):
        await session.send_async("one")
        await session.send_async("two")
    assert session.turn_count == 2


def test_messages_property_returns_a_copy():
    session = Session()
    with session.agent.override(model=TestModel()):
        session.send("hi")
    snapshot = session.messages
    snapshot.clear()
    assert session.messages, "mutating the returned list must not affect the session"


def test_reset_clears_context():
    session = Session()
    with session.agent.override(model=TestModel()):
        session.send("hi")
        assert session.messages
        session.reset()
    assert session.messages == []
    assert session.turn_count == 0


def test_session_reuses_an_injected_agent():
    agent = build_agent()
    session = Session(agent=agent)
    assert session.agent is agent
