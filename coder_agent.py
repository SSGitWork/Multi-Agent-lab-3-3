"""
Lab 3.3 -- coder_agent.py
=========================
Implement the Coder agent A2A loop.

Do NOT change MAX_ITERATIONS, FILENAME, PROJECT_DIR, _get_client(),
MODEL, or _read_original_code().
"""

import asyncio
import pathlib
import os
from dotenv import load_dotenv
load_dotenv(override=True)

from openai import AsyncOpenAI
from a2a import Broker, Message

MAX_ITERATIONS = 3
FILENAME = "word_counter.py"
PROJECT_DIR = pathlib.Path(__file__).parent / "project_files"

_client: AsyncOpenAI | None = None
MODEL = "gpt-4.1-mini"

_HELICONE_BASE = os.getenv("HELICONE_BASE_URL")
_OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
_HELICONE_API_KEY = os.getenv("HELICONE_API_KEY")


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=_OPENROUTER_API_KEY,
            base_url=_HELICONE_BASE,
        )
    return _client


def _read_original_code() -> str:
    return (PROJECT_DIR / FILENAME).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# TODO 1 -- Implement write_file
# ---------------------------------------------------------------------------
def write_file(filename: str, code: str) -> None:
    """Write code to PROJECT_DIR / filename using Path.write_text."""
    raise NotImplementedError("TODO 1: Implement write_file.")


# ---------------------------------------------------------------------------
# TODO 2 -- Implement _generate_initial_code
# ---------------------------------------------------------------------------
async def _generate_initial_code(original_code: str) -> str:
    """Prompt the LLM to fix all bugs. Return corrected code string.
    Use _get_client().chat.completions.create (plain text, not structured).
    """
    raise NotImplementedError("TODO 2: Implement _generate_initial_code.")


# ---------------------------------------------------------------------------
# TODO 3 -- Implement _apply_fixes
# ---------------------------------------------------------------------------
async def _apply_fixes(code: str, issues: list[dict]) -> str:
    """Prompt the LLM to fix the specific issues. Return updated code string.
    Format issues clearly: "Issue N [severity] location: description"
    """
    raise NotImplementedError("TODO 3: Implement _apply_fixes.")


# ---------------------------------------------------------------------------
# TODO 4 -- Implement run_coder_agent
# ---------------------------------------------------------------------------
async def run_coder_agent(broker: Broker, server_script_path: str) -> str:
    """A2A loop: generate/fix -> write -> send review_request -> receive -> repeat.

    Returns the final code string (approved or last attempt).

    Loop:
        for iteration in range(MAX_ITERATIONS):
            code = _generate_initial_code or _apply_fixes
            write_file(FILENAME, code)
            send review_request (store correlation_id)
            response = await broker.receive("coder")
            if approved: return code
            if fix_instruction: extract issues, continue
        return code
    """
    raise NotImplementedError("TODO 4: Implement run_coder_agent.")
