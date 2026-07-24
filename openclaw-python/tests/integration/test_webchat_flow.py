# 文件说明：本文件属于 集成测试层。
# 主要职责：覆盖 webchat flow 相关行为。
# 阅读提示：验证 Gateway 与通道端到端链路。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Integration test: WebChat uses Gateway EventFrame push, not channel.send()."""

from openclaw.channels.webchat.plugin import WebChatPlugin
from openclaw.contracts.channel.plugin import OutboundMessage


class TestWebChatDesign:
    """Verify WebChat is a Gateway WS push channel, not an independent adapter."""

    def test_webchat_send_is_noop(self) -> None:
        """WebChat.send() is intentionally empty — delivery via Gateway EventFrame."""
        plugin = WebChatPlugin()
        # send() should not raise, and should not do anything
        import asyncio

        msg = OutboundMessage(text="test")
        asyncio.get_event_loop().run_until_complete(plugin.send("default", "conv-1", msg))
        # If we get here without error, the no-op behavior is correct

    def test_webchat_start_stop_are_noop(self) -> None:
        """WebChat start/stop are no-ops — no persistent connection to manage."""
        plugin = WebChatPlugin()
        import asyncio

        asyncio.get_event_loop().run_until_complete(plugin.start("default", {}))
        asyncio.get_event_loop().run_until_complete(plugin.stop("default"))

    def test_webchat_meta(self) -> None:
        plugin = WebChatPlugin()
        assert plugin.id == "webchat"
        assert plugin.capabilities.chat_types == ["dm"]

    def test_webchat_accounts(self) -> None:
        plugin = WebChatPlugin()
        assert plugin.list_account_ids({}) == ["default"]
