"""Tests for :mod:`bcs_agent.cli` -- the interactive REPL."""

from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from bcs_agent.cli import HELP_TEXT, main, run_repl
from bcs_agent.session import Session


def _scripted_input(lines):
    """Build an ``input_fn`` that returns each line, then raises EOF."""
    lines_iter = iter(lines)

    def _input(prompt: str = "") -> str:
        try:
            return next(lines_iter)
        except StopIteration:
            raise EOFError

    return _input


def _drive(lines, session):
    """Run the REPL against scripted ``lines``; return (output_lines, session)."""
    out: list[str] = []
    run_repl(session, input_fn=_scripted_input(lines), output_fn=out.append)
    return out, session


def test_repl_exits_on_command():
    session = Session()
    with session.agent.override(model=TestModel()):
        out, _ = _drive(["/exit"], session)
    assert out[-1] == "Goodbye."


def test_repl_exits_on_eof():
    session = Session()
    with session.agent.override(model=TestModel()):
        out, _ = _drive([], session)
    assert "Goodbye." in out


def test_repl_sends_messages_to_the_agent():
    session = Session()
    with session.agent.override(model=TestModel()):
        out, session = _drive(["hello", "/exit"], session)
    assert any(line.startswith("agent> ") for line in out)
    assert session.turn_count == 1


def test_repl_help_command():
    session = Session()
    with session.agent.override(model=TestModel()):
        out, _ = _drive(["/help", "/exit"], session)
    assert HELP_TEXT in out


def test_repl_reset_command_clears_context():
    session = Session()
    with session.agent.override(model=TestModel()):
        out, session = _drive(["hi", "/reset", "/exit"], session)
    assert "Context cleared." in out
    assert session.messages == []


def test_repl_ignores_blank_input():
    session = Session()
    with session.agent.override(model=TestModel()):
        out, session = _drive(["", "   ", "/exit"], session)
    assert session.turn_count == 0


def test_repl_reports_agent_errors_without_crashing():
    def _failing_model(messages, info):
        raise RuntimeError("provider unavailable")

    session = Session()
    with session.agent.override(model=FunctionModel(_failing_model)):
        out, session = _drive(["hi", "/exit"], session)
    assert any(line.startswith("error: ") for line in out)
    assert out[-1] == "Goodbye."  # the loop survived the error


def test_main_starts_a_repl(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "bcs_agent.cli.run_repl", lambda session: captured.setdefault("session", session)
    )
    main()
    assert isinstance(captured["session"], Session)
