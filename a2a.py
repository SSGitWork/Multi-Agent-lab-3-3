"""
Lab 3.3 -- a2a.py
=================
Implement the A2A message schema and in-process broker.

Valid agent names: "coder", "qa"
Valid intents:     "review_request", "fix_instruction", "approved"

Message fields
--------------
    sender:         str   -- "coder" or "qa"
    receiver:       str   -- "coder" or "qa"
    intent:         str   -- one of the valid intents above
    payload:        dict  -- intent-specific data
    correlation_id: str   -- UUID4 auto-generated if not supplied

__post_init__ must raise ValueError for:
    - sender not in VALID_AGENTS
    - receiver not in VALID_AGENTS
    - intent not in VALID_INTENTS
    - sender == receiver

Broker must expose:
    async send(message)          -- put on receiver queue; raise ValueError if unknown
    async receive(agent_name)    -- get from own queue; raise ValueError if unknown
"""

import asyncio
import uuid
from dataclasses import dataclass, field

VALID_AGENTS = {"coder", "qa"}
VALID_INTENTS = {"review_request", "fix_instruction", "approved"}


@dataclass
class Message:
    sender: str
    receiver: str
    intent: str
    payload: dict
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        if self.sender not in VALID_AGENTS:
            raise ValueError(f"Invalid sender: {self.sender}")

        if self.receiver not in VALID_AGENTS:
            raise ValueError(f"Invalid receiver: {self.receiver}")

        if self.intent not in VALID_INTENTS:
            raise ValueError(f"Invalid intent: {self.intent}")

        if self.sender == self.receiver:
            raise ValueError("sender and receiver must be different")


class Broker:
    def __init__(self) -> None:
        self._queues = {name: asyncio.Queue() for name in VALID_AGENTS}

    async def send(self, message: Message) -> None:
        if message.receiver not in self._queues:
            raise ValueError(f"Unknown receiver: {message.receiver}")

        await self._queues[message.receiver].put(message)

    async def receive(self, agent_name: str) -> Message:
        if agent_name not in self._queues:
            raise ValueError(f"Unknown agent: {agent_name}")

        return await self._queues[agent_name].get()
