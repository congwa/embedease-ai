"""硅基流动 v1 专用模型

解决问题：LangChain 的 _convert_delta_to_message_chunk 不处理 reasoning_content 字段，
导致硅基流动的思考内容在 v1 模式下丢失。

解决方案：覆盖 _convert_chunk_to_generation_chunk 方法，从原始 chunk 提取
reasoning_content，注入到 AIMessageChunk 的 content 中作为 reasoning block。
"""

from typing import Any

from langchain_core.outputs import ChatGenerationChunk

from langgraph_agent_kit.chat_models.v1.models import V1ChatModel

__all__ = ["SiliconFlowV1ChatModel"]


class SiliconFlowV1ChatModel(V1ChatModel):
    """硅基流动 v1 专用模型
    
    继承 V1ChatModel，覆盖 chunk 转换方法，从原始 chunk 的 
    delta.reasoning_content 提取思考内容，注入到 content_blocks 中。
    
    **关键特性**：
    - 保持 v1 输出格式（content 为 list[ContentBlock]）
    - 自动提取 reasoning_content 并转换为 {"type": "reasoning", "reasoning": ...}
    - 与 response_handler 的 v1 解析逻辑兼容
    """
    
    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        """从原始 chunk 提取 reasoning_content 并注入到 content_blocks
        
        工作流程：
        1. 调用父类方法获取标准 generation_chunk
        2. 从原始 chunk 的 delta.reasoning_content 提取思考内容
        3. 将 reasoning block 注入到 message.content 中
        """
        # 调用父类方法获取标准转换结果
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        
        if generation_chunk is None:
            return None
        
        # 从原始 chunk 提取 reasoning_content
        reasoning_content = self._extract_reasoning_content(chunk)
        
        if reasoning_content:
            # 将 reasoning 注入到 message.content 中
            message = generation_chunk.message
            
            # v1 模式下 content 应该是 list
            if isinstance(message.content, list):
                # 在现有 content_blocks 前面插入 reasoning block
                reasoning_block = {
                    "type": "reasoning",
                    "reasoning": reasoning_content,
                }
                message.content.insert(0, reasoning_block)
            elif isinstance(message.content, str):
                # 降级处理：如果 content 是字符串，转换为 list
                original_content = message.content
                new_content = [
                    {"type": "reasoning", "reasoning": reasoning_content},
                ]
                if original_content:
                    new_content.append({"type": "text", "text": original_content})
                # 创建新的 message 替换
                from langchain_core.messages import AIMessageChunk
                new_message = AIMessageChunk(
                    content=new_content,
                    additional_kwargs=message.additional_kwargs,
                    id=message.id,
                    tool_call_chunks=getattr(message, "tool_call_chunks", []),
                )
                generation_chunk = ChatGenerationChunk(
                    message=new_message,
                    generation_info=generation_chunk.generation_info,
                )
        
        return generation_chunk
    
    def _extract_reasoning_content(self, chunk: dict) -> str | None:
        """从原始 chunk 中提取 reasoning_content
        
        硅基流动的推理内容位于 choices[0].delta.reasoning_content
        """
        if not isinstance(chunk, dict):
            return None
        
        choices = chunk.get("choices", [])
        if not choices:
            return None
        
        choice = choices[0]
        if not isinstance(choice, dict):
            return None
        
        delta = choice.get("delta", {})
        if not isinstance(delta, dict):
            return None
        
        reasoning_content = delta.get("reasoning_content")
        if isinstance(reasoning_content, str) and reasoning_content:
            return reasoning_content
        
        return None
