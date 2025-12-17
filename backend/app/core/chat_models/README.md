# Chat Models 包结构说明

## 📁 目录结构

```
app/core/chat_models/
├── __init__.py                # 统一入口，注册所有实现
├── base.py                   # 基类定义（BaseReasoningChatModel, StandardChatModel）
├── registry.py               # 模型注册表和创建工厂（ModelRegistry, create_chat_model）
├── README.md                 # 本文档
└── providers/                # 按推理字段类型分类的实现
    ├── __init__.py
    ├── reasoning_content.py  # 使用 reasoning_content 字段（如 SiliconFlow）
    ├── openai.py            # 使用 reasoning 字段（如 OpenAI）
    └── other.py             # 未知平台兜底（多字段尝试）
```

## 🎯 设计原则

### 1. 基于 Profile 的准确选择（核心）

- **优先使用 models.dev/env 配置**：通过 `reasoning_output` 字段判断是否为推理模型
- **回退到启发式判断**：如果 profile 不可用，基于模型名称关键词判断
- **统一 Matcher 签名**：所有 matcher 使用 `(model, base_url, profile)` 三参数

```python
def match_xxx(model: str, base_url: str, profile: dict | None = None) -> bool:
    # 1. 优先使用 profile（准确）
    if profile and isinstance(profile, dict):
        return profile.get("reasoning_output", False)
    
    # 2. 回退到模型名称判断（兼容）
    return "thinking" in model.lower()
```

### 2. 按字段类型分类（高效）

- **reasoning_content**：只从 `choices[0].delta.reasoning_content` 提取
  - 适用：SiliconFlow（硅基流动）等
- **reasoning**：只从 `choices[0].delta.reasoning` 提取
  - 适用：OpenAI 等
- 避免不必要的多字段尝试，提升性能

### 3. 未知平台才多字段尝试（兼容）

- **other.py** 作为兜底方案
- 按优先级尝试：`reasoning` → `reasoning_content` → `thinking` → `thought` 等
- 确保新平台也能工作

### 4. 注册顺序很重要

在 `__init__.py` 中的注册顺序：
1. `reasoning_content`：使用 reasoning_content 字段的平台
2. `openai`：使用 reasoning 字段的平台
3. `other`：兜底（多字段尝试）

## 📝 文件用途说明

### base.py
**做什么：**
- 定义 `BaseReasoningChatModel` 抽象基类
- 定义 `StandardChatModel` 标准实现（不处理推理）
- 统一处理推理内容写入 `message.additional_kwargs["reasoning_content"]`

**不做什么：**
- 不识别平台
- 不做字段匹配

### registry.py
**做什么：**
- 提供 `ModelRegistry` 类管理 matcher → model_class 映射
- 提供 `create_chat_model` 统一创建入口
- 基于 profile 遍历注册表找到第一个匹配的实现
- 所有 matcher 统一使用 3 参数签名: `(model, base_url, profile)`

**不做什么：**
- 不包含具体平台实现
- 不包含匹配逻辑（由各实现的 matcher 负责）

**Profile 优先原则：**
- 优先使用 profile 中的 `reasoning_output` 字段判断（准确）
- 如果 profile 不可用，回退到基于模型名称的启发式判断（兼容）

### providers/reasoning_content.py
**做什么：**
- 实现 `ReasoningContentChatModel`
- **只用 `reasoning_content` 字段**（确定字段类型用确定实现）
- 提供 `match_reasoning_content_model` 匹配器

**适用平台：**
- SiliconFlow（硅基流动）
- 其他使用 reasoning_content 字段的平台

**匹配特征：**
- base_url 包含已知使用此字段的平台（如 "siliconflow"）
- 模型名称包含 "thinking", "k2-thinking", "reasoning"

### providers/openai.py
**做什么：**
- 实现 `OpenAIReasoningChatModel`
- **只用 `reasoning` 字段**（确定平台用确定字段）
- 提供 `match_openai_reasoning` 匹配器

**平台特征：**
- base_url 为空、"https://api.openai.com/v1" 或包含 "openai"
- 模型名称包含 "reasoning", "o1", "thinking"

### providers/other.py
**做什么：**
- 实现 `OtherReasoningChatModel`
- **多字段尝试**（只有这个才做多字段尝试！）
- 提供 `match_other_reasoning` 匹配器（兜底）

**字段优先级：**
1. `reasoning`（OpenAI 标准）
2. `reasoning_content`（硅基流动）
3. `thinking`
4. `thought`
5. `reasoningContent`
6. `thought_content`

## 🔧 使用方式

### 业务代码使用

```python
from app.core.chat_models import create_chat_model

# 统一入口，自动选择合适的实现
model = create_chat_model(
    model="moonshotai/Kimi-K2-Thinking",
    base_url="https://api.siliconflow.cn/v1",
    api_key="sk-xxx",
)
```

### 调试/测试使用

```python
from app.core.chat_models import SiliconFlowReasoningChatModel

# 直接使用具体实现
model = SiliconFlowReasoningChatModel(
    model="moonshotai/Kimi-K2-Thinking",
    openai_api_base="https://api.siliconflow.cn/v1",
    openai_api_key="sk-xxx",
)
```

## 🚀 扩展新平台

### 步骤1：创建新文件

在 `providers/` 下创建新文件，例如 `togetherai.py`：

```python
"""TogetherAI 平台推理模型实现。"""

from app.core.chat_models.base import BaseReasoningChatModel
from app.core.logging import get_logger

logger = get_logger("chat_models.togetherai")


class TogetherAIReasoningChatModel(BaseReasoningChatModel):
    """TogetherAI 推理模型实现"""

    def _extract_reasoning_content(self, chunk: dict) -> str | None:
        """从 TogetherAI 响应中提取推理内容"""
        if not isinstance(chunk, dict):
            return None

        choices = chunk.get("choices", [])
        if choices and len(choices) > 0:
            delta = choices[0].get("delta", {})
            # TogetherAI 使用 reasoning 字段
            reasoning_content = delta.get("reasoning")
            if reasoning_content:
                logger.debug("[togetherai] 使用字段 'reasoning' 提取推理内容")
                return reasoning_content

        return None


def match_togetherai_reasoning(model: str, base_url: str) -> bool:
    """匹配 TogetherAI 推理模型"""
    is_togetherai = "together" in base_url.lower()
    has_reasoning_keyword = any(
        keyword in model.lower() 
        for keyword in ["reasoning", "thinking"]
    )
    return is_togetherai and has_reasoning_keyword
```

### 步骤2：在 __init__.py 中注册

```python
from app.core.chat_models.providers.togetherai import (
    TogetherAIReasoningChatModel,
    match_togetherai_reasoning,
)

# 在注册列表中添加（注意顺序！）
ModelRegistry.register(match_togetherai_reasoning, TogetherAIReasoningChatModel)
```

### 步骤3：完成！

无需修改其它代码，`create_chat_model` 会自动使用新的实现。

## ✅ 测试验证

```bash
cd backend
python -c "
from app.core.chat_models import (
    create_chat_model,
    SiliconFlowReasoningChatModel,
    OpenAIReasoningChatModel,
    OtherReasoningChatModel,
)

# 测试硅基流动
model1 = create_chat_model('moonshotai/Kimi-K2-Thinking', 'https://api.siliconflow.cn/v1', 'test')
assert isinstance(model1, SiliconFlowReasoningChatModel)

# 测试 OpenAI
model2 = create_chat_model('o1-preview', 'https://api.openai.com/v1', 'test')
assert isinstance(model2, OpenAIReasoningChatModel)

# 测试未知平台
model3 = create_chat_model('deepseek-reasoning', 'https://api.unknown.com/v1', 'test')
assert isinstance(model3, OtherReasoningChatModel)

print('✅ 所有测试通过！')
"
```

## 📊 性能优化效果

| 平台 | 旧实现 | 新实现 | 提升 |
|------|--------|--------|------|
| 硅基流动 | 6次字段尝试 | 1次字段查找 | 6倍 |
| OpenAI | 6次字段尝试 | 1次字段查找 | 6倍 |
| 未知平台 | 6次字段尝试 | 6次字段尝试 | 保持兼容 |

## 🔄 对外 API 兼容性

✅ **完全兼容**：其它模块的导入无需修改

```python
# llm.py 继续这样使用
from app.core.chat_models import create_chat_model

# test scripts 继续这样使用
from app.core.chat_models import SiliconFlowReasoningChatModel
```

## 📌 注意事项

1. **注册顺序很重要**：越具体的 matcher 越应先注册
2. **确定平台不做多字段尝试**：只在 `other.py` 中做兼容处理
3. **每个文件都有详细的文件头注释**：说明文件用途和设计理念
4. **扩展新平台很简单**：创建文件 → 实现类 → 注册 → 完成

