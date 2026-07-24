# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 feishu docs tools 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Contract tests for Feishu cloud docs tools."""

from __future__ import annotations

from typing import Any

import pytest
from openclaw.channels.feishu.auth import FEISHU_TOKEN_URL
from openclaw.channels.feishu.docs import (
    FEISHU_OPENAPI_BASE,
    FeishuDocsClient,
    is_mutation_request,
    normalize_feishu_docs_path,
)
from openclaw.tools.builtin.feishu_docs import (
    _extract_docx_id,
    _has_explicit_doc_write_intent,
    _markdown_to_docx_blocks,
    create_feishu_docs_create_with_content_tool,
    create_feishu_docs_raw_content_tool,
    create_feishu_docs_search_tool,
)
from openclaw.tools.policy import ToolPolicy
from openclaw.tools.types import ToolContext


class TestFeishuDocsClient:
    def test_normalizes_relative_and_full_paths(self) -> None:
        assert normalize_feishu_docs_path("docx/v1/documents/doc_1/raw_content") == (
            "/open-apis/docx/v1/documents/doc_1/raw_content",
            {},
        )
        assert normalize_feishu_docs_path(
            "https://open.feishu.cn/open-apis/drive/v1/files?page_size=10"
        ) == (
            "/open-apis/drive/v1/files",
            {"page_size": "10"},
        )

    def test_marks_mutation_requests(self) -> None:
        assert not is_mutation_request("GET", "/open-apis/docx/v1/documents/doc_1")
        assert not is_mutation_request("POST", "/open-apis/suite/docs-api/search/object")
        assert is_mutation_request("POST", "/open-apis/docx/v1/documents")

    @pytest.mark.asyncio
    async def test_write_requests_require_explicit_enable(self) -> None:
        client = FeishuDocsClient("cli_test", "secret")

        with pytest.raises(RuntimeError):
            await client.request("POST", "/docx/v1/documents", body={"title": "blocked"})

    @pytest.mark.asyncio
    async def test_rejects_non_docs_openapi_path(self) -> None:
        client = FeishuDocsClient("cli_test", "secret")

        with pytest.raises(ValueError):
            await client.request("GET", "/im/v1/messages")


class TestFeishuDocsTools:
    def test_extracts_docx_id_from_url(self) -> None:
        assert _extract_docx_id("https://example.feishu.cn/docx/ABC123?from=from_copylink") == (
            "ABC123"
        )

    @pytest.mark.asyncio
    async def test_raw_content_tool_calls_docx_api(
        self,
        httpx_mock: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
        monkeypatch.setenv("FEISHU_APP_SECRET", "secret")
        httpx_mock.add_response(
            method="POST",
            url=FEISHU_TOKEN_URL,
            json={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
        )
        httpx_mock.add_response(
            method="GET",
            url=f"{FEISHU_OPENAPI_BASE}/docx/v1/documents/doc_1/raw_content",
            json={"code": 0, "data": {"content": "hello"}},
        )

        tool = create_feishu_docs_raw_content_tool()
        assert tool.handler is not None
        result = await tool.handler({"document_id": "doc_1"}, None)

        assert result["status"] == 200
        assert result["json"]["data"]["content"] == "hello"

    @pytest.mark.asyncio
    async def test_search_tool_uses_readonly_post(
        self,
        httpx_mock: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
        monkeypatch.setenv("FEISHU_APP_SECRET", "secret")
        monkeypatch.delenv("OPENCLAW_FEISHU_DOCS_WRITE_ENABLED", raising=False)
        httpx_mock.add_response(
            method="POST",
            url=FEISHU_TOKEN_URL,
            json={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
        )
        httpx_mock.add_response(
            method="POST",
            url=f"{FEISHU_OPENAPI_BASE}/suite/docs-api/search/object",
            json={"code": 0, "data": {"docs_entities": []}},
        )

        tool = create_feishu_docs_search_tool()
        assert tool.handler is not None
        result = await tool.handler({"search_key": "项目", "count": 5}, None)

        assert result["status"] == 200
        assert result["json"]["code"] == 0

    def test_markdown_to_docx_blocks(self) -> None:
        blocks = _markdown_to_docx_blocks("# 标题\n\n段落\n\n- 列表\n\n```python\nprint(1)\n```")

        assert [block["block_type"] for block in blocks] == [3, 2, 12, 14]
        assert blocks[0]["heading1"]["elements"][0]["text_run"]["content"] == "标题"

    def test_markdown_to_docx_blocks_renders_latex_as_equations(self) -> None:
        blocks = _markdown_to_docx_blocks(
            "策略损失 $L(\\theta)$ 如下：\n\n"
            "$$\n"
            "\\hat{r}(s,a) = r(s,a) + \\epsilon \\nabla_\\theta \\log \\pi(a|s;\\theta)\n"
            "$$"
        )

        assert [block["block_type"] for block in blocks] == [2, 2]
        assert blocks[0]["text"]["elements"][1]["equation"]["content"] == "L(\\theta)"
        assert blocks[1]["text"]["elements"][0]["equation"]["content"].startswith("\\hat{r}")

    def test_feishu_doc_write_intent_requires_current_explicit_request(self) -> None:
        assert _has_explicit_doc_write_intent("建一个飞书文档，标题为 GRPO 深入讲解")
        assert _has_explicit_doc_write_intent("可以帮我创建一个文档吗，深入讲解 GRPO")
        assert not _has_explicit_doc_write_intent("大模型强化学习算法 GRPO")
        assert not _has_explicit_doc_write_intent("1")

    @pytest.mark.asyncio
    async def test_create_with_content_tool_creates_doc_and_blocks(
        self,
        httpx_mock: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
        monkeypatch.setenv("FEISHU_APP_SECRET", "secret")
        monkeypatch.setenv("OPENCLAW_FEISHU_DOCS_WRITE_ENABLED", "true")
        httpx_mock.add_response(
            method="POST",
            url=FEISHU_TOKEN_URL,
            json={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
        )
        httpx_mock.add_response(
            method="POST",
            url=f"{FEISHU_OPENAPI_BASE}/docx/v1/documents",
            json={
                "code": 0,
                "data": {
                    "document": {
                        "document_id": "doc_1",
                        "url": "https://example.feishu.cn/docx/doc_1",
                    }
                },
            },
        )
        httpx_mock.add_response(
            method="POST",
            url=(
                f"{FEISHU_OPENAPI_BASE}/docx/v1/documents/doc_1/blocks/doc_1/children"
                "?document_revision_id=-1"
            ),
            json={"code": 0, "data": {"children": []}},
        )

        tool = create_feishu_docs_create_with_content_tool()
        assert tool.handler is not None
        result = await tool.handler({"title": "GRPO", "content": "# GRPO\n\n正文"}, None)

        assert result["document_id"] == "doc_1"
        assert result["blocks_created"] == 2
        assert result["url"] == "https://example.feishu.cn/docx/doc_1"
        assert result["reply_text"] == "已创建飞书文档：《GRPO》\n链接：https://example.feishu.cn/docx/doc_1"

    @pytest.mark.asyncio
    async def test_create_with_content_tool_adds_sender_as_collaborator(
        self,
        httpx_mock: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
        monkeypatch.setenv("FEISHU_APP_SECRET", "secret")
        monkeypatch.setenv("OPENCLAW_FEISHU_DOCS_WRITE_ENABLED", "true")
        httpx_mock.add_response(
            method="POST",
            url=FEISHU_TOKEN_URL,
            json={"code": 0, "tenant_access_token": "tenant-token", "expire": 7200},
        )
        httpx_mock.add_response(
            method="POST",
            url=f"{FEISHU_OPENAPI_BASE}/docx/v1/documents",
            json={"code": 0, "data": {"document": {"document_id": "doc_1"}}},
        )
        httpx_mock.add_response(
            method="POST",
            url=(
                f"{FEISHU_OPENAPI_BASE}/docx/v1/documents/doc_1/blocks/doc_1/children"
                "?document_revision_id=-1"
            ),
            json={"code": 0, "data": {"children": []}},
        )
        httpx_mock.add_response(
            method="POST",
            url=(
                f"{FEISHU_OPENAPI_BASE}/drive/v1/permissions/doc_1/members"
                "?type=docx&need_notification=false"
            ),
            json={"code": 0, "data": {"member": {"member_id": "ou_user"}}},
        )

        tool = create_feishu_docs_create_with_content_tool()
        assert tool.handler is not None
        result = await tool.handler(
            {"title": "GRPO", "content": "正文"},
            ToolContext(
                channel="feishu",
                sender_id="ou_user",
                user_message="创建一个飞书文档，标题是 GRPO",
            ),
        )

        assert result["collaborator_added"] is True
        assert result["link_status"] == "missing_tenant_domain"
        assert "文档 ID：doc_1" in result["reply_text"]

    @pytest.mark.asyncio
    async def test_create_with_content_rejects_implicit_feishu_doc_write(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
        monkeypatch.setenv("FEISHU_APP_SECRET", "secret")
        monkeypatch.setenv("OPENCLAW_FEISHU_DOCS_WRITE_ENABLED", "true")

        tool = create_feishu_docs_create_with_content_tool()
        assert tool.handler is not None
        with pytest.raises(RuntimeError, match="没有明确要求创建或写入文档"):
            await tool.handler(
                {"title": "GRPO", "content": "正文"},
                ToolContext(channel="feishu", user_message="1"),
            )

    def test_messaging_policy_allows_feishu_docs_tools(self) -> None:
        policy = ToolPolicy(profile="messaging")

        assert policy.is_allowed("feishu_docs_api")
        assert policy.is_allowed("feishu_docs_raw_content")
        assert policy.is_allowed("feishu_docs_create")
        assert policy.is_allowed("feishu_docs_create_with_content")
        assert policy.is_allowed("feishu_docs_search")
        assert policy.is_allowed("feishu_docs_list_folder")
        assert not policy.is_allowed("bash")

    def test_create_with_content_tool_rejects_placeholder_prompt_pattern(self) -> None:
        tool = create_feishu_docs_create_with_content_tool()

        assert "must not contain placeholders" in tool.prompt_instructions
        assert "URL_1" in tool.prompt_instructions
        content_description = tool.input_schema["properties"]["content"]["description"]
        assert "Complete Markdown" in content_description
        assert "待补充" in content_description
