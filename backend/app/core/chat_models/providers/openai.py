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
        """从响应中提取推理内容（使用 reasoning 字段）
        
        Args:
            chunk: API 响应的 chunk 数据
            
        Returns:
            推理内容字符串，如果没有则返回 None
        """
        if not isinstance(chunk, dict):
            return None

        # 1. 尝试从 choices[0].delta.reasoning 提取
        choices = chunk.get("choices", [])
        if choices and len(choices) > 0:
            delta = choices[0].get("delta", {}) if isinstance(choices[0], dict) else {}
            if isinstance(delta, dict):
                reasoning = delta.get("reasoning")
                if reasoning:
                    # logger.debug("从 delta.reasoning 提取推理内容")
                    return reasoning

        # 2. 尝试从 chunk 根层提取
        reasoning = chunk.get("reasoning")
        if reasoning:
            # logger.debug("从 chunk 根层提取 reasoning")
            return reasoning

        return None
