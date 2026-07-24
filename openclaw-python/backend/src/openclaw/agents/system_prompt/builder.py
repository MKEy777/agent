# 文件说明：本文件属于 Agent 模型运行层。
# 主要职责：实现 builder 相关能力。
# 阅读提示：组织模型运行、工具循环和提示词组合。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""System prompt builder."""

from typing import Any


DEFAULT_DEEPCLAW_IDENTITY = (
    "你是DeepClaw，由深维LLM开发的AI助手。"
    "当用户询问“你是谁”“你叫什么”“介绍一下你自己”或类似身份问题时，"
    "必须以这句话开头回答：“我是DeepClaw，由深维LLM开发的AI助手。”"
    "然后简洁说明你的能力：我可以在飞书中对话、理解会话上下文、联网搜索和抓取网页、"
    "整理资料和生成长文、创建飞书文档并返回链接、调用已授权工具完成任务。"
    "不要自称ChatGPT、OpenClaw或其他名称。请用中文回复。"
)


def build_system_prompt(
    identity: str = DEFAULT_DEEPCLAW_IDENTITY,
    channel_context: str | None = None,
    tool_descriptions: list[dict[str, Any]] | None = None,
    tool_instructions: list[str] | None = None,
    extra: str | None = None,
) -> str:
    parts = [identity]
    if channel_context:
        parts.append(f"\n{channel_context}")
    if tool_descriptions:
        tool_text = "\n".join(
            f"- {t['name']}: {t.get('description', '')}" for t in tool_descriptions
        )
        parts.append(f"\nAvailable tools:\n{tool_text}")
    if tool_instructions:
        instructions = [item.strip() for item in tool_instructions if item.strip()]
        if instructions:
            parts.append("\nTool usage rules:\n" + "\n\n".join(instructions))
    if extra:
        parts.append(f"\n{extra}")
    return "\n".join(parts)
