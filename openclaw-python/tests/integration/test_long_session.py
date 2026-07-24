# 文件说明：本文件属于 集成测试层。
# 主要职责：覆盖 long session 相关行为。
# 阅读提示：验证 Gateway 与通道端到端链路。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""System-level long-session integration test.

Verifies the complete chain:
  long transcript write → overflow detection → auto compact → transcript rewrite
  → session continues running → checkpoint persisted
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest
from openclaw.agents.runtime.embedded.compaction import (
    CompactionCheckpoint,
    compact_messages,
    should_compact,
)
from openclaw.sessions.compaction import CompactionStore
from openclaw.sessions.store import SessionStore
from openclaw.sessions.transcript import TranscriptManager


def _build_long_transcript(
    transcript_mgr: TranscriptManager,
    session_id: str,
    num_turns: int = 40,
) -> list[dict[str, Any]]:
    """Write a long conversation transcript and return the messages."""
    messages: list[dict[str, Any]] = []
    for i in range(num_turns):
        user_msg = {
            "role": "user",
            "content": f"Question {i}: " + "x" * 300,
            "ts": 1000 + i,
        }
        assistant_msg = {
            "role": "assistant",
            "content": f"Answer {i}: " + "y" * 300,
            "ts": 2000 + i,
        }
        transcript_mgr.append(session_id, user_msg)
        transcript_mgr.append(session_id, assistant_msg)
        messages.extend([user_msg, assistant_msg])

        # Add some tool calls
        if i % 5 == 0:
            tool_msg = {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "bash", "arguments": '{"command": "ls"}'}}],
            }
            tool_result = {"role": "tool", "content": "file1.py\nfile2.py\n", "name": "bash"}
            transcript_mgr.append(session_id, tool_msg)
            transcript_mgr.append(session_id, tool_result)
            messages.extend([tool_msg, tool_result])

    return messages


class TestLongSessionFlow:
    """End-to-end: long transcript → detect overflow → compact → verify continuity."""

    def test_long_transcript_triggers_compaction(self) -> None:
        """Build a long transcript, verify should_compact triggers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            tm = TranscriptManager(state_dir)
            session_id = "test-long-session"

            messages = _build_long_transcript(tm, session_id, num_turns=40)
            assert len(messages) > 80  # At least 80 messages + tool calls

            # should_compact should trigger with a small context window
            assert should_compact(messages, context_window=5000)

    @pytest.mark.asyncio
    async def test_compact_and_continue(self) -> None:
        """Compact a long session, then verify it can continue (messages still valid)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            tm = TranscriptManager(state_dir)
            session_id = "test-compact-continue"

            messages = _build_long_transcript(tm, session_id, num_turns=30)
            before_count = len(messages)

            # Compact
            async def mock_summarize(text: str) -> str:
                return "Summary: discussed 30 turns about code, ran bash tool multiple times."

            result = await compact_messages(messages, summarize_fn=mock_summarize)
            assert result.messages_before == before_count
            assert result.messages_after < before_count
            assert result.messages_after <= 11  # 1 summary + 10 recent

            # Verify messages are still valid (can be used for next run)
            assert messages[0]["role"] == "system"
            assert "_compaction" in messages[0]
            for msg in messages[1:]:
                assert msg["role"] in ("user", "assistant", "tool")

            # Simulate continuing the session — append new messages
            messages.append({"role": "user", "content": "Continue: what was I working on?"})
            messages.append({"role": "assistant", "content": "Based on the summary, you were..."})
            assert len(messages) == result.messages_after + 2

    @pytest.mark.asyncio
    async def test_transcript_rewrite_roundtrip(self) -> None:
        """Compact, rewrite transcript, reload, verify data integrity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            tm = TranscriptManager(state_dir)
            session_id = "test-rewrite"

            # Write long transcript
            _build_long_transcript(tm, session_id, num_turns=25)
            original = tm.read_raw(session_id)
            assert len(original) > 50

            # Compact in memory
            messages = list(original)

            async def mock_summarize(text: str) -> str:
                return "Conversation about coding with bash tool usage."

            await compact_messages(messages, summarize_fn=mock_summarize)

            # Rewrite transcript
            tm.clear(session_id)
            for msg in messages:
                tm.append(session_id, msg)

            # Reload and verify
            reloaded = tm.read_raw(session_id)
            assert len(reloaded) == len(messages)
            assert reloaded[0]["role"] == "system"
            c = reloaded[0]["content"].lower()
            assert "compacted" in c or "summary" in c

    def test_checkpoint_persisted(self) -> None:
        """Verify CompactionStore persists and loads checkpoints correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            store = CompactionStore(state_dir)
            session_id = "test-checkpoint"

            # Initially empty
            assert store.count(session_id) == 0
            assert store.latest(session_id) is None

            # Add checkpoints
            cp1 = CompactionCheckpoint(
                version=1,
                timestamp=1000,
                reason="overflow",
                messages_before=50,
                messages_after=11,
                tokens_before=5000,
                tokens_after=1200,
                summary_length=300,
                quality_score=0.85,
            )
            store.append(session_id, cp1)
            assert store.count(session_id) == 1

            cp2 = CompactionCheckpoint(
                version=2,
                timestamp=2000,
                reason="budget",
                messages_before=30,
                messages_after=11,
                tokens_before=3000,
                tokens_after=1000,
                summary_length=200,
                quality_score=0.9,
            )
            store.append(session_id, cp2)
            assert store.count(session_id) == 2

            # Verify latest
            latest = store.latest(session_id)
            assert latest is not None
            assert latest.version == 2
            assert latest.reason == "budget"
            assert latest.quality_score == 0.9

            # Verify history
            all_cps = store.list_checkpoints(session_id)
            assert len(all_cps) == 2
            assert all_cps[0].version == 1
            assert all_cps[1].version == 2

    def test_session_store_compaction_count(self) -> None:
        """Verify session store tracks compaction count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir)
            ss = SessionStore(state_dir)
            ss.create("test", label="test session")

            entry = ss.get("test")
            assert entry is not None
            assert (entry.compaction_count or 0) == 0

            ss.update("test", {"compactionCount": 1})
            entry = ss.get("test")
            assert entry is not None
            assert entry.compaction_count == 1

            ss.update("test", {"compactionCount": 2})
            entry = ss.get("test")
            assert entry is not None
            assert entry.compaction_count == 2
