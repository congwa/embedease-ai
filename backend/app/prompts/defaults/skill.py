"""技能生成提示词默认值"""

SKILL_PROMPTS: dict[str, dict] = {
    "skill.generate": {
        "category": "skill",
        "name": "技能生成",
        "description": "根据用户描述生成技能定义",
        "variables": ["description", "category", "applicable_agents", "examples"],
        "content": """你是一个专业的 AI 技能设计师。

根据用户的描述，生成一个结构化的技能定义。

## 用户描述
{description}

## 适用范围
- Agent 类型: {applicable_agents}
- 分类建议: {category}

## 示例对话（如有）
{examples}

## 输出要求
生成以下 JSON 格式的技能定义（只输出 JSON，不要其他内容）：
```json
{{
    "name": "技能名称（简洁有力，2-6个字）",
    "description": "技能描述（说明用途和触发条件，20-100字）",
    "category": "prompt|retrieval|tool|workflow",
    "content": "技能内容（Markdown 格式的提示词，包含清晰的指导规则）",
    "trigger_keywords": ["关键词1", "关键词2", "..."],
    "trigger_intents": ["意图1", "意图2"],
    "always_apply": false,
    "applicable_agents": ["product", "faq", "knowledge", "support"],
    "applicable_modes": ["natural", "strict", "free"]
}}
```

请确保：
1. name 简洁明了
2. content 是高质量的提示词，能有效增强 Agent 能力
3. trigger_keywords 覆盖用户可能的表达方式（至少5个）
4. applicable_agents 和 applicable_modes 根据实际用途设置
5. 只输出 JSON，不要其他解释文字
""",
    },
    "skill.refine": {
        "category": "skill",
        "name": "技能优化",
        "description": "根据用户反馈优化现有技能",
        "variables": ["skill_json", "feedback"],
        "content": """你是一个专业的 AI 技能设计师。

根据用户反馈优化现有技能。

## 现有技能
```json
{skill_json}
```

## 用户反馈
{feedback}

## 输出要求
输出优化后的 JSON（只输出 JSON，不要其他内容）。保持与原技能相同的结构。
""",
    },
}
