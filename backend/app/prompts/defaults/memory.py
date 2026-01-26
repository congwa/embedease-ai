"""记忆系统提示词默认值"""

MEMORY_PROMPTS: dict[str, dict] = {
    "memory.fact_extraction": {
        "category": "memory",
        "name": "事实抽取",
        "description": "从对话中提取用户关键事实信息",
        "variables": [],
        "content": """你是一个精准的事实抽取助手。请从以下对话中提取用户的关键事实信息。

事实应该是：
1. 用户的偏好（预算、品类、风格等）
2. 用户的个人信息（职业、家庭成员、使用场景等）
3. 用户的限制或禁忌（过敏、禁用成分等）
4. 用户的计划或目标

请以 JSON 格式返回，格式如下：
{
    "facts": [
        "事实1",
        "事实2"
    ]
}

注意：
- 只提取明确陈述的事实，不要推测
- 每条事实应该是独立、完整的陈述
- 如果没有可提取的事实，返回空数组 {"facts": []}
- 保持原文语言
- 不要包含任何额外的解释文字，只返回 JSON
""",
    },
    "memory.action_decision": {
        "category": "memory",
        "name": "记忆操作决策",
        "description": "判断如何处理新事实与现有记忆的关系",
        "variables": [],
        "content": """你是一个记忆管理助手。请判断如何处理新事实与现有记忆的关系。

操作类型：
- ADD: 新事实是全新信息，应该添加
- UPDATE: 新事实是对现有记忆的更新或补充（返回 target_id）
- DELETE: 新事实表明某条现有记忆已过时或错误（返回 target_id）
- NONE: 新事实与现有记忆重复或无意义，不需要操作

请以 JSON 格式返回：
{
    "action": "ADD",
    "target_id": null,
    "reason": "简短说明原因"
}

注意：
- action 必须是 ADD、UPDATE、DELETE、NONE 之一
- 如果是 UPDATE 或 DELETE，target_id 必须填写目标记忆的 ID
- 如果是 ADD 或 NONE，target_id 为 null
- 不要包含任何额外的解释文字，只返回 JSON
""",
    },
    "memory.graph_extraction": {
        "category": "memory",
        "name": "知识图谱抽取",
        "description": "从对话中提取实体和关系",
        "variables": [],
        "content": """你是一个知识图谱抽取助手。请从以下对话中提取实体和关系。

实体类型包括：
- PERSON: 人物（用户、家人、朋友等）
- PRODUCT: 产品/商品
- CATEGORY: 品类
- BRAND: 品牌
- EVENT: 事件/计划
- ATTRIBUTE: 属性/特征
- LOCATION: 地点

关系类型包括：
- OWNS: 拥有
- PREFERS: 偏好
- DISLIKES: 不喜欢
- RELATED_TO: 相关
- BELONGS_TO: 属于
- PLANS: 计划
- FAMILY_OF: 家人
- FRIEND_OF: 朋友

请以 JSON 格式返回：
{
    "entities": [
        {"name": "实体名称", "entity_type": "类型", "observations": ["观察1"]}
    ],
    "relations": [
        {"from_entity": "起点实体", "to_entity": "终点实体", "relation_type": "关系类型"}
    ]
}

注意：
- 实体名称应该是具体的、可识别的
- 关系应该是有意义的、明确的
- 如果没有可提取的内容，返回空数组
- 不要包含任何额外的解释文字，只返回 JSON
""",
    },
}
