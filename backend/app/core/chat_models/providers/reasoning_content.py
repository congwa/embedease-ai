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
        """从响应中提取推理内容（使用 reasoning_content 字段）
        
        Args:
            chunk: API 响应的 chunk 数据
            
        Returns:
            推理内容字符串，如果没有则返回 None
        """
        if not isinstance(chunk, dict):
            return None

        # 1. 尝试从 choices[0].delta.reasoning_content 提取
        choices = chunk.get("choices", [])
        if choices and len(choices) > 0:
            delta = choices[0].get("delta", {}) if isinstance(choices[0], dict) else {}
            if isinstance(delta, dict):
                reasoning_content = delta.get("reasoning_content")
                if reasoning_content:
                    # logger.debug("从 delta.reasoning_content 提取推理内容")
                    return reasoning_content

        # 2. 尝试从 chunk 根层提取
        reasoning_content = chunk.get("reasoning_content")
        if reasoning_content:
            # logger.debug("从 chunk 根层提取 reasoning_content")
            return reasoning_content

        return None
