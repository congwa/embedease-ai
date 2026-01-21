"""噪音过滤中间件测试"""

import json

import pytest

from app.services.agent.middleware.noise_filter import (
    NoiseFilterMiddleware,
    GENERIC_NOISE_PATTERNS,
    MAX_PRODUCT_DESCRIPTION_LENGTH,
    MAX_PRODUCTS_IN_LIST,
)


class TestNoiseFilterInit:
    """测试中间件初始化"""

    def test_default_init(self):
        """测试默认初始化"""
        middleware = NoiseFilterMiddleware()
        assert middleware.enabled is True
        assert middleware.max_output_chars == 2000
        assert middleware.compress_json is True

    def test_custom_init(self):
        """测试自定义初始化"""
        middleware = NoiseFilterMiddleware(
            enabled=False,
            max_output_chars=5000,
            preserve_head_chars=1000,
            preserve_tail_chars=2000,
            compress_json=False,
        )
        assert middleware.enabled is False
        assert middleware.max_output_chars == 5000
        assert middleware.preserve_head_chars == 1000
        assert middleware.compress_json is False

    def test_custom_noise_patterns(self):
        """测试自定义噪音模式"""
        patterns = [r"DEBUG:.*\n", r"INFO:.*\n"]
        middleware = NoiseFilterMiddleware(noise_patterns=patterns)
        assert len(middleware.noise_patterns) == 2


class TestRemoveNoise:
    """测试噪音移除功能"""

    def test_remove_npm_warnings(self):
        """测试移除 npm 警告"""
        middleware = NoiseFilterMiddleware()
        text = "npm WARN deprecated module@1.0.0\nActual content\n"
        result = middleware._remove_noise(text)
        assert "npm WARN" not in result
        assert "Actual content" in result

    def test_remove_pip_logs(self):
        """测试移除 pip 日志"""
        middleware = NoiseFilterMiddleware()
        text = "Collecting requests==2.31.0\nDownloading requests-2.31.0.whl\nDone\n"
        result = middleware._remove_noise(text)
        assert "Collecting" not in result
        assert "Downloading" not in result

    def test_remove_progress_bars(self):
        """测试移除进度条"""
        middleware = NoiseFilterMiddleware()
        text = "[=====>    ] 50%\nContent here\n"
        result = middleware._remove_noise(text)
        assert "Content here" in result

    def test_remove_multiple_empty_lines(self):
        """测试移除多余空行"""
        middleware = NoiseFilterMiddleware()
        text = "Line 1\n\n\n\n\nLine 2"
        result = middleware._remove_noise(text)
        assert "\n\n\n" not in result

    def test_normal_content_preserved(self):
        """测试正常内容保留"""
        middleware = NoiseFilterMiddleware()
        text = "这是正常的商品描述信息，不应该被过滤。"
        result = middleware._remove_noise(text)
        assert result == text


class TestTruncateString:
    """测试字符串截断功能"""

    def test_no_truncation_needed(self):
        """测试不需要截断"""
        middleware = NoiseFilterMiddleware()
        text = "短文本"
        result = middleware._truncate_string(text, 100)
        assert result == text

    def test_truncation_with_suffix(self):
        """测试带后缀截断"""
        middleware = NoiseFilterMiddleware()
        text = "这是一个很长的文本内容"
        result = middleware._truncate_string(text, 10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_custom_suffix(self):
        """测试自定义后缀"""
        middleware = NoiseFilterMiddleware()
        text = "Long text content here"
        result = middleware._truncate_string(text, 15, suffix="[...]")
        assert result.endswith("[...]")


class TestCompressProduct:
    """测试商品压缩功能"""

    def test_compress_long_description(self):
        """测试压缩长描述"""
        middleware = NoiseFilterMiddleware(max_product_description=50)
        product = {
            "id": "1",
            "name": "商品名称",
            "description": "这是一个非常长的商品描述，包含很多详细信息" * 10,
        }
        result = middleware._compress_product(product)
        assert len(result["description"]) <= 50
        assert result["description"].endswith("...")

    def test_preserve_short_description(self):
        """测试保留短描述"""
        middleware = NoiseFilterMiddleware(max_product_description=100)
        product = {
            "id": "1",
            "name": "商品",
            "description": "简短描述",
        }
        result = middleware._compress_product(product)
        assert result["description"] == "简短描述"

    def test_compress_summary(self):
        """测试压缩摘要字段"""
        middleware = NoiseFilterMiddleware()
        product = {
            "id": "1",
            "summary": "非常长的摘要内容" * 50,
        }
        result = middleware._compress_product(product)
        assert len(result["summary"]) <= 150

    def test_compress_content_field(self):
        """测试压缩 content 字段（知识库场景）"""
        middleware = NoiseFilterMiddleware(max_product_description=100)
        product = {
            "id": "1",
            "content": "这是知识库的内容片段，可能非常长" * 20,
        }
        result = middleware._compress_product(product)
        assert len(result["content"]) <= 100


class TestCompressProductList:
    """测试商品列表压缩功能"""

    def test_no_compression_small_list(self):
        """测试小列表不压缩"""
        middleware = NoiseFilterMiddleware(max_products_in_list=5)
        products = [{"id": str(i), "name": f"商品{i}"} for i in range(3)]
        result = middleware._compress_product_list(products)
        assert len(result) == 3

    def test_compress_large_list(self):
        """测试大列表压缩"""
        middleware = NoiseFilterMiddleware(max_products_in_list=3)
        products = [{"id": str(i), "name": f"商品{i}"} for i in range(10)]
        result = middleware._compress_product_list(products)
        assert len(result) == 4  # 3 商品 + 1 截断标记
        assert result[-1]["_truncated"] is True
        assert result[-1]["_total_count"] == 10
        assert "7 个商品未显示" in result[-1]["_message"]

    def test_compress_with_description_truncation(self):
        """测试列表压缩同时截断描述"""
        middleware = NoiseFilterMiddleware(
            max_products_in_list=2,
            max_product_description=20,
        )
        products = [
            {"id": "1", "name": "商品1", "description": "非常长的描述" * 10},
            {"id": "2", "name": "商品2", "description": "另一个长描述" * 10},
            {"id": "3", "name": "商品3", "description": "第三个长描述" * 10},
        ]
        result = middleware._compress_product_list(products)
        assert len(result) == 3  # 2 商品 + 1 截断标记
        assert len(result[0]["description"]) <= 20


class TestCompressJsonOutput:
    """测试 JSON 输出压缩"""

    def test_compress_product_array(self):
        """测试压缩商品数组"""
        middleware = NoiseFilterMiddleware(
            max_products_in_list=2,
            max_product_description=30,
        )
        products = [
            {"id": "1", "name": "手机", "price": 1000, "description": "非常详细的描述" * 10},
            {"id": "2", "name": "耳机", "price": 200, "description": "另一个详细描述" * 10},
            {"id": "3", "name": "电脑", "price": 5000, "description": "第三个描述" * 10},
        ]
        json_str = json.dumps(products, ensure_ascii=False)
        result = middleware._compress_json_output(json_str)
        parsed = json.loads(result)
        assert len(parsed) == 3  # 2 商品 + 1 截断标记
        assert parsed[-1]["_truncated"] is True

    def test_compress_products_field(self):
        """测试压缩 products 字段"""
        middleware = NoiseFilterMiddleware(max_products_in_list=1)
        data = {
            "total": 5,
            "products": [
                {"id": "1", "name": "商品1"},
                {"id": "2", "name": "商品2"},
            ],
        }
        json_str = json.dumps(data, ensure_ascii=False)
        result = middleware._compress_json_output(json_str)
        parsed = json.loads(result)
        assert len(parsed["products"]) == 2  # 1 商品 + 1 截断标记

    def test_non_json_passthrough(self):
        """测试非 JSON 内容透传"""
        middleware = NoiseFilterMiddleware()
        text = "这不是 JSON 内容"
        result = middleware._compress_json_output(text)
        assert result == text

    def test_compress_disabled(self):
        """测试禁用 JSON 压缩"""
        middleware = NoiseFilterMiddleware(compress_json=False)
        products = [{"id": "1", "description": "长描述" * 100}]
        json_str = json.dumps(products, ensure_ascii=False)
        result = middleware._compress_json_output(json_str)
        assert result == json_str  # 原样返回


class TestTruncate:
    """测试长文本截断"""

    def test_no_truncation_short_text(self):
        """测试短文本不截断"""
        middleware = NoiseFilterMiddleware(max_output_chars=1000)
        text = "短文本内容"
        result = middleware._truncate(text)
        assert result == text

    def test_truncation_preserves_head_tail(self):
        """测试截断保留头尾"""
        middleware = NoiseFilterMiddleware(
            max_output_chars=100,
            preserve_head_chars=20,
            preserve_tail_chars=30,
        )
        text = "头部内容" + "中间内容" * 50 + "尾部内容"
        result = middleware._truncate(text)
        assert "头部" in result
        assert "尾部" in result
        assert "[已截断" in result

    def test_truncation_shows_total_length(self):
        """测试截断显示原始长度"""
        middleware = NoiseFilterMiddleware(
            max_output_chars=50,
            preserve_head_chars=10,
            preserve_tail_chars=10,
        )
        text = "x" * 1000
        result = middleware._truncate(text)
        assert "1000" in result


class TestFilterOutput:
    """测试完整过滤流程"""

    def test_filter_combined(self):
        """测试组合过滤"""
        middleware = NoiseFilterMiddleware(
            max_output_chars=500,
            max_products_in_list=2,
            max_product_description=50,
        )
        products = [
            {"id": "1", "name": "商品", "description": "长描述" * 20},
            {"id": "2", "name": "商品2", "description": "长描述2" * 20},
            {"id": "3", "name": "商品3", "description": "长描述3" * 20},
        ]
        output = json.dumps(products, ensure_ascii=False)
        result = middleware._filter_output(output)

        # 验证压缩和截断
        assert len(result) <= 500

    def test_filter_empty_string(self):
        """测试空字符串"""
        middleware = NoiseFilterMiddleware()
        assert middleware._filter_output("") == ""
        assert middleware._filter_output(None) is None

    def test_filter_disabled(self):
        """测试禁用过滤"""
        middleware = NoiseFilterMiddleware(enabled=False)
        text = "npm WARN test\n" + "x" * 5000
        # _filter_output 本身不检查 enabled，enabled 在 wrap 方法中检查
        result = middleware._filter_output(text)
        assert "npm WARN" not in result
