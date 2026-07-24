# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 dashscope provider 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""DashScope provider tool-calling contract tests."""

from __future__ import annotations

import json
from typing import Any

import pytest
from openclaw.extensions.dashscope.provider import DASHSCOPE_BASE_URL, DashScopeProvider


# revision: 0fB66 0eId9
@pytest.mark.asyncio
async def test_dashscope_stream_emits_tool_calls(httpx_mock: Any) -> None:
    first_chunk = {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_1",
                            "function": {
                                "name": "feishu_docs_create_with_content",
                                "arguments": '{"title":"GRPO"',
                            },
                        }
                    ]
                },
                "finish_reason": None,
            }
        ],
        "usage": None,
    }
    second_chunk = {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "function": {"arguments": ',"content":"正文"}'},
                        }
                    ]
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2},
    }
    httpx_mock.add_response(
        method="POST",
        url=f"{DASHSCOPE_BASE_URL}/chat/completions",
        headers={"content-type": "text/event-stream"},
        text=(
            f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n"
            f"data: {json.dumps(second_chunk, ensure_ascii=False)}\n\n"
            "data: [DONE]\n\n"
        ),
    )
    provider = DashScopeProvider("test-key")
    tools = [
        {
            "name": "feishu_docs_create_with_content",
            "description": "Create a document",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
        }
    ]

    chunks = [
        chunk
        async for chunk in provider.create_stream(
            model="qwen3.6-max-preview",
            messages=[{"role": "user", "content": "创建文档"}],
            tools=tools,
        )
    ]

    assert chunks[0] == {
        "type": "tool_call",
        "id": "call_1",
        "name": "feishu_docs_create_with_content",
        "params": {"title": "GRPO", "content": "正文"},
    }
    assert chunks[1] == {"type": "usage", "input_tokens": 1, "output_tokens": 2}

    request = httpx_mock.get_request()
    assert request is not None
    body = json.loads(request.content)
    assert body["tools"][0]["function"]["name"] == "feishu_docs_create_with_content"
