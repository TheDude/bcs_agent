"""A multi-turn conversation that accumulates context.

A :class:`Session` is the heart of the harness. Each turn is sent to the agent
together with the full message history of the conversation so far, so the model
builds context as the user chats. Pydantic AI's ``message_history`` does the
heavy lifting; this class just owns the growing list of messages.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage

from bcs_agent.agent import build_agent
from bcs_agent.config import Config


class Session:
    """A stateful, conversational wrapper around a Pydantic AI agent.

    Args:
        config: Harness configuration. Defaults to :class:`Config` defaults.
        agent: An existing agent to reuse. Built from ``config`` when omitted.
    """

    def __init__(
        self,
        config: Config | None = None,
        agent: Agent[None, str] | None = None,
    ) -> None:
        self.config = config or Config()
        self.agent = agent or build_agent(self.config)
        self._messages: list[ModelMessage] = []

    @property
    def messages(self) -> list[ModelMessage]:
        """A copy of the accumulated conversation history."""
        return list(self._messages)

    @property
    def turn_count(self) -> int:
        """Number of completed user/agent exchanges in this session."""
        from pydantic_ai.messages import ModelRequest

        return sum(isinstance(m, ModelRequest) for m in self._messages)

    def send(self, prompt: str) -> str:
        """Send ``prompt`` to the agent and return its text reply (synchronous).

        The full prior history is passed as context, and the updated history --
        including this exchange -- is retained for the next turn.
        """
        result = self.agent.run_sync(prompt, message_history=self._messages)
        self._messages = result.all_messages()
        return result.output

    async def send_async(self, prompt: str) -> str:
        """Async counterpart of :meth:`send`."""
        result = await self.agent.run(prompt, message_history=self._messages)
        self._messages = result.all_messages()
        return result.output

    def reset(self) -> None:
        """Forget all conversation history, starting a fresh context."""
        self._messages = []
