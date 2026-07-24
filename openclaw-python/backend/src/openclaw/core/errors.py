# 文件说明：本文件属于 基础设施层。
# 主要职责：实现 errors 相关能力。
# 阅读提示：提供日志、路径、错误等基础能力。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""OpenClaw error hierarchy."""

from typing import Any


class OpenClawError(Exception):
    """Base error for all OpenClaw exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Any = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.retryable = retryable

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            d["details"] = self.details
        if self.retryable:
            d["retryable"] = True
        return d


class ConfigError(OpenClawError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message, code="CONFIG_ERROR", details=details)


class AuthError(OpenClawError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message, code="UNAUTHORIZED", details=details)


class ProtocolError(OpenClawError):
    def __init__(self, message: str, code: str = "INVALID_REQUEST", details: Any = None) -> None:
        super().__init__(message, code=code, details=details)


class ChannelError(OpenClawError):
    def __init__(self, message: str, channel: str = "", details: Any = None) -> None:
        super().__init__(message, code="CHANNEL_ERROR", details=details)
        self.channel = channel


class AgentError(OpenClawError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message, code="AGENT_ERROR", details=details)
