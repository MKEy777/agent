# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 web search tool 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Contract tests for web_search."""

from __future__ import annotations

import json
from typing import Any

import pytest
from openclaw.tools.builtin.web_search import BOCHA_WEB_SEARCH_URL, create_web_search_tool


@pytest.mark.asyncio
async def test_web_search_uses_bocha_when_key_is_configured(
    httpx_mock: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOCHA_API_KEY", "bocha-test-key")
    httpx_mock.add_response(
        method="POST",
        url=BOCHA_WEB_SEARCH_URL,
        json={
            "code": 0,
            "data": {
                "webPages": {
                    "value": [
                        {
                            "name": "OpenClaw Search",
                            "url": "https://example.com/openclaw",
                            "snippet": "A search result.",
                            "summary": "A summarized search result.",
                            "siteName": "Example",
                            "datePublished": "2026-04-26",
                        }
                    ]
                }
            },
        },
    )

    tool = create_web_search_tool()
    assert tool.handler is not None
    result = await tool.handler({"query": "OpenClaw", "count": 3, "freshness": "oneWeek"}, None)

    assert result["provider"] == "bocha"
    assert result["results"][0]["title"] == "OpenClaw Search"
    assert result["results"][0]["site_name"] == "Example"

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers["authorization"] == "Bearer bocha-test-key"
    payload = json.loads(request.content.decode())
    assert payload["query"] == "OpenClaw"
    assert payload["count"] == 3
    assert payload["freshness"] == "oneWeek"
    assert payload["summary"] is True


def test_web_search_tool_exposes_research_prompt_instruction() -> None:
    tool = create_web_search_tool()

    assert "deep exploration" in tool.prompt_instructions
    assert "current or changing information" in tool.prompt_instructions
    assert "never invent citations" in tool.prompt_instructions
