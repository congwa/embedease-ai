"""Chat Schema 测试"""

import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatRequest, ImageAttachment


class TestImageAttachment:
    """测试图片附件 Schema"""

    def test_required_fields(self):
        """测试必填字段"""
        image = ImageAttachment(
            id="img_123",
            url="https://example.com/image.jpg",
        )
        assert image.id == "img_123"
        assert image.url == "https://example.com/image.jpg"

    def test_full_attachment(self):
        """测试完整附件"""
        image = ImageAttachment(
            id="img_456",
            url="https://example.com/image.png",
            thumbnail_url="https://example.com/thumb.png",
            filename="product.png",
            size=102400,
            width=800,
            height=600,
            mime_type="image/png",
        )
        assert image.filename == "product.png"
        assert image.size == 102400
        assert image.width == 800
        assert image.height == 600
        assert image.mime_type == "image/png"

    def test_optional_fields_none(self):
        """测试可选字段默认为 None"""
        image = ImageAttachment(id="test", url="https://test.com/img.jpg")
        assert image.thumbnail_url is None
        assert image.filename is None
        assert image.size is None


class TestChatRequest:
    """测试聊天请求 Schema"""

    def test_required_fields(self):
        """测试必填字段"""
        request = ChatRequest(
            user_id="user_123",
            conversation_id="conv_456",
        )
        assert request.user_id == "user_123"
        assert request.conversation_id == "conv_456"
        assert request.message == ""

    def test_full_request(self):
        """测试完整请求"""
        request = ChatRequest(
            user_id="user_123",
            conversation_id="conv_456",
            message="推荐一款手机",
            mode="strict",
            agent_id="agent_789",
        )
        assert request.message == "推荐一款手机"
        assert request.mode == "strict"
        assert request.agent_id == "agent_789"

    def test_request_with_images(self):
        """测试带图片的请求"""
        request = ChatRequest(
            user_id="user_123",
            conversation_id="conv_456",
            message="这是什么产品？",
            images=[
                ImageAttachment(id="img_1", url="https://example.com/1.jpg"),
                ImageAttachment(id="img_2", url="https://example.com/2.jpg"),
            ],
        )
        assert len(request.images) == 2
        assert request.has_images is True

    def test_has_images_false(self):
        """测试无图片时 has_images 为 False"""
        request = ChatRequest(
            user_id="user_123",
            conversation_id="conv_456",
        )
        assert request.has_images is False

    def test_has_images_empty_list(self):
        """测试空图片列表时 has_images 为 False"""
        request = ChatRequest(
            user_id="user_123",
            conversation_id="conv_456",
            images=[],
        )
        assert request.has_images is False

    def test_effective_mode_from_request(self):
        """测试 effective_mode 使用请求中的 mode"""
        request = ChatRequest(
            user_id="user_123",
            conversation_id="conv_456",
            mode="free",
        )
        assert request.effective_mode == "free"

    def test_effective_mode_default(self):
        """测试 effective_mode 使用默认值"""
        request = ChatRequest(
            user_id="user_123",
            conversation_id="conv_456",
        )
        # 默认 mode 为 None 时，使用配置或 "natural"
        assert request.effective_mode in ("natural", "free", "strict")

    def test_valid_modes(self):
        """测试有效的聊天模式"""
        for mode in ["natural", "free", "strict"]:
            request = ChatRequest(
                user_id="user_123",
                conversation_id="conv_456",
                mode=mode,
            )
            assert request.mode == mode

    def test_invalid_mode(self):
        """测试无效的聊天模式"""
        with pytest.raises(ValidationError):
            ChatRequest(
                user_id="user_123",
                conversation_id="conv_456",
                mode="invalid_mode",
            )
