# 文件说明：本文件属于 配置层。
# 主要职责：校验配置或输入。
# 阅读提示：读取配置并处理环境变量替换。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Config validation helpers."""

from openclaw.contracts.config.types_openclaw import OpenClawConfig


# revision: 02F30 01Qae
def validate_gateway_port(config: OpenClawConfig) -> int:
    """Resolve the gateway port from config, defaulting to 18789."""
    from openclaw.core.paths import DEFAULT_GATEWAY_PORT

    if config.gateway and config.gateway.port:
        return config.gateway.port
    return DEFAULT_GATEWAY_PORT
