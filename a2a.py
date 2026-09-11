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
from typing import Any

VALID_AGENTS = {"coder", "qa"}
VALID_INTENTS = {"review_request", "fix_instruction", "approved"}


# ---------------------------------------------------------------------------
# TODO 1 -- Define the Message dataclass
# ---------------------------------------------------------------------------
# @dataclass
# class Message:
#     sender:         str
#     receiver:       str
#     intent:         str
#     payload:        dict
#     correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
#
# def __post_init__(self):  validate all four constraints above
raise NotImplementedError("TODO 1: Define the Message dataclass.")


# ---------------------------------------------------------------------------
# TODO 2 -- Define the Broker class
# ---------------------------------------------------------------------------
# class Broker:
#     def __init__(self):
#         self._queues = {name: asyncio.Queue() for name in VALID_AGENTS}
#     async def send(self, message): ...
#     async def receive(self, agent_name): ...
raise NotImplementedError("TODO 2: Define the Broker class.")
