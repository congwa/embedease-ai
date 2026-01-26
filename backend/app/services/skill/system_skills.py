"""系统内置技能定义

这些技能在系统初始化时自动创建，不可修改和删除。
"""

SYSTEM_SKILLS = [
    {
        "name": "商品对比专家",
        "description": "帮助用户进行多商品对比，分析优劣势，给出推荐建议",
        "category": "prompt",
        "content": """## 商品对比技能

当用户询问多个商品的对比时，按以下结构组织回答：

### 对比维度
1. **价格区间**：列出各商品价格，标注性价比
2. **核心功能**：突出差异化特性，用表格对比
3. **适用场景**：推荐最适合的使用场景
4. **用户评价**：如有评价数据，综合分析

### 输出格式
- 使用 Markdown 表格呈现对比结果
- 每个维度给出简明评价（优/良/中/差）
- 最后给出推荐建议，说明推荐理由

### 注意事项
- 保持客观中立，不偏向任何商品
- 如果数据不足，如实说明
- 推荐时考虑用户的实际需求
""",
        "trigger_keywords": ["对比", "区别", "哪个好", "推荐哪个", "比较", "VS", "vs", "和...哪个"],
        "trigger_intents": ["compare", "recommendation"],
        "applicable_agents": ["product"],
        "applicable_modes": ["natural", "strict"],
        "always_apply": False,
    },
    {
        "name": "FAQ精准匹配",
        "description": "提高 FAQ 匹配精度，确保回答准确性",
        "category": "retrieval",
        "content": """## FAQ 匹配增强

### 匹配规则
1. 优先精确匹配用户问题的核心关键词
2. 相似度阈值：0.75 以上才考虑推荐
3. 多个匹配时，按相关度排序展示前 3 条

### 回答格式
1. 直接回答核心问题（简明扼要）
2. 如有补充信息，分点列出
3. 提供相关问题建议（如有）

### 无匹配处理
如果没有找到匹配的 FAQ：
- 诚实告知用户
- 建议用户换一种方式描述问题
- 或引导用户联系人工客服
""",
        "trigger_keywords": [],
        "trigger_intents": ["faq", "question"],
        "applicable_agents": ["faq"],
        "applicable_modes": ["natural", "strict"],
        "always_apply": True,
    },
    {
        "name": "知识库检索优化",
        "description": "优化知识库检索结果的展示和引用",
        "category": "retrieval",
        "content": """## 知识库检索增强

### 检索原则
1. 优先检索最相关的文档片段
2. 结合多个片段综合回答
3. 标注信息来源

### 引用格式
- 在回答中引用具体来源：[来源: 文档名称]
- 如果信息来自多个文档，分别标注
- 不确定的内容要注明

### 回答结构
1. 直接回答用户问题
2. 补充相关背景信息
3. 列出参考来源
4. 建议进一步阅读（如有）
""",
        "trigger_keywords": [],
        "trigger_intents": ["search", "knowledge"],
        "applicable_agents": ["knowledge"],
        "applicable_modes": ["natural", "strict"],
        "always_apply": True,
    },
    {
        "name": "客服转接引导",
        "description": "智能判断是否需要转接人工客服",
        "category": "workflow",
        "content": """## 人工客服转接规则

### 自动转接场景
以下情况建议转接人工客服：
1. 用户明确要求人工服务
2. 涉及投诉、退款、赔偿等敏感问题
3. 连续 3 次无法理解用户意图
4. 涉及账户安全、隐私问题

### 转接话术
"您好，为了更好地帮助您解决问题，我将为您转接人工客服，请稍候..."

### 非转接场景
以下情况继续 AI 服务：
- 常规产品咨询
- FAQ 类问题
- 简单的信息查询
""",
        "trigger_keywords": ["人工", "客服", "投诉", "退款", "赔偿", "转人工"],
        "trigger_intents": ["handoff", "complaint"],
        "applicable_agents": ["support", "product", "faq"],
        "applicable_modes": ["natural", "strict", "free"],
        "always_apply": False,
    },
    {
        "name": "多轮对话记忆",
        "description": "增强多轮对话的上下文理解能力",
        "category": "prompt",
        "content": """## 多轮对话增强

### 上下文理解
1. 关注用户提到的实体（商品名、品牌、规格等）
2. 记住用户的偏好和约束条件
3. 理解指代词（这个、那个、它）的指向

### 对话连贯性
- 避免重复询问已知信息
- 基于历史对话推进
- 适时总结确认理解

### 话题切换
- 用户切换话题时平滑过渡
- 保留可能需要回顾的信息
- 提供话题回顾选项
""",
        "trigger_keywords": [],
        "trigger_intents": [],
        "applicable_agents": ["product", "faq", "knowledge", "support"],
        "applicable_modes": ["natural", "free"],
        "always_apply": True,
    },
]
