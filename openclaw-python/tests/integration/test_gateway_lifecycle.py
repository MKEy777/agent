# 文件说明：本文件属于 集成测试层。
# 主要职责：覆盖 gateway lifecycle 相关行为。
# 阅读提示：验证 Gateway 与通道端到端链路。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Integration tests for Gateway MVP."""

import pytest


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestConfigEndpoint:
    @pytest.mark.asyncio
    async def test_get_config(self, client) -> None:
        resp = await client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "config" in data

    @pytest.mark.asyncio
    async def test_patch_config(self, client) -> None:
        resp = await client.patch("/api/config", json={"key": "value"})
        assert resp.status_code == 200
