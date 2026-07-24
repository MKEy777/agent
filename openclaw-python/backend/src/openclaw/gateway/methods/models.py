# 文件说明：本文件属于 Gateway 服务层。
# 主要职责：处理模型相关接口。
# 阅读提示：承载 API、WebSocket 和运行事件。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Gateway models.* method handlers."""

from typing import Any

from openclaw.gateway.state import GatewayRuntimeState
from openclaw.gateway.websocket.connection import GatewayWsClient


# revision: 09Vb5 08355
async def handle_models_list(
    params: dict[str, Any], client: GatewayWsClient, state: GatewayRuntimeState
) -> dict[str, Any]:
    runtime = getattr(state, "_gateway_runtime_ref", None)
    if runtime is None:
        return {"models": []}
    return {"models": runtime.provider_registry.all_models()}
