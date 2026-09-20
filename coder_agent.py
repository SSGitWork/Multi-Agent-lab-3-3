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

_AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
_AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
_AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if _AZURE_OPENAI_ENDPOINT and _AZURE_OPENAI_API_KEY:
            _client = AsyncOpenAI(
                api_key=_AZURE_OPENAI_API_KEY,
                base_url=_AZURE_OPENAI_ENDPOINT.rstrip("/") + "/",
            )
        else:
            _client = AsyncOpenAI(
                api_key=_OPENROUTER_API_KEY,
                base_url=_HELICONE_BASE,
            )
    return _client


def _read_original_code() -> str:
    return (PROJECT_DIR / FILENAME).read_text(encoding="utf-8")


def _active_model() -> str:
    return _AZURE_OPENAI_DEPLOYMENT or MODEL


def _clean_generated_code(code: str) -> str:
    cleaned = (code or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


# ---------------------------------------------------------------------------
# TODO 1 -- Implement write_file
# ---------------------------------------------------------------------------
def write_file(filename: str, code: str) -> None:
    """Write code to PROJECT_DIR / filename using Path.write_text."""
    (PROJECT_DIR / filename).write_text(code, encoding="utf-8")


# ---------------------------------------------------------------------------
# TODO 2 -- Implement _generate_initial_code
# ---------------------------------------------------------------------------
async def _generate_initial_code(original_code: str) -> str:
    """Prompt the LLM to fix all bugs. Return corrected code string.
    Use _get_client().chat.completions.create (plain text, not structured).
    """
    response = await _get_client().chat.completions.create(
        model=_active_model(),
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise Python software engineer. Return only complete corrected Python source code. "
                    "Do not use Markdown fences. Do not include explanations."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Fix every bug in the following Python file. Preserve the intended public functions and type hints where possible.\n\n"
                    f"{original_code}"
                ),
            },
        ],
    )
    code = response.choices[0].message.content
    if not code:
        raise RuntimeError("The LLM returned no code for the initial fix.")
    return _clean_generated_code(code)


# ---------------------------------------------------------------------------
# TODO 3 -- Implement _apply_fixes
# ---------------------------------------------------------------------------
async def _apply_fixes(code: str, issues: list[dict]) -> str:
    """Prompt the LLM to fix the specific issues. Return updated code string.
    Format issues clearly: "Issue N [severity] location: description"
    """
    formatted_issues = "\n".join(
        (
            f"Issue {index} [{issue.get('severity', 'Unknown')}] "
            f"{issue.get('location', 'Unknown location')}: {issue.get('description', 'No description provided')}"
        )
        for index, issue in enumerate(issues, start=1)
    )
    response = await _get_client().chat.completions.create(
        model=_active_model(),
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise Python software engineer. Apply the QA issues to the code. Return only complete corrected Python source code without Markdown fences or explanations."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Update the following Python file to address all QA findings.\n\n"
                    f"QA findings:\n{formatted_issues}\n\nCurrent code:\n{code}"
                ),
            },
        ],
    )
    updated_code = response.choices[0].message.content
    if not updated_code:
        raise RuntimeError("The LLM returned no code while applying QA fixes.")
    return _clean_generated_code(updated_code)


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
    del server_script_path
    original_code = _read_original_code()
    code = original_code
    issues: list[dict] = []

    for iteration in range(MAX_ITERATIONS):
        if iteration == 0:
            code = await _generate_initial_code(original_code)
        else:
            code = await _apply_fixes(code, issues)

        write_file(FILENAME, code)

        review_request = Message(
            sender="coder",
            receiver="qa",
            intent="review_request",
            payload={"filename": FILENAME},
        )
        await broker.send(review_request)

        while True:
            response = await broker.receive("coder")
            if response.correlation_id != review_request.correlation_id:
                continue
            if response.intent == "approved":
                return code
            if response.intent == "fix_instruction":
                issues = response.payload.get("issues", [])
                break
            raise ValueError(f"Unexpected QA response intent: {response.intent}")

    return code
