"""使用 reasoning 字段的推理模型实现（OpenAI 标准）

适用提供商：
- OpenAI 原生
- 其他遵循 OpenAI 标准的提供商

推理字段：`choices[0].delta.reasoning`
"""

from app.core.chat_models.base import BaseReasoningChatModel
from app.core.logging import get_logger

logger = get_logger("chat_models.openai")


class OpenAIReasoningChatModel(BaseReasoningChatModel):
    """使用 reasoning 字段的推理模型实现（OpenAI 标准）
    
    用于 OpenAI 原生推理模型和其他遵循 OpenAI 标准的平台
    """

    def _extract_reasoning_content(self, chunk: dict) -> str | None:
        return super()._extract_reasoning_content(chunk)
