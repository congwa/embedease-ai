"""用户引导工具

用于在信息不足、无法命中商品、或需要澄清用户需求时，产出标准化的引导问题与下一步建议。

该工具的目的是让 strict 模式下的“引导”也有可追溯的数据来源（tool.start/tool.end），
并将引导策略收敛为可迭代的工具输出。
"""

from __future__ import annotations

import json
import uuid

from typing import Annotated, Any

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("tool.guide_user")


class GuideUserResult(BaseModel):
    """引导用户的标准化结果"""

    message: str = Field(description="给用户展示的引导说明")
    questions: list[str] = Field(description="建议用户补充的信息/问题列表")
    suggested_actions: list[str] = Field(description="建议的下一步动作")
    context: dict[str, Any] | None = Field(default=None, description="可选：引导上下文")


@tool
def guide_user(
    user_message: Annotated[str, Field(description="用户本轮输入（原文）")],
    runtime: ToolRuntime,
    stage: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "引导阶段，可选：missing_info / no_match / clarify_goal / fallback"
            ),
        ),
    ] = None,
    intent: Annotated[str | None, Field(default=None, description="可选：识别出的意图")]=None,
    tool_name: Annotated[str | None, Field(default=None, description="可选：最近一次工具名称")]=None,
    tool_status: Annotated[
        str | None,
        Field(default=None, description="可选：工具状态 success/empty/error"),
    ] = None,
) -> str:
    """标准化引导用户补充信息，帮助命中商品检索/推荐链路。

    Returns:
        JSON 字符串，包含 message/questions/suggested_actions。
    """

    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "guide_user",
            "input": {
                "stage": stage,
                "intent": intent,
                "tool_name": tool_name,
                "tool_status": tool_status,
                "user_message_preview": user_message[:120],
            },
        },
    )

    stage_value = stage or "fallback"

    questions: list[str]
    suggested_actions: list[str]

    if stage_value == "missing_info":
        message = "为了帮你更准确地找到合适的商品，我需要你补充一些关键信息。"
        questions = [
            "你的预算范围是多少？（例如 500-1000 元）",
            "你更偏好的品类/类型是什么？（例如 降噪耳机/键盘/手机）",
            "主要使用场景是什么？（通勤/运动/办公/游戏）",
            "有没有必须要的功能点？（例如 ANC 降噪、续航、轻便、品牌偏好）",
        ]
        suggested_actions = [
            "补充以上信息后，我会调用工具检索商品并给出推荐",
            "如果你不确定预算，也可以告诉我你能接受的最高价",
        ]

    elif stage_value == "no_match":
        message = "我已尝试检索，但目前商品库里没有找到与你描述完全匹配的结果。我们可以换个方式更容易命中。"
        questions = [
            "你想要的核心关键词是什么？（品类 + 1-2 个关键特性）",
            "价格上限/下限是多少？",
            "你能接受相近替代方案吗？（例如 同价位但不同品牌/功能取舍）",
        ]
        suggested_actions = [
            "给我 2-3 个关键词，我会重新检索",
            "也可以提供你看中的商品名称/链接/型号，我可以按详情/对比来帮你选",
        ]

    elif stage_value == "clarify_goal":
        message = "我想先确认你的目标，这样我可以选择最合适的检索/对比策略。"
        questions = [
            "你是想要‘推荐几款’还是‘在两三款里选一个’？",
            "是否有明确的约束：预算/品牌/尺寸/重量/颜色/平台（京东/淘宝等）？",
        ]
        suggested_actions = [
            "确认目标后我会调用 search_products / compare_products 等工具",
        ]

    else:
        message = "为了确保推荐有据可依，我需要先拿到可检索的商品条件。"
        questions = [
            "你想买什么品类？",
            "预算大概多少？",
            "最在意的 1-2 个点是什么？（例如 续航/性能/轻便/降噪）",
        ]
        suggested_actions = [
            "补充后我会立即调用工具检索商品并给出推荐",
        ]

    result = GuideUserResult(
        message=message,
        questions=questions,
        suggested_actions=suggested_actions,
        context={
            "stage": stage_value,
            "intent": intent,
            "tool": {"name": tool_name, "status": tool_status},
        },
    )

    runtime.context.emitter.emit(
        StreamEventType.TOOL_END.value,
        {
            "tool_call_id": tool_call_id,
            "name": "guide_user",
            "status": "success",
            "output_preview": {
                "stage": stage_value,
                "question_count": len(questions),
            },
            "count": len(questions),
        },
    )

    logger.info(
        "└── 工具: guide_user 结束 ──┘",
        stage=stage_value,
        question_count=len(questions),
    )

    return result.model_dump_json(indent=2)
