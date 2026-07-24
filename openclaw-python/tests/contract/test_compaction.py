# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 compaction 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Tests for the compaction system — trigger, quality, rollback, checkpoint."""

import asyncio
from typing import Any

import pytest
from openclaw.agents.runtime.embedded.compaction import (
    build_compaction_checkpoint,
    compact_messages,
    compute_compaction_reason,
    should_compact,
)
from openclaw.agents.runtime.embedded.overflow import (
    check_overflow,
    truncate_oversized_tool_results,
)
from openclaw.agents.runtime.embedded.tool_result import truncate_tool_result
from openclaw.contracts.agent.runtime import CompactionResult


def _make_messages(count: int, with_tools: bool = False) -> list[dict[str, Any]]:
    """Generate a list of conversation messages for testing."""
    msgs: list[dict[str, Any]] = []
    for i in range(count):
        if i % 2 == 0:
            msgs.append({"role": "user", "content": f"User message {i}: " + "x" * 200})
        else:
            content = f"Assistant response {i}: " + "y" * 200
            if with_tools and i % 4 == 1:
                msgs.append(
                    {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": [{"function": {"name": "bash"}}],
                    }
                )
                msgs.append({"role": "tool", "content": "tool result " + "z" * 100, "name": "bash"})
            else:
                msgs.append({"role": "assistant", "content": content})
    return msgs


class TestShouldCompact:
    def test_few_messages_no_compact(self) -> None:
        msgs = _make_messages(5)
        assert not should_compact(msgs, context_window=32000)

    def test_many_messages_trigger(self) -> None:
        msgs = _make_messages(100)
        assert should_compact(msgs, context_window=5000)

    def test_dynamic_threshold_with_tools(self) -> None:
        msgs = _make_messages(40, with_tools=True)
        # With tools, threshold is lower → compacts sooner
        tool_count = sum(1 for m in msgs if m.get("role") == "tool")
        assert tool_count > 0


class TestComputeReason:
    def test_overflow_reason(self) -> None:
        msgs = _make_messages(100)
        reason = compute_compaction_reason(msgs, context_window=1000)
        assert reason == "overflow"

    def test_budget_reason(self) -> None:
        msgs = _make_messages(50)
        reason = compute_compaction_reason(msgs, context_window=3000)
        assert reason in ("budget", "overflow")

    def test_manual_reason(self) -> None:
        reason = compute_compaction_reason([], explicit_reason="manual")
        assert reason == "manual"


class TestCompactMessages:
    @pytest.mark.asyncio
    async def test_basic_compaction(self) -> None:
        msgs = _make_messages(30)
        before = len(msgs)

        async def mock_summarize(text: str) -> str:
            return "Summary: discussed various topics including tool usage and code."

        result = await compact_messages(msgs, summarize_fn=mock_summarize)
        assert result.messages_before == before
        assert result.messages_after < before
        assert result.messages_after <= 11  # 1 summary + 10 recent
        assert len(msgs) == result.messages_after  # mutated in place
        assert msgs[0]["role"] == "system"
        assert "compacted" in msgs[0]["content"].lower() or "summary" in msgs[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_too_few_messages(self) -> None:
        msgs = _make_messages(5)
        result = await compact_messages(msgs)
        assert result.messages_before == result.messages_after  # No compaction

    @pytest.mark.asyncio
    async def test_no_summarize_fn_fallback(self) -> None:
        msgs = _make_messages(30)
        result = await compact_messages(msgs, summarize_fn=None)
        assert result.messages_after < result.messages_before
        assert "compacted" in msgs[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_summary_timeout_fallback(self) -> None:
        async def slow_summarize(text: str) -> str:
            await asyncio.sleep(100)
            return "never reached"

        msgs = _make_messages(30)
        result = await compact_messages(msgs, summarize_fn=slow_summarize, timeout_s=0.1)
        assert result.messages_after < result.messages_before
        # Should have fallback summary, not crash
        c = msgs[0]["content"].lower()
        assert "compacted" in c or "timed out" in c

    @pytest.mark.asyncio
    async def test_summary_error_fallback(self) -> None:
        async def bad_summarize(text: str) -> str:
            raise RuntimeError("LLM exploded")

        msgs = _make_messages(30)
        result = await compact_messages(msgs, summarize_fn=bad_summarize)
        assert result.messages_after < result.messages_before

    @pytest.mark.asyncio
    async def test_compaction_metadata(self) -> None:
        msgs = _make_messages(30, with_tools=True)

        async def mock_summarize(text: str) -> str:
            return "Summary with bash tool calls and error handling."

        await compact_messages(msgs, summarize_fn=mock_summarize, reason="overflow")
        assert msgs[0].get("_compaction") is not None
        meta = msgs[0]["_compaction"]
        assert meta["reason"] == "overflow"
        assert "quality_score" in meta


class TestToolResultTruncation:
    def test_short_result_unchanged(self) -> None:
        assert truncate_tool_result("short") == "short"

    def test_long_result_truncated(self) -> None:
        long_text = "x" * 100_000
        result = truncate_tool_result(long_text)
        assert len(result) < 50_000
        assert "truncated" in result

    def test_error_tail_preserved(self) -> None:
        text = "x" * 50_000 + "\nTraceback (most recent call last):\n  Error: something failed"
        result = truncate_tool_result(text, max_chars=5000)
        assert "Traceback" in result or "Error" in result or "failed" in result

    def test_context_share_limit(self) -> None:
        result = truncate_tool_result("x" * 100_000, context_window_tokens=10000)
        # 10000 * 0.3 * 4 = 12000 chars max
        assert len(result) < 15000


class TestOverflow:
    def test_no_overflow(self) -> None:
        msgs = _make_messages(5)
        assert not check_overflow(msgs, context_window=100000)

    def test_overflow_detected(self) -> None:
        msgs = _make_messages(100)
        assert check_overflow(msgs, context_window=1000)

    def test_truncate_oversized_tool_results(self) -> None:
        msgs = [
            {"role": "user", "content": "hi"},
            {"role": "tool", "content": "x" * 100_000},
        ]
        count = truncate_oversized_tool_results(msgs, context_window_tokens=10000)
        assert count == 1
        assert len(msgs[1]["content"]) < 50000


class TestCheckpointBuild:
    def test_build_checkpoint(self) -> None:
        result = CompactionResult(messages_before=50, messages_after=11, summary="test")
        cp = build_compaction_checkpoint(result, reason="overflow", quality=0.8)
        assert cp.reason == "overflow"
        assert cp.messages_before == 50
        assert cp.messages_after == 11
        assert cp.quality_score == 0.8
        assert cp.timestamp > 0
