# 文件说明：本文件属于 集成测试层。
# 主要职责：覆盖 feishu internal endpoint 相关行为。
# 阅读提示：验证 Gateway 与通道端到端链路。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Integration tests for the Feishu internal event endpoint."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import pytest


class FakeRuntime:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def handle_feishu_sidecar_event(
        self, account_id: str, event_data: dict[str, Any]
    ) -> bool:
        self.calls.append((account_id, event_data))
        return True


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestFeishuInternalEndpoint:
    @pytest.mark.asyncio
    async def test_rejects_bad_signature(self, app, client, monkeypatch) -> None:
        monkeypatch.setenv("OPENCLAW_FEISHU_INTERNAL_SECRET", "test-secret")
        app.state.gateway_runtime = FakeRuntime()
        body = b'{"accountId":"default"}'

        resp = await client.post(
            "/internal/channels/feishu/events",
            content=body,
            headers={"x-openclaw-signature": "bad"},
        )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_accepts_signed_event(self, app, client, monkeypatch) -> None:
        secret = "test-secret"
        monkeypatch.setenv("OPENCLAW_FEISHU_INTERNAL_SECRET", secret)
        runtime = FakeRuntime()
        app.state.gateway_runtime = runtime
        payload = {
            "accountId": "default",
            "eventType": "im.message.receive_v1",
            "event": {"message": {"message_id": "om_1"}},
        }
        body = json.dumps(payload).encode()

        resp = await client.post(
            "/internal/channels/feishu/events",
            content=body,
            headers={"x-openclaw-signature": f"sha256={_sign(secret, body)}"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "handled": True}
        assert runtime.calls == [("default", payload)]
