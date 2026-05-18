"""Interactive terminal chat loop for the harness.

``run_repl`` is written so it can be driven by tests: input and output are
injected, so a test can feed scripted lines and capture replies without a TTY.
"""

from __future__ import annotations

from collections.abc import Callable

from bcs_agent.config import Config
from bcs_agent.session import Session

#: Commands the REPL understands (anything else is sent to the agent).
HELP_TEXT = """\
Commands:
  /help    show this help
  /reset   clear the conversation context
  /exit    quit (Ctrl-D also works)"""

_BANNER = "bcs-agent -- conversational harness. Type /help for commands."


def run_repl(
    session: Session | None = None,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Run the interactive chat loop until the user exits.

    Args:
        session: Conversation to drive. A fresh one is created when omitted.
        input_fn: Reads a line of user input given a prompt string.
        output_fn: Writes a line of output.
    """
    session = session or Session()
    output_fn(_BANNER)
    output_fn(f"model: {session.config.model}")

    while True:
        try:
            line = input_fn("you> ")
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            break

        prompt = line.strip()
        if not prompt:
            continue

        if prompt in ("/exit", "/quit"):
            break
        if prompt == "/help":
            output_fn(HELP_TEXT)
            continue
        if prompt == "/reset":
            session.reset()
            output_fn("Context cleared.")
            continue

        try:
            reply = session.send(prompt)
        except Exception as exc:  # noqa: BLE001 - surface any model/provider error
            output_fn(f"error: {exc}")
            continue
        output_fn(f"agent> {reply}")

    output_fn("Goodbye.")


def main() -> None:
    """Console-script entry point: run the REPL with environment-based config."""
    run_repl(Session(Config.from_env()))


if __name__ == "__main__":
    main()
