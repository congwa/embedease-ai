"""自定义 ChatOpenAI 子类 - 支持不同平台的扩展功能

架构设计：
- BaseReasoningChatModel: 抽象基类，定义推理模型接口
- 具体实现类：各平台的具体实现（SiliconFlow, TogetherAI 等）
- ModelRegistry: 模型注册表，根据模型特征自动选择合适的实现
- Agent 层完全无感知，统一使用 BaseChatModel 接口
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from app.core.logging import get_logger

logger = get_logger("chat_models")


class BaseReasoningChatModel(ChatOpenAI, ABC):
    """推理模型抽象基类
    
    所有支持推理内容的模型实现都应该继承此类。
    通过多态特性，Agent 层可以无感知地使用不同的模型实现。
    """

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> Any:
        """转换 chunk 以支持推理内容
        
        子类可以重写此方法来实现平台特定的推理内容提取逻辑。
        """
        # 调用父类方法获取基础转换
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        
        if generation_chunk is None:
            return None
        
        # 提取推理内容（由子类实现具体逻辑）
        reasoning_content = self._extract_reasoning_content(chunk)
        
        if reasoning_content:
            if not hasattr(generation_chunk.message, "additional_kwargs"):
                generation_chunk.message.additional_kwargs = {}
            
            generation_chunk.message.additional_kwargs["reasoning_content"] = (
                reasoning_content
            )
        
        return generation_chunk

    @abstractmethod
    def _extract_reasoning_content(self, chunk: dict) -> str | None:
        """从 chunk 中提取推理内容
        
        子类必须实现此方法，定义如何从平台特定的响应格式中提取推理内容。
        
        Args:
            chunk: 原始 chunk 数据（dict 格式）
        
        Returns:
            推理内容字符串，如果没有则返回 None
        """
        pass


class SiliconFlowReasoningChatModel(BaseReasoningChatModel):
    """硅基流动推理模型实现
    
    支持 SiliconFlow 平台的 reasoning_content 字段。
    """

    def _extract_reasoning_content(self, chunk: dict) -> str | None:
        """从 SiliconFlow 响应中提取推理内容"""
        choices = (
            chunk.get("choices", [])
            or chunk.get("chunk", {}).get("choices", [])
        )
        
        if choices and len(choices) > 0:
            delta = choices[0].get("delta", {})
            return delta.get("reasoning_content")
        
        return None


class StandardChatModel(ChatOpenAI):
    """标准模型实现（不支持推理内容）
    
    这是默认实现，用于不支持推理内容的模型。
    直接使用 ChatOpenAI，不做任何修改。
    """
    pass


class ModelRegistry:
    """模型注册表
    
    根据模型特征（名称、平台等）自动选择合适的实现类。
    支持注册自定义匹配器和实现类。
    """
    
    # 注册表：匹配器函数 -> 实现类
    _registry: ClassVar[dict[Callable[[str, str], bool], type[BaseChatModel]]] = {}
    
    @classmethod
    def register(
        cls,
        matcher: Callable[[str, str], bool],
        model_class: type[BaseChatModel],
    ) -> None:
        """注册模型实现
        
        Args:
            matcher: 匹配器函数，接收 (model_name, base_url) 返回是否匹配
            model_class: 对应的模型实现类
        """
        cls._registry[matcher] = model_class
        logger.debug(
            "注册模型实现",
            matcher=matcher.__name__,
            model_class=model_class.__name__,
        )
    
    @classmethod
    def create(
        cls,
        model: str,
        base_url: str,
        api_key: str,
        **kwargs: Any,
    ) -> BaseChatModel:
        """根据模型特征创建合适的实例
        
        Args:
            model: 模型名称
            base_url: API 基础 URL
            api_key: API Key
            **kwargs: 其他参数
        
        Returns:
            配置好的模型实例
        """
        # 遍历注册表，找到第一个匹配的实现
        for matcher, model_class in cls._registry.items():
            if matcher(model, base_url):
                logger.info(
                    "匹配到模型实现",
                    model=model,
                    base_url=base_url,
                    implementation=model_class.__name__,
                )
                return model_class(
                    model=model,
                    openai_api_base=base_url,
                    openai_api_key=api_key,
                    **kwargs,
                )
        
        # 默认使用标准实现
        logger.info(
            "使用默认标准模型",
            model=model,
            base_url=base_url,
        )
        return StandardChatModel(
            model=model,
            openai_api_base=base_url,
            openai_api_key=api_key,
            **kwargs,
        )


# ===== 注册内置模型实现 =====

def _match_siliconflow_reasoning(model: str, base_url: str) -> bool:
    """匹配硅基流动推理模型"""
    # 检查 base_url 是否包含 siliconflow
    is_siliconflow = "siliconflow" in base_url.lower()
    
    # 检查模型名称是否包含推理相关关键词
    reasoning_keywords = ["thinking", "k2-thinking", "reasoning"]
    has_reasoning_keyword = any(
        keyword.lower() in model.lower() for keyword in reasoning_keywords
    )
    
    return is_siliconflow and has_reasoning_keyword


# 注册硅基流动推理模型
ModelRegistry.register(_match_siliconflow_reasoning, SiliconFlowReasoningChatModel)


# ===== 扩展指南 =====
# 
# 如何添加新的模型实现：
# 
# 1. 创建新的实现类（继承 BaseReasoningChatModel 或 StandardChatModel）
# 
#    class TogetherAIReasoningChatModel(BaseReasoningChatModel):
#        def _extract_reasoning_content(self, chunk: dict) -> str | None:
#            # 实现 TogetherAI 特定的推理内容提取逻辑
#            return chunk.get("reasoning", {}).get("content")
# 
# 2. 创建匹配器函数
# 
#    def _match_togetherai_reasoning(model: str, base_url: str) -> bool:
#        return "together" in base_url.lower() and "reasoning" in model.lower()
# 
# 3. 注册到 ModelRegistry
# 
#    ModelRegistry.register(_match_togetherai_reasoning, TogetherAIReasoningChatModel)
# 
# 完成！Agent 层无需任何修改，会自动使用新的实现。


def create_chat_model(
    model: str,
    base_url: str,
    api_key: str,
    **kwargs: Any,
) -> BaseChatModel:
    """创建聊天模型实例（统一入口）
    
    这是对外提供的统一接口，Agent 层只需调用此函数即可。
    内部通过 ModelRegistry 自动选择合适的实现，完全无感知。
    
    Args:
        model: 模型名称
        base_url: API 基础 URL
        api_key: API Key
        **kwargs: 其他参数（temperature, max_tokens 等）
    
    Returns:
        配置好的模型实例（统一返回 BaseChatModel 接口）
    
    Examples:
        >>> # Agent 层使用，完全无感知具体实现
        >>> model = create_chat_model(
        ...     model="moonshotai/Kimi-K2-Thinking",
        ...     base_url="https://api.siliconflow.cn/v1",
        ...     api_key="sk-...",
        ... )
        >>> # model 可能是 SiliconFlowReasoningChatModel 或 StandardChatModel
        >>> # 但 Agent 层不需要关心，统一使用 BaseChatModel 接口
    """
    return ModelRegistry.create(model, base_url, api_key, **kwargs)
