# 文件说明：本文件属于 集成测试层。
# 主要职责：提供测试共享 fixture。
# 阅读提示：验证 Gateway 与通道端到端链路。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Shared test fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient
from openclaw.gateway.app import create_app


@pytest.fixture
def app():
    return create_app(boot=False)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
