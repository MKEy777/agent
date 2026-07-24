# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 web fetch tool 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Contract tests for web_fetch."""

from __future__ import annotations

from typing import Any

import pytest
from openclaw.tools.builtin.web_fetch import create_web_fetch_tool, extract_text


@pytest.mark.asyncio
async def test_web_fetch_extracts_readable_html_and_links(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://example.com/report",
        headers={"content-type": "text/html; charset=utf-8"},
        html="""
        <html>
          <head>
            <title>Research Report</title>
            <meta name="description" content="A source-backed report.">
            <style>.hidden { display: none; }</style>
            <script>window.bad = true</script>
          </head>
          <body>
            <h1>DeepSeek V4</h1>
            <p>Primary source details.</p>
            <a href="/paper">Paper link</a>
          </body>
        </html>
        """,
    )

    tool = create_web_fetch_tool()
    assert tool.handler is not None
    result = await tool.handler(
        {"url": "https://example.com/report", "extract_links": True},
        None,
    )

    assert result["ok"] is True
    assert result["status"] == 200
    assert result["title"] == "Research Report"
    assert result["description"] == "A source-backed report."
    assert "DeepSeek V4" in result["text"]
    assert "window.bad" not in result["text"]
    assert result["links"] == [{"text": "Paper link", "url": "https://example.com/paper"}]


@pytest.mark.asyncio
async def test_web_fetch_rejects_local_urls() -> None:
    tool = create_web_fetch_tool()
    assert tool.handler is not None
    result = await tool.handler({"url": "http://127.0.0.1:8080/private"}, None)

    assert result["ok"] is False
    assert "private" in result["error"] or "loopback" in result["error"]


def test_web_fetch_tool_exposes_research_prompt_instruction() -> None:
    tool = create_web_fetch_tool()

    assert "after web_search" in tool.prompt_instructions
    assert "official, primary, paper" in tool.prompt_instructions
    assert "Do not invent citations" in tool.prompt_instructions


def test_extract_text_keeps_backward_compatible_content() -> None:
    text = extract_text("<h1>Title</h1><p>Hello <b>world</b></p>")

    assert "Title" in text
    assert "Hello world" in text
    assert "<h1>" not in text
