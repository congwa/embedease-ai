"""使用 reasoning_content 字段的推理模型实现

适用提供商：
- SiliconFlow（硅基流动）：OpenAI 兼容模式，使用 reasoning_content 字段
- 其他使用 reasoning_content 字段的平台

推理字段：`choices[0].delta.reasoning_content`
"""

from app.core.chat_models.base import BaseReasoningChatModel
from app.core.logging import get_logger

logger = get_logger("chat_models.reasoning_content")


class ReasoningContentChatModel(BaseReasoningChatModel):
    """使用 reasoning_content 字段的推理模型实现
    
    用于 SiliconFlow 等 OpenAI 兼容平台的推理模型
    """

    def _extract_reasoning_content(self, chunk: dict) -> str | None:
        return super()._extract_reasoning_content(chunk)
