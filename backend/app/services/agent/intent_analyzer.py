"""意图识别 Agent 服务

专门用于识别用户意图的独立 Agent，使用 LLM 进行精准的意图分析。
"""

from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph

from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.schemas.intent import IntentAnalysis

logger = get_logger("intent_analyzer")

# 意图识别系统提示词
INTENT_ANALYSIS_SYSTEM_PROMPT = """你是一个专业的意图识别助手，负责分析用户的商品推荐相关需求。

## 任务
分析用户输入，识别其真实意图，并给出后续行动建议。

## 意图类型
1. **search** - 搜索商品
   - 用户想要查找某类商品
   - 示例："我想买降噪耳机"、"推荐跑步鞋"

2. **compare** - 对比商品
   - 用户想要比较多个商品
   - 示例："对比一下这几款耳机"、"哪个更好？"

3. **detail** - 查看详情
   - 用户想要了解某个商品的详细信息
   - 示例："这款商品怎么样？"、"介绍一下索尼耳机"

4. **filter_price** - 价格过滤
   - 用户有明确的价格预算
   - 示例："2000元以下的笔记本"、"预算1000元"

5. **recommend** - 推荐商品
   - 用户需要个性化推荐
   - 示例："适合学生的电脑"、"帮我推荐"

6. **question** - 一般性问题
   - 用户询问非商品相关的问题
   - 示例："什么是降噪？"、"如何选择耳机？"

7. **greeting** - 问候
   - 用户在打招呼
   - 示例："你好"、"在吗？"

8. **unknown** - 未知意图
   - 无法明确识别的意图
   - 示例：含糊不清的表述

## 分析要求
1. **intent**: 选择最匹配的意图类型（从上述8种中选择）
2. **confidence**: 给出置信度（0.0-1.0），越确定值越高
3. **suggested_actions**: 建议采取的行动（使用哪些工具、如何响应）
4. **reasoning**: 简要说明为什么识别为该意图

## 示例分析

输入："帮我找2000元以下的降噪耳机"
输出：
{
  "intent": "filter_price",
  "confidence": 0.95,
  "suggested_actions": [
    "使用 filter_by_price 工具过滤价格在2000元以下",
    "结合 search_products 工具搜索降噪耳机",
    "从结果中推荐最合适的商品"
  ],
  "reasoning": "用户明确提到价格预算（2000元以下）和商品类型（降噪耳机），主要意图是价格过滤"
}

输入："对比一下索尼和苹果的耳机"
输出：
{
  "intent": "compare",
  "confidence": 0.9,
  "suggested_actions": [
    "使用 search_products 搜索索尼和苹果的耳机",
    "提取商品ID",
    "使用 compare_products 工具进行对比",
    "给出对比结果和购买建议"
  ],
  "reasoning": "用户使用了'对比'关键词，明确想要比较两个品牌的耳机"
}

## 注意事项
- 优先识别明确的关键词（对比、价格、详情等）
- 如果有多个意图倾向，选择最主要的意图
- 置信度要客观，不确定时给出较低的值
- suggested_actions 要具体可执行
"""


class IntentAnalyzerService:
    """意图识别 Agent 服务

    使用独立的 LLM Agent 进行精准的意图识别。
    """

    _instance: "IntentAnalyzerService | None" = None
    _agent: CompiledStateGraph | None = None

    def __new__(cls) -> "IntentAnalyzerService":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_agent(self) -> CompiledStateGraph:
        """获取意图识别 Agent

        Returns:
            编译后的意图识别 Agent
        """
        if self._agent is None:
            logger.info("初始化意图识别 Agent...")

            # 初始化模型
            model = get_chat_model()

            try:
                # 创建意图识别 Agent
                self._agent = create_agent(
                    model=model,
                    tools=[],  # 不需要工具，只做意图识别
                    system_prompt=INTENT_ANALYSIS_SYSTEM_PROMPT,
                    response_format=IntentAnalysis,  # 结构化输出
                )

                logger.info("意图识别 Agent 初始化完成")

            except Exception as e:
                logger.error(f"意图识别 Agent 初始化失败: {e}")
                raise

        return self._agent

    async def analyze_intent(self, user_message: str) -> IntentAnalysis:
        """分析用户意图

        Args:
            user_message: 用户消息

        Returns:
            意图分析结果

        Example:
            >>> analyzer = IntentAnalyzerService()
            >>> result = await analyzer.analyze_intent("帮我找2000元以下的降噪耳机")
            >>> print(result.intent)  # "filter_price"
            >>> print(result.confidence)  # 0.95
        """
        agent = self.get_agent()

        logger.info(
            "开始分析用户意图",
            message_preview=user_message[:100],
        )

        try:
            # 调用意图识别 Agent
            result = await agent.ainvoke({"messages": [{"role": "user", "content": user_message}]})

            # 提取结构化响应
            intent_analysis = result.get("structured_response")

            if intent_analysis:
                logger.info(
                    "意图识别完成",
                    intent=intent_analysis.intent,
                    confidence=intent_analysis.confidence,
                )
                return intent_analysis
            else:
                logger.warning("未获取到结构化响应，返回默认意图")
                # 返回默认意图
                return IntentAnalysis(
                    intent="search",
                    confidence=0.5,
                    suggested_actions=["使用 search_products 搜索商品"],
                    reasoning="无法解析结构化响应，使用默认搜索意图",
                )

        except Exception as e:
            logger.error(f"意图识别失败: {e}", exc_info=True)
            # 返回默认意图
            return IntentAnalysis(
                intent="search",
                confidence=0.3,
                suggested_actions=["使用 search_products 搜索商品"],
                reasoning=f"意图识别出错: {str(e)}，使用默认搜索意图",
            )


# 全局单例
intent_analyzer_service = IntentAnalyzerService()
