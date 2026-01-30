# 测试文档

本文档描述了 embedease-ai 后端的测试覆盖情况，包含单元测试和集成测试两大类。

## 测试概览

| 测试类型 | 测试文件 | 测试数量 | 说明 |
|---------|---------|---------|------|
| 单元测试 | `prompts/test_registry.py` | 14 | PromptRegistry 服务测试 |
| 集成测试 | `integration/prompts/test_agent_prompts.py` | 6 | Agent 提示词效果测试 |
| 集成测试 | `integration/prompts/test_crawler_prompts.py` | 3 | 爬虫提示词效果测试 |
| 集成测试 | `integration/prompts/test_memory_prompts.py` | 4 | 记忆系统提示词效果测试 |
| 集成测试 | `integration/prompts/test_skill_prompts.py` | 3 | 技能生成提示词效果测试 |

---

## 单元测试

### `prompts/test_registry.py` - PromptRegistry 服务测试

测试 `PromptRegistry` 类的核心功能，确保提示词管理系统正常工作。

#### 测试用例

| 测试方法 | 测试内容 | 保证的能力 |
|---------|---------|-----------|
| `test_get_default_prompt` | 获取默认提示词（数据库无记录） | 系统能正确返回内置的默认提示词 |
| `test_get_nonexistent_prompt` | 获取不存在的提示词 | 对不存在的 key 返回 None，不会抛出异常 |
| `test_get_content_default` | 获取默认提示词内容 | 能直接获取提示词文本内容 |
| `test_get_content_with_variables` | 带变量的提示词格式化 | 支持模板变量替换功能 |
| `test_list_all_default_prompts` | 列出所有默认提示词 | 系统内置至少 10 个默认提示词 |
| `test_list_all_filter_category` | 按分类过滤提示词 | 支持按 category 筛选提示词 |
| `test_update_creates_new_record` | 更新创建新记录 | 自定义提示词时正确创建数据库记录 |
| `test_update_nonexistent_raises` | 更新不存在的提示词 | 更新无效 key 时抛出明确错误 |
| `test_reset_deletes_record` | 重置删除数据库记录 | 重置后恢复为默认值 |
| `test_reset_nonexistent_raises` | 重置不存在的提示词 | 重置无效 key 时抛出明确错误 |
| `test_delete_custom_prompt` | 删除自定义提示词 | 支持删除用户创建的提示词 |
| `test_delete_default_prompt_raises` | 删除默认提示词 | 禁止删除系统内置提示词 |

#### 便捷函数测试 (`TestGetDefaultPromptContent`)

| 测试方法 | 测试内容 | 保证的能力 |
|---------|---------|-----------|
| `test_get_existing_prompt` | 获取存在的提示词 | 便捷函数能正确获取内容 |
| `test_get_nonexistent_prompt` | 获取不存在的提示词 | 便捷函数对无效 key 返回 None |
| `test_format_with_variables` | 变量格式化 | 便捷函数支持模板变量替换 |

---

## 集成测试

> **重要**：集成测试需要配置真实的 `LLM_API_KEY` 和 `LLM_PROVIDER` 环境变量。未配置时测试会自动跳过。

### `integration/prompts/test_agent_prompts.py` - Agent 提示词测试

验证各类 Agent 系统提示词在真实 AI 调用场景下的效果。

| 测试方法 | 测试内容 | 保证的能力 |
|---------|---------|-----------|
| `test_product_prompt_generates_recommendation` | 商品推荐提示词 | AI 能生成专业友好的商品推荐回复 |
| `test_faq_prompt_answers_question` | FAQ 提示词 | AI 能直接回答或引导用户的常见问题 |
| `test_kb_prompt_references_data` | 知识库提示词 | AI 在无数据时明确表示需要检索 |
| `test_custom_prompt_is_helpful` | 自定义提示词 | AI 保持有帮助的通用助手行为 |

---

### `integration/prompts/test_crawler_prompts.py` - 爬虫提示词测试

验证爬虫数据提取提示词的 AI 调用效果。

| 测试方法 | 测试内容 | 保证的能力 |
|---------|---------|-----------|
| `test_product_extraction_returns_json` | 商品信息提取 | AI 能从 HTML 中提取商品信息并返回有效 JSON |
| `test_non_product_page_detection` | 非商品页面检测 | AI 能正确识别非商品页面 |
| `test_content_extraction_general` | 通用内容提取 | AI 能提取文章等通用内容 |

#### 提取结果验证

- **商品页面**：返回 `is_product_page: true`，包含 `title/name/price` 等字段
- **非商品页面**：返回 `is_product_page: false`

---

### `integration/prompts/test_memory_prompts.py` - 记忆系统提示词测试

验证用户记忆管理相关提示词的 AI 调用效果。

| 测试方法 | 测试内容 | 保证的能力 |
|---------|---------|-----------|
| `test_fact_extraction_returns_json` | 事实抽取 | AI 能从对话中提取用户相关事实 |
| `test_memory_action_decision` | 记忆操作决策 | AI 能正确决定 ADD/UPDATE/DELETE/NONE 操作 |
| `test_graph_extraction_entities_and_relations` | 知识图谱抽取 | AI 能提取实体和关系构建知识图谱 |
| `test_fact_extraction_empty_conversation` | 空对话处理 | 简单问候返回空事实数组 |

#### 数据结构验证

- **事实抽取**：返回 `{ "facts": [...] }`
- **操作决策**：返回 `{ "action": "ADD|UPDATE|DELETE|NONE", "target_id": "..." }`
- **图谱抽取**：返回 `{ "entities": [...], "relations": [...] }`

---

### `integration/prompts/test_skill_prompts.py` - 技能生成提示词测试

验证技能（Skill）生成和优化提示词的 AI 调用效果。

| 测试方法 | 测试内容 | 保证的能力 |
|---------|---------|-----------|
| `test_skill_generate_returns_valid_json` | 技能生成 | AI 能根据描述生成完整的技能定义 JSON |
| `test_skill_refine_improves_skill` | 技能优化 | AI 能根据反馈改进技能定义 |
| `test_skill_generate_with_examples` | 带示例生成 | AI 能参考示例生成更精准的技能 |

#### 技能定义结构验证

```json
{
  "name": "名称（≤20字符）",
  "description": "描述",
  "category": "prompt",
  "content": "内容（>20字符）",
  "trigger_keywords": ["关键词1", "关键词2", "..."]  // ≥3个
}
```

---

## 运行测试

### 运行所有单元测试

```bash
pytest backend/tests/prompts/ -v
```

### 运行集成测试（需配置 API）

```bash
# 确保 .env 中配置了 LLM_API_KEY 和 LLM_PROVIDER
pytest backend/tests/integration/ -v -m integration
```

### 运行特定测试文件

```bash
pytest backend/tests/prompts/test_registry.py -v
pytest backend/tests/integration/prompts/test_agent_prompts.py -v
```

---

## 质量保证总结

这些测试共同保证了：

1. **提示词管理系统**：CRUD 操作正常，默认值/自定义值切换正确
2. **Agent 行为**：不同场景下 AI 响应符合预期风格
3. **数据提取**：爬虫能正确识别和提取页面信息
4. **记忆系统**：用户信息能被正确抽取和管理
5. **技能生成**：AI 能生成结构化的技能定义
