# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 feishu channel 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Feishu channel contract tests."""

from __future__ import annotations

from typing import Any

import pytest
from openclaw.channels.feishu.auth import FeishuAuth
from openclaw.channels.feishu.events import (
    FEISHU_WS_ENDPOINT_URL,
    FRAME_TYPE_DATA,
    HEADER_MESSAGE_ID,
    HEADER_SEQ,
    HEADER_SUM,
    HEADER_TRACE_ID,
    HEADER_TYPE,
    MESSAGE_TYPE_EVENT,
    FeishuEventSubscriber,
    _decode_frame,
    _encode_frame,
)
from openclaw.channels.feishu.message import parse_inbound
from openclaw.channels.feishu.plugin import FeishuChannelPlugin


def test_parse_sidecar_text_event() -> None:
    msg = parse_inbound(
        {
            "accountId": "default",
            "eventType": "im.message.receive_v1",
            "event": {
                "sender": {"sender_id": {"open_id": "ou_user"}},
                "message": {
                    "message_id": "om_1",
                    "chat_id": "oc_chat",
                    "chat_type": "p2p",
                    "message_type": "text",
                    "content": '{"text":"hello"}',
                },
            },
        }
    )

    assert msg is not None
    assert msg.sender_id == "ou_user"
    assert msg.conversation_id == "oc_chat"
    assert msg.chat_type == "dm"
    assert msg.text == "hello"
    assert msg.raw is not None
    assert msg.raw["message_id"] == "om_1"


def test_feishu_accounts_can_use_environment(monkeypatch) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret")

    plugin = FeishuChannelPlugin()

    assert plugin.list_account_ids({}) == ["default"]


@pytest.mark.asyncio
async def test_group_message_requires_mention_by_default() -> None:
    seen = []

    async def on_inbound(msg: object) -> None:
        seen.append(msg)

    plugin = FeishuChannelPlugin(on_inbound=on_inbound)
    plugin._configs["default"] = {"groupPolicy": "mention"}  # noqa: SLF001

    handled = await plugin.handle_event(
        "default",
        {
            "eventType": "im.message.receive_v1",
            "event": {
                "sender": {"sender_id": {"open_id": "ou_user"}},
                "message": {
                    "message_id": "om_1",
                    "chat_id": "oc_chat",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": '{"text":"hello group"}',
                },
            },
        },
    )

    assert handled is False
    assert seen == []


@pytest.mark.asyncio
async def test_group_message_with_mention_is_handled() -> None:
    seen = []

    async def on_inbound(msg: object) -> None:
        seen.append(msg)

    plugin = FeishuChannelPlugin(on_inbound=on_inbound)
    plugin._configs["default"] = {"groupPolicy": "mention"}  # noqa: SLF001

    handled = await plugin.handle_event(
        "default",
        {
            "eventType": "im.message.receive_v1",
            "event": {
                "sender": {"sender_id": {"open_id": "ou_user"}},
                "message": {
                    "message_id": "om_1",
                    "chat_id": "oc_chat",
                    "chat_type": "group",
                    "message_type": "text",
                    "content": '{"text":"<at user_id=\\"bot\\">Bot</at> hello"}',
                },
            },
        },
    )

    assert handled is True
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_duplicate_message_id_is_ignored() -> None:
    seen = []

    async def on_inbound(msg: object) -> None:
        seen.append(msg)

    plugin = FeishuChannelPlugin(on_inbound=on_inbound)
    plugin._configs["default"] = {"groupPolicy": "mention"}  # noqa: SLF001
    event = {
        "eventType": "im.message.receive_v1",
        "event": {
            "sender": {"sender_id": {"open_id": "ou_user"}},
            "message": {
                "message_id": "om_duplicate",
                "chat_id": "oc_chat",
                "chat_type": "p2p",
                "message_type": "text",
                "content": '{"text":"hello"}',
            },
        },
    }

    assert await plugin.handle_event("default", event) is True
    assert await plugin.handle_event("default", event) is False
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_feishu_ws_config_uses_callback_endpoint(httpx_mock: Any) -> None:
    httpx_mock.add_response(
        method="POST",
        url=FEISHU_WS_ENDPOINT_URL,
        json={
            "code": 0,
            "msg": "",
            "data": {
                "URL": "wss://example.invalid/ws?device_id=d1&service_id=100",
                "ClientConfig": {"PingInterval": 120},
            },
        },
    )
    subscriber = FeishuEventSubscriber(FeishuAuth("cli_test", "secret"), lambda _: None)

    ws_url, client_config = await subscriber._get_ws_config()  # noqa: SLF001

    assert ws_url.startswith("wss://example.invalid/")
    assert client_config["PingInterval"] == 120


@pytest.mark.asyncio
async def test_feishu_ws_binary_event_frame_is_dispatched() -> None:
    seen: list[dict[str, Any]] = []

    async def on_message(payload: dict[str, Any]) -> None:
        seen.append(payload)

    class FakeWs:
        def __init__(self) -> None:
            self.sent: list[bytes] = []

        async def send(self, payload: bytes) -> None:
            self.sent.append(payload)

    subscriber = FeishuEventSubscriber(FeishuAuth("cli_test", "secret"), on_message)
    ws = FakeWs()
    payload = {
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "sender": {"sender_id": {"open_id": "ou_user"}},
            "message": {
                "message_id": "om_1",
                "chat_id": "oc_chat",
                "chat_type": "p2p",
                "message_type": "text",
                "content": '{"text":"hello"}',
            },
        },
    }
    frame = {
        "SeqID": 1,
        "LogID": 1,
        "service": 100,
        "method": FRAME_TYPE_DATA,
        "headers": [
            {"key": HEADER_TYPE, "value": MESSAGE_TYPE_EVENT},
            {"key": HEADER_MESSAGE_ID, "value": "msg_1"},
            {"key": HEADER_SUM, "value": "1"},
            {"key": HEADER_SEQ, "value": "0"},
            {"key": HEADER_TRACE_ID, "value": "trace_1"},
        ],
        "payload": __import__("json").dumps(payload).encode(),
    }

    await subscriber._handle_frame(_decode_frame(_encode_frame(frame)), ws)  # noqa: SLF001

    assert seen == [payload]
    assert len(ws.sent) == 1
    ack = _decode_frame(ws.sent[0])
    assert ack["method"] == FRAME_TYPE_DATA
