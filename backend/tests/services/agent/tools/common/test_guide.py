"""guide_user 工具测试

测试用户引导工具的模型和逻辑。
"""

import pytest
from pydantic import ValidationError

from app.services.agent.tools.common.guide import GuideUserResult


class TestGuideUserResult:
    """测试 GuideUserResult 模型"""

    def test_valid_minimal(self):
        """测试最小有效数据"""
        result = GuideUserResult(
            message="请提供更多信息",
            questions=["您的预算是多少？"],
            suggested_actions=["提供预算范围"],
        )
        assert result.message == "请提供更多信息"
        assert len(result.questions) == 1
        assert len(result.suggested_actions) == 1
        assert result.context is None

    def test_valid_full(self):
        """测试完整有效数据"""
        result = GuideUserResult(
            message="需要补充信息",
            questions=["预算？", "品牌偏好？"],
            suggested_actions=["提供预算", "选择品牌"],
            context={"stage": "missing_info", "intent": "product_search"},
        )
        assert result.context is not None
        assert result.context["stage"] == "missing_info"

    def test_empty_questions(self):
        """测试空问题列表"""
        result = GuideUserResult(
            message="消息",
            questions=[],
            suggested_actions=["动作"],
        )
        assert result.questions == []

    def test_empty_suggested_actions(self):
        """测试空建议动作列表"""
        result = GuideUserResult(
            message="消息",
            questions=["问题"],
            suggested_actions=[],
        )
        assert result.suggested_actions == []

    def test_multiple_questions(self):
        """测试多个问题"""
        questions = [
            "您的预算范围是多少？",
            "您更看重哪些功能？",
            "您偏好哪些品牌？",
        ]
        result = GuideUserResult(
            message="为了更好地帮助您",
            questions=questions,
            suggested_actions=["回答问题"],
        )
        assert len(result.questions) == 3

    def test_chinese_content(self):
        """测试中文内容"""
        result = GuideUserResult(
            message="您好！请问您需要什么帮助？",
            questions=["您想要什么类型的商品？", "预算大概多少？"],
            suggested_actions=["继续浏览", "联系客服"],
        )
        assert "您好" in result.message
        assert any("商品" in q for q in result.questions)

    def test_context_with_various_data(self):
        """测试不同类型的上下文数据"""
        result = GuideUserResult(
            message="消息",
            questions=["问题"],
            suggested_actions=["动作"],
            context={
                "stage": "clarify_goal",
                "intent": "compare",
                "tool_name": "search_products",
                "tool_status": "empty",
                "count": 0,
                "nested": {"key": "value"},
            },
        )
        assert result.context["count"] == 0
        assert result.context["nested"]["key"] == "value"

    def test_missing_message(self):
        """测试缺少 message 字段"""
        with pytest.raises(ValidationError):
            GuideUserResult(
                questions=["问题"],
                suggested_actions=["动作"],
            )

    def test_missing_questions(self):
        """测试缺少 questions 字段"""
        with pytest.raises(ValidationError):
            GuideUserResult(
                message="消息",
                suggested_actions=["动作"],
            )

    def test_missing_suggested_actions(self):
        """测试缺少 suggested_actions 字段"""
        with pytest.raises(ValidationError):
            GuideUserResult(
                message="消息",
                questions=["问题"],
            )


class TestGuideStages:
    """测试引导阶段"""

    def test_missing_info_stage_content(self):
        """测试 missing_info 阶段内容"""
        result = GuideUserResult(
            message="为了帮你更准确地找到合适的商品，我需要你补充一些关键信息。",
            questions=[
                "您的预算范围是多少？",
                "您更看重哪些功能或特性？",
            ],
            suggested_actions=[
                "告诉我您的预算",
                "说明您的使用场景",
            ],
            context={"stage": "missing_info"},
        )
        assert "补充" in result.message
        assert result.context["stage"] == "missing_info"

    def test_no_match_stage_content(self):
        """测试 no_match 阶段内容"""
        result = GuideUserResult(
            message="抱歉，没有找到完全匹配的商品。",
            questions=["是否尝试其他关键词？"],
            suggested_actions=["修改搜索条件", "浏览热门商品"],
            context={"stage": "no_match"},
        )
        assert "没有找到" in result.message
        assert result.context["stage"] == "no_match"

    def test_clarify_goal_stage_content(self):
        """测试 clarify_goal 阶段内容"""
        result = GuideUserResult(
            message="我想更好地理解您的需求。",
            questions=["您是想购买还是只是了解？"],
            suggested_actions=["明确购买意向"],
            context={"stage": "clarify_goal"},
        )
        assert result.context["stage"] == "clarify_goal"

    def test_fallback_stage_content(self):
        """测试 fallback 阶段内容"""
        result = GuideUserResult(
            message="我可以帮您做什么？",
            questions=["您需要什么帮助？"],
            suggested_actions=["搜索商品", "查看类目"],
            context={"stage": "fallback"},
        )
        assert result.context["stage"] == "fallback"
