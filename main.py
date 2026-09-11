"""
Lab 3.3 — main.py
=================
Orchestrates the full Coder ↔ QA A2A review loop.

The Coder and QA agents run as concurrent asyncio tasks sharing a Broker.
Do NOT modify this file.

Usage
-----
    python main.py
"""

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from a2a import Broker
from coder_agent import run_coder_agent
from qa_agent import run_qa_agent_a2a

MCP_SERVER = str(pathlib.Path(__file__).parent / "mcp_server.py")


async def main() -> None:
    print("=" * 55)
    print("Lab 3.3 — Coder ↔ QA A2A Review Loop")
    print("=" * 55)

    broker = Broker()

    # Run both agents concurrently — they communicate through the broker
    coder_task = asyncio.create_task(
        run_coder_agent(broker, MCP_SERVER)
    )
    qa_task = asyncio.create_task(
        run_qa_agent_a2a(broker, MCP_SERVER)
    )

    final_code, _ = await asyncio.gather(coder_task, qa_task)

    print("\n" + "=" * 55)
    print("Final code:")
    print("=" * 55)
    print(final_code)


if __name__ == "__main__":
    asyncio.run(main())
