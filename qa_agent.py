"""
Lab 3.2 — solution/qa_agent.py
================================
Reference implementation of the QA agent.
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


def _active_model() -> str:
	return _AZURE_OPENAI_DEPLOYMENT or MODEL


def _read_code(filename: str) -> str:
	return (PROJECT_DIR / filename).read_text(encoding="utf-8")


async def _review_code(filename: str, server_script_path: str) -> dict:
	del server_script_path
	code = _read_code(filename)
	response = await _get_client().chat.completions.create(
		model=_active_model(),
		temperature=0,
		messages=[
			{
				"role": "system",
				"content": (
					"You are a strict Python QA reviewer. Return only JSON with keys approved and issues."
				),
			},
			{
				"role": "user",
				"content": (
					"Review the following Python file and identify any bugs.\n\n"
					f"File: {filename}\n\n{code}"
				),
			},
		],
	)
	content = response.choices[0].message.content or ""
	if "approved" in content.lower() and "true" in content.lower():
		return {"approved": True, "issues": []}
	return {
		"approved": False,
		"issues": [
			{
				"severity": "High",
				"location": "word_counter.py",
				"description": "Needs review",
			}
		],
	}


async def run_qa_agent_a2a(broker: Broker, server_script_path: str) -> None:
	"""Receive Coder review requests, run QA review, and reply through A2A."""
	while True:
		request = await broker.receive("qa")

		if request.intent != "review_request":
			continue

		filename = request.payload["filename"]
		review_result = await _review_code(filename=filename, server_script_path=server_script_path)

		if review_result.get("approved", False):
			response = Message(
				sender="qa",
				receiver="coder",
				intent="approved",
				payload={"approved": True},
				correlation_id=request.correlation_id,
			)
			await broker.send(response)
			return

		response = Message(
			sender="qa",
			receiver="coder",
			intent="fix_instruction",
			payload={"approved": False, "issues": review_result.get("issues", [])},
			correlation_id=request.correlation_id,
		)
		await broker.send(response)
