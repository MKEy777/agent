# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 protocol frames 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Contract tests for protocol frame models — round-trip JSON compatibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from openclaw.contracts.protocol.frames import (
    EventFrame,
    GatewayFrame,
    RequestFrame,
    ResponseFrame,
)
from openclaw.contracts.protocol.hello import ConnectParams, HelloOk
from openclaw.contracts.protocol.snapshot import Snapshot, StateVersion
from openclaw.contracts.protocol.version import PROTOCOL_VERSION

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "protocol_frames"


def load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text())


class TestProtocolVersion:
    def test_version_is_3(self) -> None:
        assert PROTOCOL_VERSION == 3


class TestRequestFrame:
    def test_parse_fixture(self) -> None:
        data = load_fixture("request.json")
        frame = RequestFrame.model_validate(data)
        assert frame.type == "req"
        assert frame.id == "conn-1"
        assert frame.method == "connect"
        assert frame.params is not None

    def test_round_trip(self) -> None:
        data = load_fixture("request.json")
        frame = RequestFrame.model_validate(data)
        dumped = json.loads(frame.model_dump_json(exclude_none=True))
        assert dumped["type"] == data["type"]
        assert dumped["id"] == data["id"]
        assert dumped["method"] == data["method"]

    def test_rejects_empty_id(self) -> None:
        with pytest.raises(ValueError):
            RequestFrame.model_validate({"type": "req", "id": "", "method": "test"})

    def test_rejects_empty_method(self) -> None:
        with pytest.raises(ValueError):
            RequestFrame.model_validate({"type": "req", "id": "1", "method": ""})


class TestResponseFrame:
    def test_parse_ok_response(self) -> None:
        data = load_fixture("response.json")
        frame = ResponseFrame.model_validate(data)
        assert frame.type == "res"
        assert frame.ok is True
        assert frame.payload is not None
        assert frame.error is None

    def test_parse_error_response(self) -> None:
        data = load_fixture("error_response.json")
        frame = ResponseFrame.model_validate(data)
        assert frame.ok is False
        assert frame.error is not None
        assert frame.error.code == "INVALID_REQUEST"


class TestEventFrame:
    def test_parse_tick(self) -> None:
        data = load_fixture("event.json")
        frame = EventFrame.model_validate(data)
        assert frame.type == "event"
        assert frame.event == "tick"
        assert frame.payload["ts"] == 1712000000000


class TestGatewayFrameDiscriminator:
    def test_parse_request(self) -> None:
        from pydantic import TypeAdapter

        adapter = TypeAdapter(GatewayFrame)
        data = load_fixture("request.json")
        frame = adapter.validate_python(data)
        assert isinstance(frame, RequestFrame)

    def test_parse_response(self) -> None:
        from pydantic import TypeAdapter

        adapter = TypeAdapter(GatewayFrame)
        data = load_fixture("response.json")
        frame = adapter.validate_python(data)
        assert isinstance(frame, ResponseFrame)

    def test_parse_event(self) -> None:
        from pydantic import TypeAdapter

        adapter = TypeAdapter(GatewayFrame)
        data = load_fixture("event.json")
        frame = adapter.validate_python(data)
        assert isinstance(frame, EventFrame)


class TestConnectParams:
    def test_parse_from_request_fixture(self) -> None:
        data = load_fixture("request.json")
        params = ConnectParams.model_validate(data["params"])
        assert params.min_protocol == 1
        assert params.max_protocol == 3
        assert params.client.id == "web-admin"
        assert params.client.platform == "darwin"


class TestHelloOk:
    def test_parse_from_response_fixture(self) -> None:
        data = load_fixture("response.json")
        hello = HelloOk.model_validate(data["payload"])
        assert hello.type == "hello-ok"
        assert hello.protocol == 3
        assert hello.server.version == "0.1.0"
        assert hello.server.conn_id == "abc-123"
        assert len(hello.features.methods) == 3
        assert hello.policy.tick_interval_ms == 30000

    def test_snapshot_in_hello(self) -> None:
        data = load_fixture("response.json")
        hello = HelloOk.model_validate(data["payload"])
        assert isinstance(hello.snapshot, Snapshot)
        assert hello.snapshot.uptime_ms == 0
        assert hello.snapshot.state_version.presence == 0


class TestStateVersion:
    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError):
            StateVersion.model_validate({"presence": -1, "health": 0})
