"""v1 模型基类

强制使用 LangChain v1 输出格式的模型封装。
"""

from typing import Any

from langchain_openai import ChatOpenAI

__all__ = [
    "V1ChatModel",
    "is_v1_model",
]


class V1ChatModel(ChatOpenAI):
    """强制 v1 输出的模型基类
    
    继承自 ChatOpenAI，强制设置 output_version="v1"，
    确保 AIMessage.content 直接存储标准化的 content_blocks。
    
    **关键特性**：
    - output_version 硬编码为 "v1"，不可通过参数覆盖
    - AIMessage.content 为 list[ContentBlock] 格式
    - 可直接使用 message.content_blocks 访问标准化内容
    - _chat_model_version 属性标识版本，供 response_handler 检测
    
    使用示例：
    ```python
    model = V1ChatModel(
        model="gpt-4",
        openai_api_base="...",
        openai_api_key="...",
    )
    
    response = await model.ainvoke(messages)
    # response.content 是 list[ContentBlock]
    # response.content_blocks 也可用
    ```
    """
    
    output_version: str = "v1"
    _chat_model_version: str = "v1"
    
    def __init__(self, **kwargs: Any) -> None:
        """初始化 v1 模型
        
        移除外部传入的 output_version 参数，强制使用 v1。
        """
        # 移除外部传入的 output_version，强制使用 v1
        kwargs.pop("output_version", None)
        super().__init__(output_version="v1", **kwargs)


def is_v1_model(model: Any) -> bool:
    """检测模型是否为 v1 版本
    
    用于 response_handler 自动检测应该使用哪种解析方式。
    
    Args:
        model: 模型实例
        
    Returns:
        True 如果是 v1 模型，否则 False
    """
    if model is None:
        return True  # 无 model 时默认使用 v1
    return getattr(model, "_chat_model_version", None) == "v1"
