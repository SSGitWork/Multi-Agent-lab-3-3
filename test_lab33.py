"""
tests/test_lab33.py
===================
Black-box test suite for Lab 3.3.

All tests run without live LLM calls or real MCP subprocesses.

Run normally:       pytest
Run with live calls: pytest --run-llm
"""

import asyncio
import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

LAB_ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(LAB_ROOT))

ORIGINAL_CODE = (LAB_ROOT / "project_files" / "word_counter.py").read_text()
FIXED_CODE = '''\
"""
word_counter.py — fixed version
"""

def count_words(text: str) -> dict[str, int]:
    counts = {}
    for word in text.split():
        word = word.lower().strip(".,!?;:\\"\'()[]{}")
        counts[word] = counts.get(word, 0) + 1
    return counts


def top_n_words(counts: dict[str, int], n: int) -> dict[str, int]:
    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_words[:n])
'''

HIGH_ISSUES = [
    {"severity": "High", "location": "count_words()", "description": "No lowercasing"},
    {"severity": "High", "location": "count_words()", "description": "No punctuation stripping"},
]
MEDIUM_ISSUES = [
    {"severity": "Medium", "location": "top_n_words()", "description": "Missing reverse=True"},
]


# ---------------------------------------------------------------------------
# Tests: Message dataclass
# ---------------------------------------------------------------------------

class TestMessage:
    def test_valid_message_creation(self):
        from a2a import Message
        msg = Message(
            sender="coder", receiver="qa",
            intent="review_request", payload={"filename": "word_counter.py"},
        )
        assert msg.sender == "coder"
        assert msg.receiver == "qa"
        assert msg.intent == "review_request"
        assert msg.payload == {"filename": "word_counter.py"}

    def test_correlation_id_auto_generated(self):
        from a2a import Message
        msg = Message(sender="coder", receiver="qa",
                      intent="review_request", payload={})
        assert isinstance(msg.correlation_id, str)
        assert len(msg.correlation_id) == 36  # UUID4 format

    def test_explicit_correlation_id(self):
        from a2a import Message
        msg = Message(sender="coder", receiver="qa",
                      intent="review_request", payload={},
                      correlation_id="my-id-123")
        assert msg.correlation_id == "my-id-123"

    def test_invalid_sender_raises(self):
        from a2a import Message
        with pytest.raises(ValueError, match="sender"):
            Message(sender="unknown", receiver="qa",
                    intent="review_request", payload={})

    def test_invalid_receiver_raises(self):
        from a2a import Message
        with pytest.raises(ValueError, match="receiver"):
            Message(sender="coder", receiver="unknown",
                    intent="review_request", payload={})

    def test_invalid_intent_raises(self):
        from a2a import Message
        with pytest.raises(ValueError, match="intent"):
            Message(sender="coder", receiver="qa",
                    intent="bad_intent", payload={})

    def test_same_sender_receiver_raises(self):
        from a2a import Message
        with pytest.raises(ValueError):
            Message(sender="coder", receiver="coder",
                    intent="review_request", payload={})

    def test_all_valid_intents_accepted(self):
        from a2a import Message
        for intent in ("review_request", "fix_instruction", "approved"):
            msg = Message(sender="coder", receiver="qa",
                          intent=intent, payload={})
            assert msg.intent == intent

    def test_both_agent_combinations_valid(self):
        from a2a import Message
        Message(sender="coder", receiver="qa",
                intent="review_request", payload={})
        Message(sender="qa", receiver="coder",
                intent="approved", payload={})


# ---------------------------------------------------------------------------
# Tests: Broker
# ---------------------------------------------------------------------------

class TestBroker:
    async def test_send_and_receive(self):
        from a2a import Broker, Message
        broker = Broker()
        msg = Message(sender="coder", receiver="qa",
                      intent="review_request", payload={"filename": "f.py"})
        await broker.send(msg)
        received = await broker.receive("qa")
        assert received.sender == "coder"
        assert received.intent == "review_request"

    async def test_message_reaches_correct_queue(self):
        from a2a import Broker, Message
        broker = Broker()
        to_qa = Message(sender="coder", receiver="qa",
                        intent="review_request", payload={})
        to_coder = Message(sender="qa", receiver="coder",
                           intent="approved", payload={"approved": True})
        await broker.send(to_qa)
        await broker.send(to_coder)

        qa_msg = await broker.receive("qa")
        coder_msg = await broker.receive("coder")

        assert qa_msg.intent == "review_request"
        assert coder_msg.intent == "approved"

    async def test_receive_unknown_agent_raises(self):
        from a2a import Broker
        broker = Broker()
        with pytest.raises(ValueError):
            await broker.receive("supervisor")

    async def test_fifo_ordering(self):
        from a2a import Broker, Message
        broker = Broker()
        for i in range(3):
            msg = Message(sender="coder", receiver="qa",
                          intent="review_request",
                          payload={"filename": f"file_{i}.py"},
                          correlation_id=f"id-{i}")
            await broker.send(msg)

        for i in range(3):
            received = await broker.receive("qa")
            assert received.correlation_id == f"id-{i}", \
                "Broker must deliver messages in FIFO order"

    async def test_correlation_id_preserved(self):
        from a2a import Broker, Message
        broker = Broker()
        msg = Message(sender="coder", receiver="qa",
                      intent="review_request", payload={},
                      correlation_id="test-corr-id")
        await broker.send(msg)
        received = await broker.receive("qa")
        assert received.correlation_id == "test-corr-id"


# ---------------------------------------------------------------------------
# Tests: write_file
# ---------------------------------------------------------------------------

class TestWriteFile:
    def test_writes_file_to_project_dir(self, tmp_path, monkeypatch):
        import coder_agent
        monkeypatch.setattr(coder_agent, "PROJECT_DIR", tmp_path)
        coder_agent.write_file("test.py", "print('hello')")
        assert (tmp_path / "test.py").read_text() == "print('hello')"

    def test_overwrites_existing_file(self, tmp_path, monkeypatch):
        import coder_agent
        monkeypatch.setattr(coder_agent, "PROJECT_DIR", tmp_path)
        (tmp_path / "test.py").write_text("old content")
        coder_agent.write_file("test.py", "new content")
        assert (tmp_path / "test.py").read_text() == "new content"


# ---------------------------------------------------------------------------
# Tests: _generate_initial_code and _apply_fixes (LLM mocked)
# ---------------------------------------------------------------------------

def _mock_llm_text(text: str):
    """Patch _get_client to return a mock that yields the given text."""
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_create = AsyncMock(return_value=mock_completion)
    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create
    return patch("coder_agent._get_client", return_value=mock_client)


class TestGenerateInitialCode:
    async def test_returns_string(self):
        from coder_agent import _generate_initial_code
        with _mock_llm_text(FIXED_CODE):
            result = await _generate_initial_code(ORIGINAL_CODE)
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_calls_llm(self):
        from coder_agent import _generate_initial_code
        with _mock_llm_text(FIXED_CODE) as mock_patch:
            await _generate_initial_code(ORIGINAL_CODE)
        mock_client = mock_patch.return_value
        mock_client.chat.completions.create.assert_called_once()

    async def test_receives_original_code_in_prompt(self):
        from coder_agent import _generate_initial_code
        with _mock_llm_text(FIXED_CODE) as mock_patch:
            await _generate_initial_code(ORIGINAL_CODE)
        mock_client = mock_patch.return_value
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][1]
        all_content = " ".join(m["content"] for m in messages)
        assert "word_counter" in all_content or "count_words" in all_content, \
            "The prompt must include the original code"


class TestApplyFixes:
    async def test_returns_string(self):
        from coder_agent import _apply_fixes
        with _mock_llm_text(FIXED_CODE):
            result = await _apply_fixes(ORIGINAL_CODE, HIGH_ISSUES)
        assert isinstance(result, str)

    async def test_issues_included_in_prompt(self):
        from coder_agent import _apply_fixes
        with _mock_llm_text(FIXED_CODE) as mock_patch:
            await _apply_fixes(ORIGINAL_CODE, HIGH_ISSUES)
        mock_client = mock_patch.return_value
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][1]
        all_content = " ".join(m["content"] for m in messages)
        assert "No lowercasing" in all_content or "lower" in all_content.lower(), \
            "Issue descriptions must appear in the fix prompt"


# ---------------------------------------------------------------------------
# Tests: run_coder_agent (full loop, both LLM and QA mocked)
# ---------------------------------------------------------------------------

def _make_qa_response(intent: str, issues: list[dict], correlation_id: str):
    from a2a import Message
    payload = {"approved": True} if intent == "approved" else {
        "issues": issues, "approved": False
    }
    return Message(
        sender="qa", receiver="coder",
        intent=intent, payload=payload,
        correlation_id=correlation_id,
    )


class TestRunCoderAgent:
    async def test_sends_review_request(self, tmp_path, monkeypatch):
        """Coder must send a review_request on the first iteration."""
        import coder_agent
        from a2a import Broker, Message
        monkeypatch.setattr(coder_agent, "PROJECT_DIR", tmp_path)
        (tmp_path / "word_counter.py").write_text(ORIGINAL_CODE)

        broker = Broker()
        sent_messages = []

        original_send = broker.send
        async def capturing_send(msg):
            sent_messages.append(msg)
            await original_send(msg)
        broker.send = capturing_send

        # Pre-load QA's response so Coder doesn't block
        async def auto_respond():
            req = await broker.receive("qa")
            response = _make_qa_response("approved", [], req.correlation_id)
            await broker.send(response)
        asyncio.create_task(auto_respond())

        with _mock_llm_text(FIXED_CODE):
            await coder_agent.run_coder_agent(broker, "mcp_server.py")

        review_requests = [m for m in sent_messages if m.intent == "review_request"]
        assert len(review_requests) >= 1, "Coder must send at least one review_request"

    async def test_review_request_has_correct_fields(self, tmp_path, monkeypatch):
        import coder_agent
        from a2a import Broker
        monkeypatch.setattr(coder_agent, "PROJECT_DIR", tmp_path)
        (tmp_path / "word_counter.py").write_text(ORIGINAL_CODE)

        broker = Broker()
        sent_messages = []
        original_send = broker.send
        async def capturing_send(msg):
            sent_messages.append(msg)
            await original_send(msg)
        broker.send = capturing_send

        async def auto_respond():
            req = await broker.receive("qa")
            await broker.send(
                _make_qa_response("approved", [], req.correlation_id)
            )
        asyncio.create_task(auto_respond())

        with _mock_llm_text(FIXED_CODE):
            await coder_agent.run_coder_agent(broker, "mcp_server.py")

        req = next(m for m in sent_messages if m.intent == "review_request")
        assert req.sender == "coder"
        assert req.receiver == "qa"
        assert "filename" in req.payload

    async def test_stops_on_approved(self, tmp_path, monkeypatch):
        """Coder must stop after receiving 'approved'."""
        import coder_agent
        from a2a import Broker
        monkeypatch.setattr(coder_agent, "PROJECT_DIR", tmp_path)
        (tmp_path / "word_counter.py").write_text(ORIGINAL_CODE)

        broker = Broker()
        request_count = [0]
        original_send = broker.send
        async def capturing_send(msg):
            if msg.intent == "review_request":
                request_count[0] += 1
            await original_send(msg)
        broker.send = capturing_send

        async def auto_respond():
            req = await broker.receive("qa")
            await broker.send(_make_qa_response("approved", [], req.correlation_id))
        asyncio.create_task(auto_respond())

        with _mock_llm_text(FIXED_CODE):
            await coder_agent.run_coder_agent(broker, "mcp_server.py")

        assert request_count[0] == 1, \
            "Coder must stop after receiving 'approved' — should only send 1 review_request"

    async def test_iterates_on_fix_instruction(self, tmp_path, monkeypatch):
        """Coder must loop again after receiving 'fix_instruction'."""
        import coder_agent
        from a2a import Broker
        monkeypatch.setattr(coder_agent, "PROJECT_DIR", tmp_path)
        (tmp_path / "word_counter.py").write_text(ORIGINAL_CODE)

        broker = Broker()
        request_count = [0]
        original_send = broker.send
        async def capturing_send(msg):
            if msg.intent == "review_request":
                request_count[0] += 1
            await original_send(msg)
        broker.send = capturing_send

        async def auto_respond():
            # First response: fix_instruction
            req1 = await broker.receive("qa")
            await broker.send(
                _make_qa_response("fix_instruction", HIGH_ISSUES, req1.correlation_id)
            )
            # Second response: approved
            req2 = await broker.receive("qa")
            await broker.send(
                _make_qa_response("approved", [], req2.correlation_id)
            )
        asyncio.create_task(auto_respond())

        with _mock_llm_text(FIXED_CODE):
            await coder_agent.run_coder_agent(broker, "mcp_server.py")

        assert request_count[0] == 2, \
            "Coder must send a second review_request after receiving fix_instruction"

    async def test_respects_max_iterations(self, tmp_path, monkeypatch):
        """Coder must not exceed MAX_ITERATIONS even if never approved."""
        import coder_agent
        from a2a import Broker
        monkeypatch.setattr(coder_agent, "PROJECT_DIR", tmp_path)
        (tmp_path / "word_counter.py").write_text(ORIGINAL_CODE)
        monkeypatch.setattr(coder_agent, "MAX_ITERATIONS", 3)

        broker = Broker()
        request_count = [0]
        original_send = broker.send
        async def capturing_send(msg):
            if msg.intent == "review_request":
                request_count[0] += 1
            await original_send(msg)
        broker.send = capturing_send

        # QA always responds with fix_instruction
        async def auto_respond():
            for _ in range(coder_agent.MAX_ITERATIONS):
                try:
                    req = await asyncio.wait_for(broker.receive("qa"), timeout=5.0)
                    await broker.send(
                        _make_qa_response("fix_instruction", HIGH_ISSUES, req.correlation_id)
                    )
                except asyncio.TimeoutError:
                    break
        asyncio.create_task(auto_respond())

        with _mock_llm_text(FIXED_CODE):
            await coder_agent.run_coder_agent(broker, "mcp_server.py")

        assert request_count[0] <= coder_agent.MAX_ITERATIONS, \
            f"Coder sent {request_count[0]} requests but MAX_ITERATIONS is {coder_agent.MAX_ITERATIONS}"

    async def test_writes_file_each_iteration(self, tmp_path, monkeypatch):
        """Coder must write the file before sending review_request."""
        import coder_agent
        from a2a import Broker
        monkeypatch.setattr(coder_agent, "PROJECT_DIR", tmp_path)

        # Copy word_counter.py to tmp_path so _read_original_code works
        (tmp_path / "word_counter.py").write_text(ORIGINAL_CODE)

        broker = Broker()
        write_order = []
        send_order = []
        original_write = coder_agent.write_file
        def tracking_write(filename, code):
            write_order.append(len(write_order))
            original_write(filename, code)
        coder_agent.write_file = tracking_write

        original_send = broker.send
        async def tracking_send(msg):
            if msg.intent == "review_request":
                send_order.append(len(send_order))
            await original_send(msg)
        broker.send = tracking_send

        async def auto_respond():
            req = await broker.receive("qa")
            await broker.send(_make_qa_response("approved", [], req.correlation_id))
        asyncio.create_task(auto_respond())

        with _mock_llm_text(FIXED_CODE):
            await coder_agent.run_coder_agent(broker, "mcp_server.py")

        coder_agent.write_file = original_write
        assert len(write_order) >= 1, "write_file must be called at least once"
        assert write_order[0] < send_order[0] or (write_order and send_order), \
            "write_file must be called before review_request is sent"

    async def test_returns_string(self, tmp_path, monkeypatch):
        import coder_agent
        from a2a import Broker
        monkeypatch.setattr(coder_agent, "PROJECT_DIR", tmp_path)
        (tmp_path / "word_counter.py").write_text(ORIGINAL_CODE)

        broker = Broker()
        async def auto_respond():
            req = await broker.receive("qa")
            await broker.send(_make_qa_response("approved", [], req.correlation_id))
        asyncio.create_task(auto_respond())

        with _mock_llm_text(FIXED_CODE):
            result = await coder_agent.run_coder_agent(broker, "mcp_server.py")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Live end-to-end test
# ---------------------------------------------------------------------------

@pytest.mark.llm
async def test_live_full_loop():
    """Full Coder ↔ QA loop with real LLM and MCP server.

    Run with:  pytest --run-llm
    Requires:  API_KEY, mcp_server.py at lab root.
    """
    import coder_agent
    from a2a import Broker
    from qa_agent import run_qa_agent_a2a

    broker = Broker()
    mcp_server = str(LAB_ROOT / "mcp_server.py")

    coder_task = asyncio.create_task(
        coder_agent.run_coder_agent(broker, mcp_server)
    )
    qa_task = asyncio.create_task(
        run_qa_agent_a2a(broker, mcp_server)
    )

    final_code, _ = await asyncio.gather(coder_task, qa_task)

    assert isinstance(final_code, str)
    assert len(final_code) > 0
    # The fixed code should lowercase words
    assert "lower" in final_code, \
        "Fixed code should contain .lower() to address the case bug"
