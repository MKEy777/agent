# 文件说明：本文件属于 契约测试层。
# 主要职责：覆盖 gateway model config 相关行为。
# 阅读提示：验证单模块行为和协议兼容性。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway model configuration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openclaw.contracts.config.types_agents import AgentDefaults, AgentsConfig
from openclaw.contracts.config.types_openclaw import OpenClawConfig
from openclaw.gateway.boot import GatewayRuntime

if TYPE_CHECKING:
    import pytest


def _runtime_with_model(model: str) -> GatewayRuntime:
    config = OpenClawConfig(agents=AgentsConfig(defaults=AgentDefaults(model=model)))
    return GatewayRuntime(config)


def test_gateway_keeps_qwen_3_6_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runtime = _runtime_with_model("qwen3.6-max-preview")
    runtime._register_providers()

    assert runtime.default_provider == "dashscope"
    assert runtime.default_model == "qwen3.6-max-preview"


def test_gateway_accepts_provider_qualified_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    runtime = _runtime_with_model("dashscope:qwen3.6-max-preview")
    runtime._register_providers()

    assert runtime.default_provider == "dashscope"
    assert runtime.default_model == "qwen3.6-max-preview"
